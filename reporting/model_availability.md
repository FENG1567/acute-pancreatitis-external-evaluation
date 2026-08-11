# Model availability statement

Frozen research pipelines exist for logistic A, logistic B, exploratory logistic C, and the paper-guided XGBoost reconstruction. Their cryptographic hashes are recorded in `models/model_hash_registry.csv`.

Public release of fitted model objects is **pending** final privacy, data-use-agreement, and licence review. Model weights may encode information learned from controlled clinical databases; the existence of a local object does not by itself establish that it can be redistributed.

If models are deposited, the release must include feature order, preprocessing, expected units, missing-input behaviour, software versions, training-data provenance at an aggregate level, intended-use limitations, and object hashes. The paper-guided reconstruction must remain clearly separated from the unavailable published model object.

None of the models is authorised for clinical deployment. They require larger independent validation, recalibration, prospective evaluation, impact assessment, software assurance, and appropriate governance before any patient-level use.
