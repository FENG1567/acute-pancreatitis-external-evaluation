# Current limitations for the revised manuscript

1. The MIMIC landmark development set has 347 patients and 31 deaths. Ridge penalisation, a reduced representation and 3x3 nested validation make the modelling process inspectable but do not eliminate overfitting.
2. The locked primary eICU evaluation has 359 patients and 21 deaths. Discrimination, calibration, paired differences and clinical-utility estimates therefore have wide uncertainty.
3. Standard binomial-logistic calibration replaced the historical OLS surrogate. The external intercepts and slopes indicate poor absolute-risk transport, but remain imprecise.
4. Corrected keyed MIMIC out-of-fold estimates are post-audit internal diagnostics produced after external results were known. They cannot supply a pre-blinded formal degradation estimate.
5. The eICU priority-only primary phenotype used target-database diagnosis information. The broader and sensitive phenotypes are reported separately, but target-informed selection remains a limitation.
6. The strict diagnosis-time phenotype is not executable because a reliable comparable diagnosis event time is unavailable. It is reported as `NE`, not approximated.
7. The 24-h landmark conditions the estimand on being alive and observed at 24 h. Results do not apply to admission-time prediction, early deaths or early ICU discharge.
8. NWICU mortality could not be independently verified; SICdb has only 17 deaths; HiRID lacks a fit-for-purpose acute-pancreatitis phenotype. None supplies an additional formal external validation.
9. Exact SOFA and BISAP comparisons are unavailable. Missing components were not assigned normal scores, and absence of a pleural-effusion record was not treated as negative evidence.
10. The published XGBoost comparison is a paper-guided reconstruction. Original code, weights, complete mappings and preprocessing were unavailable.
11. Stage-6B masking and decomposition implementations do not estimate a valid causal or fraction-explained quantity. They are retained only in the historical validity table.
12. Measurement presence, extraction availability and semantic mapping are distinct. Structured records cannot identify clinician intent or prove that measurement-process differences caused performance differences.
13. No hospital had enough events for stable centre-specific AUROC or regression. Hospital-cluster bootstrap intervals are sensitivity analyses only.
14. Decision-curve analysis is supportive because the primary external cohort has 21 deaths. The study supplies no clinical-deployment claim.
15. Prospective recalibration, workflow integration, fairness assessment, impact evaluation and software/regulatory validation remain necessary before patient-level use.
16. A public repository DOI, licence and final code release are not yet available and remain explicitly deferred by the user (Minor 10).
