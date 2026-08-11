# Protocol amendment A-7-02: standard calibration and bootstrap correction

Status: required correction after independent Stage-7 audit. No model, cohort, or locked prediction was changed.

Stage-6 calibration intercept/slope values were derived by ordinary least squares with a binary outcome, rather than the pre-specified/standard binomial logistic calibration model `logit(Y)=alpha+beta*logit(p)`. Consequently, Stage-6 calibration metrics, their bootstrap intervals, and any downstream calibration- or recalibration-dependent output are invalidated for submission use. This includes `validation/primary_external_metrics.csv` calibration columns, `validation/external_metric_bootstrap.csv` calibration rows, `validation/calibration_metrics.csv` as an unvalidated plotted artifact, and `degradation/recalibration_intercept_results.csv`. They remain preserved immutable historical artifacts.

Independent Stage-6B code audit also invalidates the degradation decomposition for manuscript claims: the intercept update is invalid; case-mix weights were applied to eICU and never used to calculate performance and its ESS formula is wrong; value alignment is descriptive only; target masking did not change predictions because process NaNs were median-imputed back to one while values remained available; domain occlusion only replaces process features; and the hospital-level file fits no regression with zero hospitals meeting threshold. The affected files (`degradation/recalibration_intercept_results.csv`, `case_mix_weights.parquet`, `case_mix_overlap_audit.csv`, `value_alignment_sensitivity.csv`, `masking_runs.parquet`, `masking_positivity_audit.csv`, `domain_occlusion_results.csv`, `hospital_level_model.csv`, and `hospital_measurement_distance.csv`) are preserved but invalid-for-claim. Masking fraction explained is not estimable because of an implementation failure, not a scientific negative result.

Stage 7 recomputes alpha and beta independently from the locked prediction file using statsmodels binomial GLM, unpenalized sklearn logistic regression, and a separate Newton implementation for bootstrap estimation. Patient-level and hospital-cluster sensitivity percentile intervals are recorded. A/B are primary; C and paper reconstruction remain exploratory.

## Before/after calibration values

| model | metric | stage6_value | stage7_standard_binomial_value | stage7_ci_low | stage7_ci_high | reason |
| --- | --- | --- | --- | --- | --- | --- |
| A | calibration_intercept | 0.192726124815267 | -1.4756180269782149 | -2.1442769120200587 | -0.8178064738695767 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| A | calibration_slope | 0.0310164542544516 | 0.4458554784294361 | 0.30713483375409967 | 0.6472336746821835 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| B | calibration_intercept | 0.1945785700965809 | -1.372968816459665 | -2.006844190407555 | -0.7097441631179805 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| B | calibration_slope | 0.0285559000601292 | 0.4326424847572626 | 0.29805027304243964 | 0.6421412795631644 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| C | calibration_intercept | 0.1288992226692783 | -2.2464171514899305 | -2.85190377746683 | -1.7644791645969737 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| C | calibration_slope | 0.0065532153570041 | 0.06989910195369733 | 0.04562130685129563 | 0.10740472314557584 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| paper | calibration_intercept | 0.3636927008628845 | 1.9316412239688985 | 0.057206193620395994 | 4.0135457236615 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
| paper | calibration_slope | 0.0568624325096607 | 0.9475006702531528 | 0.5835377924786892 | 1.4173678499717182 | Stage 6 used OLS(binary outcome ~ logit prediction); Stage 7 uses standard binomial logistic calibration. |
