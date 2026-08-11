"""Public release assertions for the post-audit aggregate result package."""
from __future__ import annotations

import csv
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parent


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


class Stage7ReleaseTests(unittest.TestCase):
    def test_roles_and_historical_boundaries_are_explicit(self):
        data = rows(PACKAGE / "final" / "source_of_truth_metrics.csv")
        roles = {x["result_role"] for x in data}
        self.assertTrue({"primary_locked_external", "post_audit_corrected_internal", "post_audit_sensitivity", "historical_invalid"}.issubset(roles))
        historical = next(x for x in data if x["result_id"] == "R8_HISTORICAL_STAGE6B_IMPLEMENTATION_AUDIT")
        self.assertIn("provenance only", historical["interpretation"])
        minor = next(x for x in data if x["result_id"] == "R8_MINOR10_PUBLIC_REPOSITORY_DOI_LICENSE")
        self.assertEqual(minor["result_role"], "deferred")

    def test_current_table_index_prevents_legacy_misuse(self):
        text = (ROOT / "03_主表" / "README_CURRENT_TABLES.md").read_text(encoding="utf-8")
        self.assertIn("table2_primary_and_corrected_internal_performance", text)
        self.assertIn("superseded", text)

    def test_current_display_tables_resolve_result_ids(self):
        ids = {x["result_id"] for x in rows(PACKAGE / "final" / "source_of_truth_metrics.csv")}
        current = [
            ROOT / "03_主表" / "table1_cohort_flow_and_roles.csv",
            ROOT / "03_主表" / "table2_primary_and_corrected_internal_performance.csv",
            ROOT / "03_主表" / "table3_phenotype_sensitivity.csv",
            ROOT / "03_主表" / "table4_model_complexity.csv",
            ROOT / "03_主表" / "table5_patient_cluster_and_paired_AB.csv",
            ROOT / "03_主表" / "table6_historical_validity.csv",
            ROOT / "04_补充材料" / "补充表" / "table_s1_outer_fold_performance_and_complexity.csv",
            ROOT / "04_补充材料" / "补充表" / "table_s2_inner_C_search.csv",
            ROOT / "04_补充材料" / "补充表" / "table_s3_paired_A_vs_B_all.csv",
            ROOT / "04_补充材料" / "补充表" / "table_s4_corrected_internal_external_differences.csv",
            ROOT / "04_补充材料" / "补充表" / "table_s5_clinical_score_computability.csv",
            ROOT / "04_补充材料" / "补充表" / "table_s6_fold_coefficient_mapping.csv",
        ]
        for path in current:
            self.assertTrue(path.exists(), path)
            for row in rows(path):
                for result_id in row.get("result_ids", row.get("result_id", "")).split(";"):
                    if result_id:
                        self.assertIn(result_id, ids, (path, result_id))


if __name__ == "__main__":
    unittest.main()
