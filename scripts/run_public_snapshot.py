#!/usr/bin/env python3
"""Validate that the public aggregate reproducibility snapshot is complete.

This script deliberately reads no patient-level data, controlled predictions,
fitted model objects, credentials, or local data paths.
"""
from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "final/source_of_truth_metrics.csv",
    "final/result_traceability.csv",
    "final/claim_evidence_matrix.csv",
    "source_data/fig1_design_and_cohort_flow.csv",
    "source_data/fig5_phenotype_cluster_paired_robustness.csv",
    "tables/table1_cohort_flow_and_roles.csv",
    "supplementary/tables/table_s1_outer_fold_performance_and_complexity.csv",
)


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        raise SystemExit("Missing public files: " + ", ".join(missing))
    for name in REQUIRED:
        with (ROOT / name).open("r", encoding="utf-8-sig", newline="") as handle:
            if not next(csv.reader(handle), None):
                raise SystemExit(f"No header row: {name}")
    print(f"Public aggregate snapshot validated ({len(REQUIRED)} required files).")


if __name__ == "__main__":
    main()
