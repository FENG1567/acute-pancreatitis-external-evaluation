# Protocol amendment A-7-03: internal logistic OOF invalidation

Status: P0 correction after Stage-7 independent audit.

`stage5_models.py` constructed logistic OOF summaries with `np.array(list(v.values()))` while the outcome vector remained in population (`pids`) order. The dictionary was populated fold-by-fold, and the two orders differ at 346/347 positions. Thus `modeling/oof_summary.csv` logistic A/B/C values (0.5439/0.5302/0.5526) are prediction-outcome misaligned and invalid. The commonly cited 0.891 value is instead an unweighted mean of the three held-out fold AUROCs, not pooled OOF performance.

No patient-level logistic OOF predictions were saved. Stage 7 does not refit models, so correctly aligned pooled OOF performance cannot be recovered. All pooled logistic internal-performance claims are NO-GO; do not cite 0.891 in the manuscript or compare external eICU AUROC against an internal pooled OOF reference. Fold-specific AUROCs remain descriptive supplementary outputs only and must state 31 development events.

Evidence: `audits/stage7_internal_oof_discrepancy_audit.csv`; superseding source-of-truth result `R7_INTERNAL_OOF_VALIDITY_STATUS`.
