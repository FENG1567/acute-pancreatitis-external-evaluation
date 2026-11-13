"""Corrected, frozen-model eICU external evaluation.

This module consumes explicitly supplied controlled inputs. It never fits or
updates a model. Patient-keyed outputs are written only beneath ``controlled``;
aggregate metric tables contain no patient or hospital identifiers.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import re
import tempfile
from io import BytesIO
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd


KEY = "raw_icu_stay_id_hash"
OUTCOME = "outcome"
HOSPITAL = "hospitalid"
METRICS = (
    "auroc",
    "auprc",
    "brier",
    "log_loss",
    "calibration_in_the_large",
    "calibration_intercept",
    "calibration_slope",
    "scaled_brier",
)
THRESHOLDS = np.round(np.arange(0.01, 0.301, 0.01), 2)
N_BOOT = 2000
SEED_ANALYSIS = 20260811
PRIMARY_SEED = SEED_ANALYSIS + 100
SENSITIVE_SEED = SEED_ANALYSIS + 200
SENSITIVE_N = 1106
SENSITIVE_EVENTS = 96
PRIMARY_N = 359
PRIMARY_EVENTS = 21
_UNKNOWN_GENDERS = {
    "", "u", "unk", "unknown", "not known", "not recorded", "missing",
    "n/a", "na", "n.a.", "nan", "null", "none", "unavailable",
}


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_gender(value: Any) -> float:
    """Map recognized gender labels to the model's sex_male encoding.

    Unknown or missing values remain NaN so the frozen imputer handles them;
    they are never silently converted to the female value.
    """
    try:
        if pd.isna(value):
            return float("nan")
    except (TypeError, ValueError):
        pass
    label = str(value).strip().casefold()
    if label in {"m", "male"}:
        return 1.0
    if label in {"f", "female"}:
        return 0.0
    if label in _UNKNOWN_GENDERS:
        return float("nan")
    raise ValueError("unrecognized gender category")


def apply_gender_link(features: pd.DataFrame, patient_link: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of ``features`` with only ``sex_male`` corrected."""
    _require_columns(features, (KEY, "sex_male"), "sensitive features")
    _require_columns(patient_link, (KEY, "gender"), "patient link")
    feature_keys = _validated_keys(features, "sensitive features")
    link_keys = _validated_keys(patient_link, "patient link")
    if len(set(link_keys)) != len(link_keys):
        raise ValueError("patient link contains duplicate stay keys")
    if set(link_keys) != set(feature_keys):
        raise ValueError("patient-link keys must match the sensitive-feature keys exactly")

    gender_by_key = dict(zip(link_keys, patient_link["gender"].tolist()))
    corrected_values: list[float] = []
    for key in feature_keys:
        try:
            corrected_values.append(normalize_gender(gender_by_key[key]))
        except ValueError:
            raise ValueError("unrecognized gender category in patient link") from None

    corrected = features.copy(deep=True)
    corrected["sex_male"] = np.asarray(corrected_values, dtype=float)
    return corrected


def _require_columns(frame: pd.DataFrame, required: Sequence[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {', '.join(missing)}")


def _validated_keys(frame: pd.DataFrame, label: str) -> list[str]:
    values = frame[KEY]
    if values.isna().any():
        raise ValueError(f"{label} contains missing stay keys")
    keys: list[str] = []
    for value in values.tolist():
        if not isinstance(value, str) or not value or value.strip() != value:
            raise ValueError(f"{label} stay keys must be non-empty, trimmed strings")
        keys.append(value)
    if len(set(keys)) != len(keys):
        raise ValueError(f"{label} contains duplicate stay keys")
    return keys


def _binary_outcome(frame: pd.DataFrame, label: str) -> np.ndarray:
    _require_columns(frame, (OUTCOME,), label)
    try:
        outcome = pd.to_numeric(frame[OUTCOME], errors="raise").to_numpy(dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} outcome must contain only 0/1 values") from error
    if not np.isfinite(outcome).all() or not np.isin(outcome, (0.0, 1.0)).all():
        raise ValueError(f"{label} outcome must contain only 0/1 values")
    return outcome.astype(np.int8)


def _valid_hospitals(frame: pd.DataFrame, label: str) -> np.ndarray:
    _require_columns(frame, (HOSPITAL,), label)
    hospitals = frame[HOSPITAL].to_numpy()
    if pd.isna(hospitals).any():
        raise ValueError(f"{label} contains missing hospital clusters")
    try:
        unique = np.unique(hospitals)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} hospital clusters are not consistently typed") from error
    if len(unique) < 2:
        raise ValueError(f"{label} must contain at least two hospital clusters")
    return hospitals


def expit(values: np.ndarray) -> np.ndarray:
    values = np.clip(np.asarray(values, dtype=float), -40.0, 40.0)
    return 1.0 / (1.0 + np.exp(-values))


def _logit(probability: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probability, dtype=float), 1e-9, 1.0 - 1e-9)
    return np.log(clipped / (1.0 - clipped))


