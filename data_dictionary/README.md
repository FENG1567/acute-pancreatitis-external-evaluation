# Stage-7 data dictionary

This directory documents shareable output schemas. It does not contain a patient-level data dictionary for redistribution. Database-specific mappings remain in `ontology/variable_map.csv`, and the measurement-feature contract remains in `features/process_feature_dictionary.json`.

- `stage7_output_dictionary.csv` defines the unique metric registry, traceability registry, claim-evidence matrix, and manuscript template tokens.
- Values used in manuscript text, tables, or figures must resolve through a registered `result_id`.
- Blank confidence limits mean that a valid interval was not registered; they must not be displayed as zero or inferred.
- `result_role` determines whether a result is primary, exploratory, descriptive, superseded, or invalid-for-claim.
- Patient identifiers, source text, and row-level predictions are excluded from the public reporting dictionary.
