# Public output dictionary

The current metric registry is `final/source_of_truth_metrics.csv`; result IDs link to `final/result_traceability.csv`. `source_kind` distinguishes the external reevaluation from the internal development summaries. Blank intervals are unavailable, not zero.

`calibration_in_the_large` fixes the prediction-logit coefficient at one. `calibration_intercept` and `calibration_slope` are joint logistic-recalibration parameters. `scaled_brier` uses the observed-prevalence constant-risk reference. Full-precision outputs include effective bootstrap counts. Display tables preserve author rounding and NE labels. Database variable-level mappings are under `ontology/`; no patient records are included.
