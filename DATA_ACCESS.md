# Data access

This public package contains aggregate statistics and publication figures only. Original databases require their own training, access approvals and data-use agreements. Those permissions are not granted by this repository.

Controlled reevaluation requires the original trusted frozen Model A/B bundles (feature order, imputer, scaler and estimator), the 1,106-person sensitive landmark feature checkpoint, the original 359-person primary lock, and a private key-to-source-gender linking file. No such patient-level or serialized-model files are included here. SHA-256 hashes verify artifact identity, not permission to share data.

The CLI writes patient-keyed revised locks only under its separate `controlled/` output. Never upload that directory, raw data, private input paths, credentials or hospital identifiers. Only aggregate files under the run's `metrics/` and the non-identifying manifest may be published after review. Unknown gender labels remain missing for the frozen imputer; unrecognized categories fail rather than being silently coded female.
