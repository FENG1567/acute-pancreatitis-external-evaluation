# Protocol amendment A-7-01: clinical-score computability correction

Status: required correction after independent Stage-7 source-table audit.

- Stage-5 MIMIC BISAP converted missing BUN/GCS/age/SIRS/effusion evidence to Boolean `False`, creating an invalid 347/347 complete-rate claim. The corrected Stage-7 bounds retain missing components as unknown.
- Stage-5 MIMIC SOFA `scan_extra` did not filter vasopressor, ventilation, or urine events to the pre-specified 0--24 h window. These Stage-5 SOFA scores are not valid landmark score results and are superseded for reporting by the Stage-7 audit status.
- Stage-6 eICU code hard-coded GCS and respiratory components unavailable although eICU source tables contain them. The corrected Stage-7 eICU output re-extracts time-indexed PaO2/FiO2 where available and uses existing time-indexed GCS features; exact scoring remains unavailable where support status, units, or time semantics do not resolve it.
- Pleural-effusion absence is not inferred from absence of an unstructured text mention in either database.

Affected prior score-computability claims and score tables must be marked superseded. This amendment does not retrain a model, alter a frozen cohort, or change locked external predictions.
