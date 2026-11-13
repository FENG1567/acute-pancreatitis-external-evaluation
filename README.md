# Acute pancreatitis external-evaluation reproducibility materials

Companion materials for **External performance, calibration, and cross-database measurement-process differences in acute pancreatitis mortality models: a 24-h landmark multi-database study** (BMJ Health & Care Informatics, manuscript bmjhci-2026-102482; revision materials, 12 November 2026).

This release contains the current submitted main Table 1 (panels A and B), Supplemental Tables S1–S8, four main and four supplemental figures, their available aggregate sources, and the frozen-model external-evaluation code. The eICU evaluation was run on the original authorized analysis server. It preserves model coefficients, imputation, scaling, cohort membership, and outcomes; only the source sex-label mapping was corrected (Male/M=1, Female/F=0).

## Quick start

Use Python 3.12. Install `environment/requirements.txt` in a dedicated environment. The exact server versions are recorded in `provenance/external_evaluation_manifest.json` and `environment/server_evaluation.lock`.

```bash
python scripts/run_public_snapshot.py
python -m unittest discover -s tests -v
python scripts/revise_final2_figures.py --figure all
```

The first command checks the file inventory against `PACKAGE_MANIFEST.csv`. The numerical tests use synthetic data. The last command makes PNG previews from the supplied TIFF files; it does **not** recreate original figure design or numerical results. Submitted PDFs/TIFFs are preserved unchanged.

## Contents and evidence roles

- `final/source_of_truth_metrics.csv`: current eICU metrics, plus explicitly labelled secondary MIMIC internal summaries.
- `source_data/recomputed_external/`: full-precision external metrics, paired A-minus-B contrasts and decision curves from the server run.
- `tables/`, `supplementary/tables/`: current author display tables and notes, exported without changing their values; `source_data/submitted/` retains supplied full-precision supplement CSVs.
- `figures/`, `supplementary/figures/`: the submitted four main and four supplemental TIFF/PDF figure files, with preview PNGs and legends where supplied.
- `code/external_evaluation.py`, `scripts/recompute_corrected_external.py`: corrected external evaluation from controlled frozen checkpoints. Calibration-in-the-large fixes the slope at 1; joint calibration intercept and slope are reported separately.
- `cohort/`, `ontology/`, `data_dictionary/`: retained study specifications; table and figure numbering in this README and the current exports takes precedence over older stage labels in technical definitions.
- `reporting/`: author-provided current research-reporting checklist.
- `provenance/`: source hashes, figure and table sources, and software versions.

## Controlled reproduction

Raw MIMIC-IV/eICU/NWICU/SICdb/HiRID data, patient-level features, predictions, hospital identifiers, and fitted model objects are not distributed. Researchers must obtain their own authorized source access. This repository provides checkpoint-based external reevaluation, not a self-contained redistribution of the licensed raw-data pipeline. See `RUNBOOK.md` and `DATA_ACCESS.md` for required private inputs.

## Citation and licence

Cite the associated manuscript when final bibliographic details are available. No repository DOI is asserted. The authors have not selected a code licence; this update does not assign one. Data access terms are separate from code licensing.
