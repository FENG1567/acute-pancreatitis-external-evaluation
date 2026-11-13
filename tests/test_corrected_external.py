"""Synthetic-only tests for the corrected frozen-model eICU evaluation."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

import external_evaluation as evaluation  # noqa: E402


class GenderCorrectionTests(unittest.TestCase):
    def test_labels_are_stripped_case_insensitive_and_unknown_stays_missing(self):
        self.assertEqual(evaluation.normalize_gender("  m "), 1.0)
        self.assertEqual(evaluation.normalize_gender("MALE"), 1.0)
        self.assertEqual(evaluation.normalize_gender(" f "), 0.0)
        self.assertEqual(evaluation.normalize_gender("Female"), 0.0)
        for value in (None, np.nan, pd.NA, " Unknown ", "u", "not recorded", ""):
            self.assertTrue(np.isnan(evaluation.normalize_gender(value)))

    def test_unrecognized_gender_fails_and_only_copy_sex_is_changed(self):
        features = pd.DataFrame({
            evaluation.KEY: ["stay-a", "stay-b", "stay-c"],
            "sex_male": [0.0, 0.0, 1.0],
            "age": [40.0, 50.0, 60.0],
        })
        link = pd.DataFrame({
            evaluation.KEY: ["stay-a", "stay-b", "stay-c"],
            "gender": ["M", "unknown", "Female"],
        })
        corrected = evaluation.apply_gender_link(features, link)
        self.assertEqual(features["sex_male"].tolist(), [0.0, 0.0, 1.0])
        self.assertEqual(corrected["sex_male"].iloc[0], 1.0)
        self.assertTrue(np.isnan(corrected["sex_male"].iloc[1]))
        self.assertEqual(corrected["sex_male"].iloc[2], 0.0)
        pd.testing.assert_series_equal(features["age"], corrected["age"])
        with self.assertRaisesRegex(ValueError, "unrecognized gender category"):
            evaluation.apply_gender_link(features, link.assign(gender=["M", "Other", "F"]))


class MetricAndBootstrapTests(unittest.TestCase):
    def test_joint_calibration_rejects_separation_and_constant_predictions(self):
        for y, p in [(np.array([0,0,1,1]),np.array([.1,.2,.8,.9])),
                     (np.array([0,0,0,1]),np.array([.2,.2,.2,.2]))]:
            a,b=evaluation.logistic_calibration(y,p)
            self.assertTrue(np.isnan(a) and np.isnan(b))
            self.assertTrue(np.isfinite(evaluation.calibration_in_the_large(y,p)))
        with self.assertRaises(ValueError):
            evaluation.metric_values(np.array([0.,.5,1.]),np.array([.1,.2,.3]))

    def test_citl_is_offset_intercept_distinct_from_joint_calibration(self):
        y = np.asarray([0, 1, 0, 0, 1, 0, 1, 1], dtype=np.int8)
        probability = np.asarray([0.04, 0.10, 0.18, 0.31, 0.47, 0.64, 0.79, 0.92])
        metrics = evaluation.metric_values(y, probability)
        shifted_prevalence = np.mean(evaluation.expit(evaluation._logit(probability) + metrics["calibration_in_the_large"]))
        self.assertAlmostEqual(shifted_prevalence, np.mean(y), places=9)
        self.assertNotAlmostEqual(metrics["calibration_in_the_large"], metrics["calibration_intercept"], places=4)
        expected_scaled = 1.0 - metrics["brier"] / (np.mean(y) * (1.0 - np.mean(y)))
        self.assertAlmostEqual(metrics["scaled_brier"], expected_scaled)
        self.assertIn("calibration_slope", metrics)

        from sklearn.metrics import average_precision_score, roc_auc_score
        self.assertAlmostEqual(metrics["auroc"], roc_auc_score(y, probability))
        self.assertAlmostEqual(metrics["auprc"], average_precision_score(y, probability))

    def test_one_class_bootstrap_draw_keeps_defined_proper_scores(self):
        metrics = evaluation.metric_values(np.zeros(4, dtype=np.int8), np.asarray([0.1, 0.2, 0.3, 0.4]))
        self.assertTrue(np.isnan(metrics["auroc"]))
        self.assertTrue(np.isnan(metrics["calibration_in_the_large"]))
        self.assertTrue(np.isnan(metrics["scaled_brier"]))
        self.assertTrue(np.isfinite(metrics["brier"]))
        self.assertTrue(np.isfinite(metrics["log_loss"]))

    def test_cluster_bootstrap_is_deterministic_and_retains_repeated_hospitals(self):
        hospitals = np.asarray([10, 10, 20, 20])
        first = evaluation.index_draws(4, 123, hospitals, n_bootstrap=64)
        second = evaluation.index_draws(4, 123, hospitals, n_bootstrap=64)
        self.assertTrue(all(np.array_equal(left, right) for left, right in zip(first, second)))
        self.assertTrue(any(len(np.unique(hospitals[draw])) == 1 for draw in first))
        for draw in first:
            self.assertEqual(len(draw) % 2, 0)
            for selected_rows in draw.reshape(-1, 2):
                hospital = hospitals[selected_rows[0]]
                self.assertTrue(np.array_equal(selected_rows, np.flatnonzero(hospitals == hospital)))
        repeated = next(draw for draw in first if len(np.unique(hospitals[draw])) == 1)
        self.assertTrue(np.all(np.bincount(repeated, minlength=4)[np.unique(repeated)] == 2))

    def test_evaluate_dataset_returns_paired_cluster_and_dca_rows(self):
        rng = np.random.default_rng(7)
        n = 80
        y = np.tile(np.asarray([0, 1], dtype=np.int8), n // 2)
        frame = pd.DataFrame({
            "outcome": y,
            "hospitalid": np.repeat(np.arange(8), 10),
            "pred_A": np.clip(0.4 + 0.1 * y + rng.normal(0, 0.2, n), 0.01, 0.99),
            "pred_B": np.clip(0.38 + 0.12 * y + rng.normal(0, 0.2, n), 0.01, 0.99),
        })
        result1 = evaluation.evaluate_dataset("synthetic", frame, 91, clustered=True, n_bootstrap=8)
        result2 = evaluation.evaluate_dataset("synthetic", frame, 91, clustered=True, n_bootstrap=8)
        pd.testing.assert_frame_equal(pd.DataFrame(result1[0]), pd.DataFrame(result2[0]), check_exact=True)
        paired = pd.DataFrame(result1[1])
        self.assertTrue((paired["comparison"] == "A_minus_B").all())
        self.assertTrue(paired["cluster_ci_low"].notna().all())
        dca = pd.DataFrame(result1[2])
        self.assertEqual(set(dca["model"]), {"A", "B", "A_minus_B", "treat_all", "treat_none"})
        self.assertTrue((dca["threshold"].between(0.01, 0.30)).all())


class OutputAndHashSafetyTests(unittest.TestCase):
    def test_existing_output_and_repository_source_data_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            existing = parent / "existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                evaluation.validate_new_output_path(existing, repo_root=ROOT)
        with self.assertRaisesRegex(ValueError, "source/raw-data"):
            evaluation.validate_new_output_path(ROOT / "source_data" / "new_run", repo_root=ROOT)

    def test_symlink_output_path_is_rejected_when_platform_supports_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.mkdir()
            link = root / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("directory symlinks are unavailable on this platform")
            with self.assertRaisesRegex(ValueError, "symlink or junction"):
                evaluation.validate_new_output_path(link / "new_run", repo_root=ROOT)

    def test_both_hashes_are_verified_before_any_joblib_load(self):
        import joblib

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model_a = root / "a.joblib"
            model_b = root / "b.joblib"
            model_a.write_bytes(b"synthetic-A")
            model_b.write_bytes(b"synthetic-B")
            with mock.patch.object(joblib, "load") as load:
                with self.assertRaisesRegex(ValueError, "Model B SHA-256"):
                    evaluation._load_verified_bundles(
                        model_a,
                        model_b,
                        evaluation.sha256_file(model_a),
                        "0" * 64,
                    )
                load.assert_not_called()


class SyntheticRunTests(unittest.TestCase):
    def _make_inputs(self, root: Path) -> dict[str, Path | str]:
        from joblib import dump
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        rng = np.random.default_rng(2026)
        n = evaluation.SENSITIVE_N
        y = np.zeros(n, dtype=np.int8)
        y[: evaluation.PRIMARY_EVENTS] = 1
        y[evaluation.PRIMARY_N : evaluation.PRIMARY_N + (evaluation.SENSITIVE_EVENTS - evaluation.PRIMARY_EVENTS)] = 1
        age = rng.normal(58.0, 14.0, n) + y * 3.0
        gender = np.where(np.arange(n) % 2 == 0, "Male", "Female").astype(object)
        gender[400] = " Unknown "  # outside the locked primary subset
        old_sex_male = np.zeros(n)
        features = pd.DataFrame({
            evaluation.KEY: [f"synthetic-stay-{index:04d}" for index in range(n)],
            "outcome": y,
            "hospitalid": np.arange(n) % 4,
            "age": age,
            "sex_male": old_sex_male,
        })
        patient_link = pd.DataFrame({evaluation.KEY: features[evaluation.KEY], "gender": gender})

        bundles = {}
        for name, regularization in (("A", 0.5), ("B", 2.0)):
            feature_names = ["age", "sex_male"]
            matrix = features[feature_names].astype(float)
            matrix['sex_male'] = np.where(np.arange(n) % 2 == 0, 1., 0.)
            imputer = SimpleImputer(strategy="median").fit(matrix)
            transformed = imputer.transform(matrix)
            scaler = StandardScaler().fit(transformed)
            scaled = scaler.transform(transformed)
            model = LogisticRegression(C=regularization, max_iter=500).fit(scaled, y)
            bundles[name] = {"features": feature_names, "imputer": imputer, "scaler": scaler, "model": model}

        primary = features.iloc[: evaluation.PRIMARY_N][[evaluation.KEY, "outcome", "hospitalid"]].copy()
        for name, bundle in bundles.items():
            matrix = features.iloc[: evaluation.PRIMARY_N][bundle["features"]].astype(float)
            primary[f"pred_{name}"] = bundle["model"].predict_proba(
                bundle["scaler"].transform(bundle["imputer"].transform(matrix))
            )[:, 1]

        feature_path = root / "synthetic_features.parquet"
        patient_link_path = root / "synthetic_patient_link.csv"
        primary_path = root / "synthetic_primary_lock.parquet"
        model_a_path = root / "synthetic_model_a.joblib"
        model_b_path = root / "synthetic_model_b.joblib"
        features.to_parquet(feature_path, index=False)
        patient_link.to_csv(patient_link_path, index=False)
        primary.to_parquet(primary_path, index=False)
        dump(bundles["A"], model_a_path)
        dump(bundles["B"], model_b_path)
        return {
            "features_path": feature_path,
            "patient_link_path": patient_link_path,
            "primary_lock_path": primary_path,
            "model_a_path": model_a_path,
            "model_b_path": model_b_path,
            "model_a_sha256": evaluation.sha256_file(model_a_path),
            "model_b_sha256": evaluation.sha256_file(model_b_path),
            "features_sha256": evaluation.sha256_file(feature_path),
            "primary_lock_sha256": evaluation.sha256_file(primary_path),
        }

    def test_complete_synthetic_run_writes_separated_aggregate_and_controlled_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self._make_inputs(root)
            output = evaluation.run_corrected_evaluation(
                **inputs,
                output_path=root / "new_run",
                bootstrap_replicates=5,
                repo_root=ROOT,
            )
            old_primary=pd.read_parquet(inputs['primary_lock_path'])
            new_primary=pd.read_parquet(output/'controlled/eicu_primary_locked_359.parquet')
            self.assertFalse(np.array_equal(old_primary['pred_A'],new_primary['pred_A']))
            self.assertFalse(np.array_equal(old_primary['pred_B'],new_primary['pred_B']))
            full=pd.read_parquet(output/'controlled/eicu_sensitive_corrected_1106.parquet').set_index(evaluation.KEY)
            np.testing.assert_array_equal(new_primary['pred_A'],full.loc[new_primary[evaluation.KEY],'pred_A'])
            self.assertTrue((output / "executed_manifest.json").is_file())
            self.assertTrue((output / "controlled" / "eicu_primary_locked_359.parquet").is_file())
            self.assertTrue((output / "controlled" / "eicu_sensitive_corrected_1106.parquet").is_file())
            self.assertTrue((output / "metrics" / "performance_metrics.csv").is_file())
            self.assertTrue((output / "metrics" / "paired_A_vs_B.csv").is_file())
            self.assertTrue((output / "metrics" / "decision_curve_analysis.csv").is_file())
            manifest = pd.read_json(output / "executed_manifest.json", typ="series")
            self.assertEqual(manifest["status"], "PASS")
            metrics = pd.read_csv(output / "metrics" / "performance_metrics.csv")
            self.assertEqual(set(metrics["dataset"]), {"eICU_primary_locked_359", "eICU_sensitive_corrected_1106"})
            self.assertEqual(set(metrics["metric"]), set(evaluation.METRICS))
            self.assertNotIn(evaluation.KEY, metrics.columns)
            corrected_lock = pd.read_parquet(output / "controlled" / "eicu_sensitive_corrected_1106.parquet")
            self.assertEqual(len(corrected_lock), evaluation.SENSITIVE_N)
            self.assertEqual(int(corrected_lock["outcome"].sum()), evaluation.SENSITIVE_EVENTS)


if __name__ == "__main__":
    unittest.main()
