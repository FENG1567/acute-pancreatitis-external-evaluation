# Reproduction runbook

## Public checks

Run `python scripts/run_public_snapshot.py` from this repository to check the file inventory against the manifest. `python -m unittest discover -s tests -v` runs the numerical and input-safety tests. The inventory check uses only the standard library; numerical tests need the dependencies below.

## Authorized frozen-checkpoint reevaluation

Run on the authorized analysis server, in a dedicated Python environment compatible with the frozen bundles (scikit-learn 1.9.0 for this release). Do not load arbitrary joblib files: joblib uses executable pickle semantics. Obtain trusted expected hashes independently before executing this command.

```bash
python scripts/recompute_corrected_external.py \
  --features /private/inputs/sensitive_features.parquet \
  --patient-link /private/inputs/patient_link.csv \
  --primary-lock /private/inputs/original_primary_lock.parquet \
  --model-a /private/models/logistic_A.joblib \
  --model-b /private/models/logistic_B.joblib \
  --features-sha256 TRUSTED_FEATURE_SHA256 \
  --primary-lock-sha256 TRUSTED_ORIGINAL_LOCK_SHA256 \
  --model-a-sha256 TRUSTED_MODEL_A_SHA256 \
  --model-b-sha256 TRUSTED_MODEL_B_SHA256 \
  --output /private/runs/new_corrected_run
```

The output directory must not exist. The private link CSV has columns `raw_icu_stay_id_hash,gender`, exactly one row per sensitive-cohort key. The code first reproduces baseline primary predictions within absolute floating-point tolerance 1e-15, then corrects sex on a copy of the feature table, without fitting or tuning a model. Corrected primary predictions are the keyed subset of the corrected sensitive predictions. It calculates patient and hospital-cluster percentile intervals with 2,000 draws each, paired A-minus-B contrasts, and decision curves at thresholds 0.01–0.30. Repeated sampled clusters retain all repeated rows. All input hashes are pinned or recorded, and checked again before success.

Output `controlled/` is private. `metrics/` contains aggregate CSVs; `executed_manifest.json` records input hashes, definitions, seeds, code hashes and software versions. Invalid joint-calibration fits (non-identifiable, separated or unconverged) are excluded only from that metric's interval; effective replicate counts are reported. The current executed release has 2,000 valid draws for every reported metric.

## Figures and tables

The submitted table CSVs preserve author display precision and NE values. Full-precision server summaries are separate, so rounded display tables are not represented as raw analysis outputs. `scripts/revise_final2_figures.py --figure all` converts submitted TIFFs to PNG previews. It does not rerender the original multi-panel layout from data. Figure data and their provenance remain available for independent numerical plots.

Do not overwrite supplied source files or reuse an existing analysis output directory. Changing inputs or methods constitutes a new run, not a check of this release.
