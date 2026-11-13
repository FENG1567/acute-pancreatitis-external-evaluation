## Supplemental Table S1

Note: Eligible denotes the first eligible ICU stay/patient meeting the cohort definition; landmark denotes patients reaching the 24-h landmark; deaths are in-hospital deaths among landmark patients. NE denotes not estimable or not executable and is not zero. OOF denotes out-of-fold predictions. Counts are aggregate first eligible ICU stays/patients.

## Supplemental Table S2

Note: Presence is the proportion with at least one eligible measure, and rate/h is the median measures per hour among observed patients. NE denotes not estimable or not structurally comparable and is not zero measurement. These comparisons are descriptive and do not identify clinician intent, a causal measurement-process effect, or a care-quality difference.

## Supplemental Table S3

Note: Corrected eICU estimates use the prespecified frozen models after harmonising source sex labels to the model coding (Male=1, Female=0). Original all-zero mapping rows show point estimates only for comparison with the corrected evaluation. For corrected estimates, confidence intervals are patient-bootstrap 95% intervals; hospital-cluster sensitivity intervals are summarised in the main text for AUROC. Calibration-in-the-large was estimated with the predicted logit as an offset and slope fixed at 1. Joint intercept and slope were estimated together in a logistic-recalibration model. NE, not estimated for the secondary internal diagnostic.

## Supplemental Table S4

Note: The three MIMIC-IV outer validation folds contain 116 patients with 10 deaths, 116 with 11 deaths, and 115 with 10 deaths, respectively. Estimates describe individual held-out folds; pooled out-of-fold estimates are reported in Supplemental Table S3. Fold indices are 0, 1 and 2. C is the inverse regularisation strength. Model complexity is the approximate ridge effective degrees of freedom.

## Supplemental Table S5

Note: Log loss is reported for each inner validation fold at each candidate C within each outer training fold. C is the inverse regularisation strength; the selected C for each model and outer fold is shown in bold and reported in Supplemental Table S4. Fold indices are 0, 1 and 2.

## Supplemental Table S6

Note: Differences are Model A minus Model B, calculated using the same patient-bootstrap samples; confidence intervals are 95% percentile intervals. Positive differences favour Model A for AUROC and AUPRC and Model B for Brier score and log loss. Calibration-in-the-large and the jointly estimated calibration intercept are reported separately. Hospital-cluster intervals for external AUROC and AUPRC are shown in Supplemental Figure S3. Intervals spanning zero are compatible with differences in either direction and do not establish equivalence.

## Supplemental Table S7

Note: Missing score components were not assigned normal values, and absence of a pleural-effusion mention was not treated as evidence that effusion was absent. SOFA, Sequential Organ Failure Assessment; BISAP, Bedside Index for Severity in Acute Pancreatitis.

## Supplemental Table S8

Note: Coefficients are from the transformed predictor space in each MIMIC-IV outer training fold. Model B had 47 declared and 46 transformed features after removal of the all-missing GCS measurement-presence indicator. NA denotes a predictor not included in that model, not a coefficient of zero. Fold indices are 0, 1 and 2. GCS, Glasgow Coma Scale; BUN, blood urea nitrogen; MAP, mean arterial pressure; SpO2, peripheral oxygen saturation.
