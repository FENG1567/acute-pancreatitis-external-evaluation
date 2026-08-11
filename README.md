# Acute pancreatitis external-evaluation reproducibility materials

This repository is a public, aggregate-level companion to the manuscript on external degradation of a 24-hour landmark acute-pancreatitis risk model. It contains the current aggregate result registry, publication tables and figures, figure source data, model cards, cohort/ontology specifications, and selected public build and validation materials.

## Scope and access boundary

MIMIC-IV, eICU, NWICU, SICdb, and HiRID source data are not redistributed here. Obtain each source under its own access and licence terms, then set local paths in `config/paths.example.yaml`; do not commit local paths, credentials, patient-level extracts, prediction files, hospital identifiers, or fitted model objects. Controlled predictions and model artifacts are intentionally not public.

The public snapshot supports inspection of the aggregate evidence and integrity validation. Full patient-level re-analysis is deliberately out of scope because it requires controlled inputs that are not distributed. The current numerical source of truth is `final/source_of_truth_metrics.csv`; result links are in `final/result_traceability.csv`.

## Quick start

Use Python 3.12 (dependencies: `environment/requirements.lock` or `environment/environment.yml`).

```powershell
py -3.12 scripts/run_public_snapshot.py
py -3.12 scripts/revise_final2_figures.py --figure all
py -3.12 -m py_compile scripts/*.py code/*.py tests/*.py
```

`run_public_snapshot.py` validates that the public aggregate registry and figure-source files are present and readable. `scripts/revise_final2_figures.py --figure all` rebuilds all five main and three supplementary figures directly from `final/` and `source_data/`, writing only repository-local PDF/PNG files under `figures/` and `supplementary/figures/`. It does not require, read, or write licensed raw data.

## Layout

- `final/`: source-of-truth metrics, result traceability, and claim-evidence registry.
- `tables/`, `supplementary/tables/`, `source_data/`: current aggregate manuscript outputs and plot inputs.
- `figures/`, `supplementary/figures/`: current publication figures (PDF/PNG).
- `cohort/`, `ontology/`, `data_dictionary/`, `model_cards/`: public specifications and documentation.
- `config/`, `environment/`, `scripts/`, `tests/`: reproducibility configuration, dependencies, and public validation code.
- `reporting/`, `provenance/`, `audits/`, `figure_contracts/`: method, reporting, and traceability materials.

## Citation and licence

Please cite the associated manuscript once bibliographic details are available. No repository DOI has been assigned. A licence has not yet been selected by the authors; do not assume reuse permission until they add one.