def calibration_in_the_large(y: np.ndarray, probability: np.ndarray) -> float:
    """Estimate CITL with logit(prediction) as an offset and slope fixed at 1."""
    y = np.asarray(y, dtype=float)
    offset = _logit(probability)
    event_count = float(np.sum(y))
    if event_count <= 0.0 or event_count >= len(y):
        return float("nan")

    # The score is monotone in the intercept. Bisection avoids the oversized
    # Newton steps that can occur when all frozen predictions are extreme.
    lower, upper = -1.0, 1.0
    while float(np.sum(expit(offset + lower))) >= event_count:
        lower *= 2.0
    while float(np.sum(expit(offset + upper))) <= event_count:
        upper *= 2.0
    for _ in range(100):
        intercept = (lower + upper) / 2.0
        fitted_events = float(np.sum(expit(offset + intercept)))
        if fitted_events < event_count:
            lower = intercept
        else:
            upper = intercept
        if upper - lower < 1e-11:
            break
    intercept = (lower + upper) / 2.0
    if not np.isfinite(intercept):
        raise RuntimeError("non-finite calibration-in-the-large estimate")
    return float(intercept)


def logistic_calibration(y: np.ndarray, probability: np.ndarray) -> tuple[float, float]:
    """Fit the joint unpenalized calibration intercept and slope by Newton steps."""
    y = np.asarray(y, dtype=float)
    log_odds = _logit(probability)
    design = np.column_stack((np.ones(len(log_odds), dtype=float), log_odds))
    if np.linalg.matrix_rank(design) < 2 or np.unique(y).size != 2:
        return float('nan'), float('nan')
    # In a one-dimensional logistic model these inequalities detect complete
    # and quasi-complete separation. No finite joint MLE exists in that case.
    positive = log_odds[y == 1]
    negative = log_odds[y == 0]
    if np.min(positive) >= np.max(negative) or np.max(positive) <= np.min(negative):
        return float('nan'), float('nan')
    coefficients = np.zeros(2, dtype=float)
    converged = False
    for _ in range(100):
        fitted = expit(design @ coefficients)
        gradient = design.T @ (y - fitted)
        weight = np.maximum(fitted * (1.0 - fitted), 1e-10)
        information = design.T @ (design * weight[:, None])
        step = np.linalg.pinv(information, rcond=1e-12) @ gradient
        coefficients += step
        if np.max(np.abs(step)) < 1e-10:
            converged = True
            break
    if not converged or not np.isfinite(coefficients).all():
        return float('nan'), float('nan')
    if np.max(np.abs(design.T @ (y - expit(design @ coefficients)))) > 1e-6:
        return float('nan'), float('nan')
    return float(coefficients[0]), float(coefficients[1])


def _roc_auc(y: np.ndarray, probability: np.ndarray) -> float:
    order = np.argsort(probability, kind="mergesort")
    sorted_probability = probability[order]
    sorted_y = y[order]
    _, inverse, counts = np.unique(sorted_probability, return_inverse=True, return_counts=True)
    starts = np.cumsum(counts) - counts
    average_ranks = starts + (counts + 1.0) / 2.0
    ranks = average_ranks[inverse]
    positives = int(np.sum(y == 1))
    negatives = len(y) - positives
    return float((np.sum(ranks[sorted_y == 1]) - positives * (positives + 1) / 2.0) / (positives * negatives))


def _average_precision(y: np.ndarray, probability: np.ndarray) -> float:
    order = np.argsort(-probability, kind="mergesort")
    sorted_probability = probability[order]
    sorted_y = y[order]
    group_ends = np.flatnonzero(np.r_[sorted_probability[:-1] != sorted_probability[1:], True])
    cumulative_true_positives = np.cumsum(sorted_y)[group_ends]
    precision_at_end = cumulative_true_positives / (group_ends + 1.0)
    positives_per_group = np.diff(np.r_[0, cumulative_true_positives])
    recall_increment = positives_per_group / float(np.sum(y == 1))
    return float(np.sum(precision_at_end * recall_increment))


