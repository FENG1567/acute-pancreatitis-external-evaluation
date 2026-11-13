#!/usr/bin/env python3
"""Run the eICU external evaluation on authorized controlled files.

This command is intended for the original authorized analysis server. It does
not discover source data, access a database, or fit/refit the frozen models.
Provide trusted model SHA-256 digests obtained independently of the model
files before allowing joblib to load them.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from external_evaluation import run_corrected_evaluation  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Recompute corrected primary/sensitive eICU metrics from explicitly supplied "
            "controlled inputs. Patient-keyed outputs are isolated under controlled/."
        )
    )
    parser.add_argument("--features", type=Path, required=True, help="controlled 1106-row sensitive feature Parquet")
    parser.add_argument("--patient-link", type=Path, required=True, help="private CSV with raw_icu_stay_id_hash and gender columns")
    parser.add_argument("--primary-lock", type=Path, required=True, help="existing locked 359-row primary prediction Parquet")
    parser.add_argument("--model-a", type=Path, required=True, help="trusted frozen Model A joblib bundle")
    parser.add_argument("--model-b", type=Path, required=True, help="trusted frozen Model B joblib bundle")
    parser.add_argument("--model-a-sha256", required=True, help="trusted expected SHA-256 for Model A")
    parser.add_argument("--model-b-sha256", required=True, help="trusted expected SHA-256 for Model B")
    parser.add_argument("--features-sha256", required=True, help="trusted expected SHA-256 for sensitive feature checkpoint")
    parser.add_argument("--primary-lock-sha256", required=True, help="trusted expected SHA-256 for original primary lock")
    parser.add_argument("--output", type=Path, required=True, help="new, nonexistent output directory outside repository source/raw-data directories")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        output = run_corrected_evaluation(
            features_path=args.features,
            patient_link_path=args.patient_link,
            primary_lock_path=args.primary_lock,
            model_a_path=args.model_a,
            model_b_path=args.model_b,
            model_a_sha256=args.model_a_sha256,
            model_b_sha256=args.model_b_sha256,
            features_sha256=args.features_sha256,
            primary_lock_sha256=args.primary_lock_sha256,
            output_path=args.output,
            repo_root=ROOT,
        )
    except (OSError, RuntimeError, ValueError, ImportError) as error:
        parser.exit(2, f"error: corrected eICU evaluation failed: {error}\n")
    print(f"PASS: corrected eICU evaluation completed; outputs written to {output}")
    print(f"Manifest: {output / 'executed_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
