# Model card - logistic A (value-only)

- **Status:** frozen primary research model.
- **Intended research use:** retrospective landmark prediction of in-hospital mortality among eligible ICU acute-pancreatitis patients and locked cross-database performance evaluation.
- **Input tier:** frozen value summaries only, using the Stage-5 reduced first/worst representation and recorded feature order.
- **Pipeline:** training-fitted imputation, scaling, and ridge logistic regression stored as one frozen object.
- **Object hash:** `dcad29590d644f0ffa11df8c8149d8b133d29cd429a2ebc0b51e77c7c8e82750`.
- **Primary limitations:** sparse development/external events, internal OOF artifact inconsistency, cross-database value/measurement semantics, unstable calibration, no fairness or prospective impact evaluation.
- **Missing inputs:** use only the frozen preprocessing rules; do not manually set unknown measurements to normal.
- **Prohibited use:** patient-level clinical decisions, autonomous triage, deployment outside the audited schema, or claims of causal measurement-process effects.
- **Availability:** fitted-object redistribution is pending privacy/data-use/licence review.
