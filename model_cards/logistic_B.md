# Model card - logistic B (value plus missingness)

- **Status:** frozen primary research model.
- **Intended research use:** same target and evaluation path as logistic A, with pre-specified presence/grouped-missingness features.
- **Input tier:** logistic A values plus frozen missingness indicators; no post-landmark information.
- **Pipeline:** training-fitted imputation, scaling, and ridge logistic regression stored as one frozen object.
- **Object hash:** `7138a646a0391c3d393a99d50aeb7cb7bab7257c15498b77ffaeea94db8c942b`.
- **Evidence boundary:** paired external intervals do not establish stable superiority over A. Missingness associations do not identify clinician intent or causal effects.
- **Primary limitations:** sparse events, internal OOF artifact inconsistency, site-specific missingness semantics, unstable calibration, no prospective evaluation.
- **Prohibited use:** clinical deployment or statements that missingness features clearly improve transport.
- **Availability:** fitted-object redistribution is pending privacy/data-use/licence review.