def metric_values(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    """Calculate discrimination, proper scores, distinct calibration terms, and scaled Brier."""
    y = np.asarray(y, dtype=float)
    probability = np.asarray(probability, dtype=float)
    if y.ndim != 1 or probability.ndim != 1 or len(y) != len(probability):
        raise ValueError("outcome and probability must be aligned one-dimensional arrays")
    if len(y) == 0:
        raise ValueError("outcome and probability must contain at least one row")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("outcome must contain only 0/1 values")
    y = y.astype(np.int8)
    if not np.isfinite(probability).all() or np.any((probability < 0.0) | (probability > 1.0)):
        raise ValueError("predicted probabilities must be finite and lie in [0, 1]")
    p_clip = np.clip(probability, 1e-9, 1.0 - 1e-9)
    prevalence = float(np.mean(y))
    brier = float(np.mean((y - probability) ** 2))
    log_loss = float(-np.mean(y * np.log(p_clip) + (1 - y) * np.log(1.0 - p_clip)))
    if np.unique(y).size != 2:
        return {
            "auroc": float("nan"),
            "auprc": float("nan"),
            "brier": brier,
            "log_loss": log_loss,
            "calibration_in_the_large": float("nan"),
            "calibration_intercept": float("nan"),
            "calibration_slope": float("nan"),
            "scaled_brier": float("nan"),
        }
    joint_intercept, joint_slope = logistic_calibration(y, probability)
    return {
        "auroc": _roc_auc(y, probability),
        "auprc": _average_precision(y, probability),
        "brier": brier,
        "log_loss": log_loss,
        "calibration_in_the_large": calibration_in_the_large(y, probability),
        "calibration_intercept": joint_intercept,
        "calibration_slope": joint_slope,
        "scaled_brier": float(1.0 - brier / (prevalence * (1.0 - prevalence))),
    }


def net_benefit(y: np.ndarray, probability: np.ndarray) -> np.ndarray:
    selected = np.asarray(probability, dtype=float)[:, None] >= THRESHOLDS[None, :]
    y = np.asarray(y, dtype=np.int8)
    true_positive = np.mean(selected & (y[:, None] == 1), axis=0)
    false_positive = np.mean(selected & (y[:, None] == 0), axis=0)
    return true_positive - false_positive * THRESHOLDS / (1.0 - THRESHOLDS)


def index_draws(
    n: int,
    seed: int,
    hospitals: np.ndarray | None = None,
    n_bootstrap: int = N_BOOT,
) -> list[np.ndarray]:
    """Create deterministic patient or hospital-cluster bootstrap indices.

    Cluster sampling concatenates each selected hospital's complete row set in
    draw order. If a hospital is selected more than once, all its rows are
    deliberately repeated rather than deduplicated.
    """
    if n <= 0 or n_bootstrap <= 0:
        raise ValueError("bootstrap sample and replicate counts must be positive")
    rng = np.random.default_rng(seed)
    if hospitals is None:
        return [rng.integers(0, n, n) for _ in range(n_bootstrap)]
    hospitals = np.asarray(hospitals)
    if hospitals.ndim != 1 or len(hospitals) != n or pd.isna(hospitals).any():
        raise ValueError("hospital clusters must be non-missing and aligned to rows")
    unique = np.unique(hospitals)
    positions = {hospital: np.flatnonzero(hospitals == hospital) for hospital in unique}
    draws: list[np.ndarray] = []
    for _ in range(n_bootstrap):
        selected_hospitals = rng.choice(unique, len(unique), replace=True)
        draws.append(np.concatenate([positions[hospital] for hospital in selected_hospitals]))
    return draws


def percentile(draws: Sequence[float] | np.ndarray) -> tuple[float, float]:
    values = np.asarray(draws, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return float("nan"), float("nan")
    return float(np.quantile(values, 0.025)), float(np.quantile(values, 0.975))


def evaluate_dataset(
    name: str,
    frame: pd.DataFrame,
    seed: int,
    clustered: bool,
    n_bootstrap: int = N_BOOT,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Evaluate A and B with paired patient and, where requested, cluster CIs."""
    _require_columns(frame, (OUTCOME, "pred_A", "pred_B"), name)
    y = _binary_outcome(frame, name)
    probabilities = {model: frame[f"pred_{model}"].to_numpy(dtype=float) for model in ("A", "B")}
    for model, probability in probabilities.items():
        if not np.isfinite(probability).all() or np.any((probability < 0.0) | (probability > 1.0)):
            raise ValueError(f"{name} Model {model} predictions must be finite probabilities")
    patient_draws = index_draws(len(frame), seed, n_bootstrap=n_bootstrap)
    if clustered:
        hospital_ids = _valid_hospitals(frame, name)
        cluster_draws = index_draws(len(frame), seed + 1000, hospital_ids, n_bootstrap)
    else:
        cluster_draws = []

    point_metrics = {model: metric_values(y, probabilities[model]) for model in ("A", "B")}
    point_dca = {model: net_benefit(y, probabilities[model]) for model in ("A", "B")}
    patient_metric = {model: defaultdict(list) for model in ("A", "B")}
    cluster_metric = {model: defaultdict(list) for model in ("A", "B")}
    patient_dca = {model: [] for model in ("A", "B")}
    cluster_dca = {model: [] for model in ("A", "B")}
    patient_difference: dict[str, list[float]] = defaultdict(list)
    cluster_difference: dict[str, list[float]] = defaultdict(list)
    patient_dca_difference: list[np.ndarray] = []
    cluster_dca_difference: list[np.ndarray] = []

    for draws, metrics_by_model, dca_by_model, differences, dca_differences in (
        (patient_draws, patient_metric, patient_dca, patient_difference, patient_dca_difference),
        (cluster_draws, cluster_metric, cluster_dca, cluster_difference, cluster_dca_difference),
    ):
        for draw in draws:
            draw_metrics: dict[str, dict[str, float]] = {}
            for model in ("A", "B"):
                draw_y = y[draw]
                draw_probability = probabilities[model][draw]
                draw_metrics[model] = metric_values(draw_y, draw_probability)
                for metric, value in draw_metrics[model].items():
                    metrics_by_model[model][metric].append(value)
                dca_by_model[model].append(net_benefit(draw_y, draw_probability))
            for metric in METRICS:
                differences[metric].append(draw_metrics["A"][metric] - draw_metrics["B"][metric])
            dca_differences.append(dca_by_model["A"][-1] - dca_by_model["B"][-1])

    performance_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    for model in ("A", "B"):
        for metric in METRICS:
            patient_ci = percentile(patient_metric[model][metric])
            cluster_ci = percentile(cluster_metric[model][metric]) if clustered else (np.nan, np.nan)
            performance_rows.append({
                "dataset": name,
                "model": model,
                "metric": metric,
                "estimate": point_metrics[model][metric],
                "patient_ci_low": patient_ci[0],
                "patient_ci_high": patient_ci[1],
                "patient_bootstrap_valid": int(np.isfinite(patient_metric[model][metric]).sum()),
                "cluster_ci_low": cluster_ci[0],
                "cluster_ci_high": cluster_ci[1],
                "cluster_bootstrap_valid": int(np.isfinite(cluster_metric[model][metric]).sum()) if clustered else 0,
                "bootstrap_replicates_requested": n_bootstrap,
            })
    for metric in METRICS:
        patient_ci = percentile(patient_difference[metric])
        cluster_ci = percentile(cluster_difference[metric]) if clustered else (np.nan, np.nan)
        paired_rows.append({
            "dataset": name,
            "comparison": "A_minus_B",
            "metric": metric,
            "estimate": point_metrics["A"][metric] - point_metrics["B"][metric],
            "patient_ci_low": patient_ci[0],
            "patient_ci_high": patient_ci[1],
            "cluster_ci_low": cluster_ci[0],
            "cluster_ci_high": cluster_ci[1],
            "bootstrap_replicates_requested": n_bootstrap,
            "patient_bootstrap_valid": int(np.isfinite(patient_difference[metric]).sum()),
            "cluster_bootstrap_valid": int(np.isfinite(cluster_difference[metric]).sum()) if clustered else 0,
        })

    prevalence = float(np.mean(y))
    dca_rows: list[dict[str, Any]] = []
    patient_dca_array = {model: np.asarray(patient_dca[model], dtype=float) for model in ("A", "B")}
    cluster_dca_array = {model: np.asarray(cluster_dca[model], dtype=float) for model in ("A", "B")}
    patient_dca_diff_array = np.asarray(patient_dca_difference, dtype=float)
    cluster_dca_diff_array = np.asarray(cluster_dca_difference, dtype=float)
    for index, threshold in enumerate(THRESHOLDS):
        treat_all = prevalence - (1.0 - prevalence) * threshold / (1.0 - threshold)
        dca_rows.extend((
            {"dataset": name, "model": "treat_none", "threshold": threshold, "net_benefit": 0.0,
             "patient_ci_low": 0.0, "patient_ci_high": 0.0,
             "cluster_ci_low": 0.0 if clustered else np.nan,
             "cluster_ci_high": 0.0 if clustered else np.nan},
            {"dataset": name, "model": "treat_all", "threshold": threshold, "net_benefit": treat_all,
             "patient_ci_low": np.nan, "patient_ci_high": np.nan,
             "cluster_ci_low": np.nan, "cluster_ci_high": np.nan},
        ))
        for model in ("A", "B"):
            patient_ci = percentile(patient_dca_array[model][:, index])
            cluster_ci = percentile(cluster_dca_array[model][:, index]) if clustered else (np.nan, np.nan)
            dca_rows.append({
                "dataset": name,
                "model": model,
                "threshold": threshold,
                "net_benefit": point_dca[model][index],
                "patient_ci_low": patient_ci[0],
                "patient_ci_high": patient_ci[1],
                "cluster_ci_low": cluster_ci[0],
                "cluster_ci_high": cluster_ci[1],
            })
        patient_ci = percentile(patient_dca_diff_array[:, index])
        cluster_ci = percentile(cluster_dca_diff_array[:, index]) if clustered else (np.nan, np.nan)
        dca_rows.append({
            "dataset": name,
            "model": "A_minus_B",
            "threshold": threshold,
            "net_benefit": point_dca["A"][index] - point_dca["B"][index],
            "patient_ci_low": patient_ci[0],
            "patient_ci_high": patient_ci[1],
            "cluster_ci_low": cluster_ci[0],
            "cluster_ci_high": cluster_ci[1],
        })
    return performance_rows, paired_rows, dca_rows


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    checker = getattr(path, "is_junction", None)
    return bool(checker()) if checker is not None else False


def validate_new_output_path(output: Path, repo_root: Path | None = None) -> Path:
    """Validate a not-yet-existing output directory and return its resolved path."""
    raw = Path(output).expanduser()
    if not raw.name or raw.name in {".", ".."}:
        raise ValueError("output must name a new directory")
    absolute = raw if raw.is_absolute() else Path.cwd() / raw
    for ancestor in (absolute, *absolute.parents):
        if _is_link_or_junction(ancestor):
            raise ValueError("output path may not contain a symlink or junction")
    resolved = absolute.resolve(strict=False)
    if resolved.exists() or resolved.is_symlink() or _is_link_or_junction(resolved):
        raise FileExistsError(f"output already exists: {resolved}")
    if repo_root is not None:
        root = Path(repo_root).resolve(strict=True)
        forbidden = (
            root / "source_data",
            root / "rawdata",
            root / "raw_data",
            root / "raw-data",
            root / "raw",
            root / "data" / "raw",
            root / "data" / "rawdata",
            root / "data" / "raw_data",
        )
        for directory in forbidden:
            forbidden_path = directory.resolve(strict=False)
            if resolved == forbidden_path or forbidden_path in resolved.parents:
                raise ValueError("refusing output beneath repository source/raw-data directories")
    if not resolved.parent.is_dir():
        raise FileNotFoundError("output parent directory must already exist")
    return resolved


def _verify_expected_hash(path: Path, expected_hash: str, label: str) -> str:
    if not re.fullmatch(r"[0-9a-fA-F]{64}", str(expected_hash)):
        raise ValueError(f"{label} expected SHA-256 must be 64 hexadecimal characters")
    actual_hash = sha256_file(path)
    if actual_hash.lower() != str(expected_hash).lower():
        raise ValueError(f"{label} SHA-256 does not match the supplied trusted digest")
    return actual_hash


def _load_verified_bundles(
    model_a_path: Path,
    model_b_path: Path,
    model_a_sha256: str,
    model_b_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    """Verify both trusted digests before either serialized bundle is loaded."""
    data_a = model_a_path.read_bytes()
    data_b = model_b_path.read_bytes()
    hashes = {"model_A": hashlib.sha256(data_a).hexdigest(), "model_B": hashlib.sha256(data_b).hexdigest()}
    for label, expected in (("model_A", model_a_sha256), ("model_B", model_b_sha256)):
        if not re.fullmatch(r'[0-9a-fA-F]{64}', str(expected)) or hashes[label] != str(expected).lower():
            raise ValueError(('Model A' if label == 'model_A' else 'Model B') + ' SHA-256 does not match the supplied trusted digest')
    # joblib uses pickle semantics: only load artifacts whose expected hashes
    # were obtained from a trusted source and matched above.
    import joblib

    bundles = {"A": joblib.load(BytesIO(data_a)), "B": joblib.load(BytesIO(data_b))}
    for name, bundle in bundles.items():
        _validate_bundle(bundle, name)
    return bundles["A"], bundles["B"], hashes


def _validate_bundle(bundle: Any, label: str) -> None:
    if not isinstance(bundle, Mapping):
        raise ValueError(f"Model {label} bundle must be a mapping")
    required = ("features", "imputer", "scaler", "model")
    missing = [name for name in required if name not in bundle]
    if missing:
        raise ValueError(f"Model {label} bundle is missing: {', '.join(missing)}")
    features = bundle["features"]
    if isinstance(features, (str, bytes)):
        raise ValueError(f"Model {label} feature list is invalid")
    feature_names = list(features)
    if not feature_names or len(set(feature_names)) != len(feature_names) or "sex_male" not in feature_names:
        raise ValueError(f"Model {label} must have a unique feature list including sex_male")
    if not callable(getattr(bundle["imputer"], "transform", None)):
        raise ValueError(f"Model {label} imputer has no transform method")
    if not callable(getattr(bundle["scaler"], "transform", None)):
        raise ValueError(f"Model {label} scaler has no transform method")
    if not callable(getattr(bundle["model"], "predict_proba", None)):
        raise ValueError(f"Model {label} has no predict_proba method")
    classes = getattr(bundle["model"], "classes_", None)
    if classes is not None and (len(classes) != 2 or classes[1] != 1):
        raise ValueError(f"Model {label} positive outcome class must be at probability column 1")


def _predict_frozen(frame: pd.DataFrame, bundle: Mapping[str, Any], label: str) -> np.ndarray:
    feature_names = list(bundle["features"])
    missing = [name for name in feature_names if name not in frame.columns]
    if missing:
        raise ValueError(f"Model {label} input is missing frozen features: {', '.join(missing)}")
    try:
        matrix = frame.loc[:, feature_names].astype(float)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Model {label} features must be numeric or missing") from error
    if np.isinf(matrix.to_numpy(dtype=float)).any():
        raise ValueError(f"Model {label} input features contain infinity")
    transformed = bundle["imputer"].transform(matrix)
    transformed = bundle["scaler"].transform(transformed)
    predicted = np.asarray(bundle["model"].predict_proba(transformed), dtype=float)
    if predicted.ndim != 2 or predicted.shape != (len(frame), 2):
        raise ValueError(f"Model {label} predict_proba returned an unexpected shape")
    probability = predicted[:, 1]
    if not np.isfinite(probability).all() or np.any((probability < 0.0) | (probability > 1.0)):
        raise ValueError(f"Model {label} returned invalid probabilities")
    return probability


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8", lineterminator="\n", float_format="%.17g")


def _write_json(value: Any, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _assert_cohort(frame: pd.DataFrame, label: str, expected_n: int, expected_events: int) -> np.ndarray:
    _validated_keys(frame, label)
    outcome = _binary_outcome(frame, label)
    if len(frame) != expected_n or int(np.sum(outcome)) != expected_events:
        raise ValueError(f"{label} cohort assertion failed (expected n={expected_n}, events={expected_events})")
    _valid_hospitals(frame, label)
    return outcome


def _verify_primary_alignment(features: pd.DataFrame, primary_lock: pd.DataFrame) -> None:
    feature_keys = _validated_keys(features, "sensitive features")
    primary_keys = _validated_keys(primary_lock, "primary lock")
    if not set(primary_keys).issubset(feature_keys):
        raise ValueError("primary-lock keys are not all present in the sensitive features")
    indexed = features.set_index(KEY, drop=False)
    aligned = indexed.loc[primary_keys]
    primary_outcome = _binary_outcome(primary_lock, "primary lock")
    aligned_outcome = _binary_outcome(aligned, "primary-overlap features")
    if not np.array_equal(primary_outcome, aligned_outcome):
        raise ValueError("primary-lock outcomes do not match the sensitive-feature overlap")
    primary_hospital = primary_lock[HOSPITAL].to_numpy()
    aligned_hospital = aligned[HOSPITAL].to_numpy()
    if not np.array_equal(primary_hospital, aligned_hospital):
        raise ValueError("primary-lock hospital clusters do not match the sensitive-feature overlap")


def _manifest(
    stage: Path,
    input_hashes: Mapping[str, str],
    model_hashes: Mapping[str, str],
    bootstrap_replicates: int,
    code_paths: Sequence[Path],
) -> dict[str, Any]:
    artifacts = {}
    for path in sorted(candidate for candidate in stage.rglob("*") if candidate.is_file()):
        relative = path.relative_to(stage).as_posix()
        artifacts[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    versions = {}
    for distribution in ("numpy", "pandas", "scikit-learn", "joblib", "pyarrow"):
        try:
            versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            versions[distribution] = None
    return {
        "schema_version": "1.0",
        "analysis_version": "corrected-eicu-external-1.0",
        "status": "PASS",
        "inputs_sha256": dict(input_hashes),
        "frozen_model_sha256": dict(model_hashes),
        "code_sha256": {path.name: sha256_file(path) for path in code_paths},
        "software_versions": versions,
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "primary_patient_seed": PRIMARY_SEED,
            "primary_hospital_seed": PRIMARY_SEED + 1000,
            "sensitive_patient_seed": SENSITIVE_SEED,
            "sensitive_hospital_seed": SENSITIVE_SEED + 1000,
            "hospital_resample_rule": "sample hospitals with replacement; append every row for every selected cluster, retaining repeated clusters",
        },
        "metric_definitions": {
            "calibration_in_the_large": "logistic intercept with logit(prediction) as offset and slope fixed at 1",
            "calibration_intercept_and_slope": "joint unpenalized logistic calibration regression with free intercept and slope",
            "scaled_brier": "1 - Brier / [prevalence * (1 - prevalence)]",
            "log_loss_probability_clipping": "[1e-9, 1 - 1e-9]",
        },
        "assertions": {
            "primary_n": PRIMARY_N,
            "primary_events": PRIMARY_EVENTS,
            "sensitive_n": SENSITIVE_N,
            "sensitive_events": SENSITIVE_EVENTS,
            "primary_baseline_predictions_match_lock_at_absolute_tolerance": 1e-15,
            "model_refit": False,
            "only_corrected_feature": "sex_male",
        },
        "outputs_sha256": artifacts,
        "publication_control": "controlled/ contains patient-keyed locks and must not be published; metrics/ contains aggregate outputs",
    }


def run_corrected_evaluation(
    *,
    features_path: Path,
    patient_link_path: Path,
    primary_lock_path: Path,
    model_a_path: Path,
    model_b_path: Path,
    model_a_sha256: str,
    model_b_sha256: str,
    features_sha256: str,
    primary_lock_sha256: str,
    output_path: Path,
    bootstrap_replicates: int = N_BOOT,
    repo_root: Path | None = None,
) -> Path:
    """Run the evaluation into a new output directory atomically."""
    if bootstrap_replicates <= 0:
        raise ValueError("bootstrap replicate count must be positive")
    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[1]
    final_output = validate_new_output_path(output_path, repo_root)
    inputs = {
        "features": Path(features_path),
        "patient_link": Path(patient_link_path),
        "primary_lock": Path(primary_lock_path),
        "model_A": Path(model_a_path),
        "model_B": Path(model_b_path),
    }
    for label, path in inputs.items():
        if not path.is_file():
            raise FileNotFoundError(f"{label} input file is missing")
    if inputs["model_A"].resolve() == inputs["model_B"].resolve():
        raise ValueError("Model A and Model B must be distinct files")
    # Pin and parse the same byte snapshots, not files reopened after hashing.
    snapshots = {name: path.read_bytes() for name, path in inputs.items() if name not in ('model_A', 'model_B')}
    input_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in snapshots.items()}
    for name, expected in (("features", features_sha256), ("primary_lock", primary_lock_sha256)):
        if not re.fullmatch(r'[0-9a-fA-F]{64}', str(expected)) or input_hashes[name] != str(expected).lower():
            raise ValueError(name + ' SHA-256 does not match the supplied trusted digest')

    # Check both trusted artifact digests before either joblib object is loaded.
    bundle_a, bundle_b, model_hashes = _load_verified_bundles(
        inputs["model_A"], inputs["model_B"], model_a_sha256, model_b_sha256
    )

    features = pd.read_parquet(BytesIO(snapshots['features']))
    patient_link = pd.read_csv(
        BytesIO(snapshots['patient_link']),
        dtype={KEY: "string", "gender": "string"},
        keep_default_na=True,
    )
    primary_lock = pd.read_parquet(BytesIO(snapshots['primary_lock']))
    _require_columns(features, (KEY, OUTCOME, HOSPITAL, "sex_male"), "sensitive features")
    _require_columns(primary_lock, (KEY, OUTCOME, HOSPITAL, "pred_A", "pred_B"), "primary lock")
    _assert_cohort(features, "sensitive features", SENSITIVE_N, SENSITIVE_EVENTS)
    _assert_cohort(primary_lock, "primary lock", PRIMARY_N, PRIMARY_EVENTS)
    _verify_primary_alignment(features, primary_lock)

    aligned_primary_features = features.set_index(KEY, drop=False).loc[primary_lock[KEY].tolist()]
    for model_name, bundle in (("A", bundle_a), ("B", bundle_b)):
        baseline = _predict_frozen(aligned_primary_features, bundle, model_name)
        locked = primary_lock[f"pred_{model_name}"].to_numpy(dtype=float)
        if not np.isfinite(locked).all() or np.any((locked < 0.0) | (locked > 1.0)):
            raise ValueError(f"primary lock Model {model_name} predictions are invalid")
        if not np.allclose(baseline, locked, atol=1e-15, rtol=0):
            raise ValueError(f"Model {model_name} baseline predictions do not match the primary lock within 1e-15")

    corrected_features = apply_gender_link(features, patient_link)
    corrected_predictions = corrected_features[[KEY, OUTCOME, HOSPITAL]].copy()
    for model_name, bundle in (("A", bundle_a), ("B", bundle_b)):
        corrected_predictions[f"pred_{model_name}"] = _predict_frozen(corrected_features, bundle, model_name)

    primary_for_metrics = primary_lock.copy(deep=True)
    corrected_by_key = corrected_predictions.set_index(KEY)
    for model_name in ('A', 'B'):
        primary_for_metrics[f'pred_{model_name}'] = corrected_by_key.loc[primary_lock[KEY], f'pred_{model_name}'].to_numpy()
    performance_rows: list[dict[str, Any]] = []
    paired_rows: list[dict[str, Any]] = []
    dca_rows: list[dict[str, Any]] = []
    for name, frame, seed in (
        ("eICU_primary_locked_359", primary_for_metrics, PRIMARY_SEED),
        ("eICU_sensitive_corrected_1106", corrected_predictions, SENSITIVE_SEED),
    ):
        performance, paired, dca = evaluate_dataset(
            name, frame, seed, clustered=True, n_bootstrap=bootstrap_replicates
        )
        performance_rows.extend(performance)
        paired_rows.extend(paired)
        dca_rows.extend(dca)

    input_hashes.update(model_hashes)
    for name, path in inputs.items():
        if sha256_file(path) != input_hashes[name]:
            raise RuntimeError('Input changed during evaluation: ' + name)
    code_paths = (Path(__file__).resolve(), Path(__file__).resolve().parents[1] / "scripts" / "recompute_corrected_external.py")

    # Build outside the final name. The final directory appears only after all
    # outputs and the run manifest are complete.
    with tempfile.TemporaryDirectory(prefix=f".{final_output.name}.tmp-", dir=final_output.parent) as temporary:
        stage = Path(temporary)
        controlled = stage / "controlled"
        metrics = stage / "metrics"
        controlled.mkdir()
        metrics.mkdir()
        primary_for_metrics.to_parquet(controlled / "eicu_primary_locked_359.parquet", index=False)
        corrected_predictions.to_parquet(controlled / "eicu_sensitive_corrected_1106.parquet", index=False)
        _write_csv(pd.DataFrame(performance_rows), metrics / "performance_metrics.csv")
        _write_csv(pd.DataFrame(paired_rows), metrics / "paired_A_vs_B.csv")
        _write_csv(pd.DataFrame(dca_rows), metrics / "decision_curve_analysis.csv")
        manifest = _manifest(stage, input_hashes, model_hashes, bootstrap_replicates, code_paths)
        _write_json(manifest, stage / "executed_manifest.json")

        # Refuse a concurrently created destination; never replace an existing run.
        rechecked_output = validate_new_output_path(output_path, repo_root)
        if rechecked_output != final_output:
            raise RuntimeError("output path changed during the run")
        os.rename(stage, final_output)
    return final_output
