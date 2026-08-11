# Public snapshot runbook

1. Create the environment from `environment/environment.yml` or install the locked dependencies in `environment/requirements.lock`.
2. Copy `config/paths.example.yaml` to a private local configuration only after obtaining approved source-data access. Keep that local configuration outside version control.
3. Run the public aggregate validation:

```powershell
py -3.12 scripts/run_public_snapshot.py
py -3.12 -m py_compile scripts/*.py code/*.py tests/*.py
```

4. Review `final/source_of_truth_metrics.csv`, `final/result_traceability.csv`, the aggregate `tables/` and `source_data/`, and the current figure outputs.

The public snapshot deliberately does not execute a patient-level reconstruction. `scripts/revise_final2_figures.py --figure all` rebuilds all eight publication figures from packaged aggregate inputs only, writing PDF/PNG outputs only beneath `figures/` and `supplementary/figures/`. No controlled prediction or fitted-model artifact is included.

Before public release, the authors must select a licence. No licence or repository DOI is asserted in this package.
