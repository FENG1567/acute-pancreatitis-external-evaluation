# Model card - paper-guided XGBoost reconstruction

- **Status:** frozen exploratory paper-guided reconstruction.
- **Object hash:** `4c4a337e6e53632bc0ad31dbb34f40df2fed76df2cfaffb46de217319a6785a6`.
- **Construction:** built from the published article and supplement using fixed reported hyperparameters and project-specific assumptions recorded in `published_model/`.
- **Unavailable source material:** original training code, trained weights, complete cohort code, exact item mappings, full KNN details, abnormal-value rules, and all selection/splitting details.
- **Naming rule:** always "paper-guided reconstruction" or "published-model reconstruction."
- **Interpretation boundary:** its performance belongs to this reconstruction and cannot be attributed to the unavailable published model object.
- **Additional bias concern:** the source publication's reported external-validation/round-selection description may permit target-set model selection and is not treated as a blind gold-standard benchmark.
- **Prohibited use:** clinical deployment or attribution to the original model object.
- **Availability:** fitted-object redistribution is pending privacy/data-use/licence review.
