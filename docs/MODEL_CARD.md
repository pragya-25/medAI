# Model Card: Chest X-ray Pneumonia Classifier

> **FOR EDUCATION ONLY. NOT FOR CLINICAL USE.** This model was built as a student project. It has not been
> clinically validated, is not a medical device, and must never inform diagnosis or treatment.

## Model details
| | |
|---|---|
| Architecture | DenseNet121, ImageNet-pretrained, final layer replaced with 1 output (binary) |
| Framework | PyTorch / torchvision |
| Input | Single frontal chest X-ray, resized to 224×224, grayscale replicated to 3 channels, ImageNet normalization |
| Output | Probability of "pneumonia-like lung opacity", plus a Grad-CAM heatmap |
| Training | 6 epochs, AdamW (lr 1e-4, cosine schedule), weighted BCE loss (`pos_weight` about 3.4), mixed precision, on a Colab T4 |
| Augmentation | Rotation about ±10°, zoom 0.9–1.1, contrast (gamma 0.8–1.2). No horizontal flip (it would put the heart on the wrong side). |

## Intended use
- Learning exercise on medical-imaging pipelines: DICOM handling, transfer learning, explainability, human-in-the-loop review.
- A demonstration of a radiologist-in-the-loop workflow with audit logging.

**Out of scope:** any real patient care, screening, triage, or second-reader use; pediatric patients; CT/MRI; any dataset or scanner other than the one described below.

## Data
- **RSNA Pneumonia Detection Challenge** (Kaggle): 26,684 frontal chest X-ray DICOMs, with bounding boxes for lung opacities. The images come from the NIH ChestX-ray14 collection.
- Binary label per patient: 1 if at least one pneumonia bounding box exists (22.5% positive), else 0.
- Split **by patient**, stratified: train 18,678 / validation 4,003 / test 4,003 (70/15/15, seed 42). Each split has the same 22.5% positive rate.
- Data is versioned with DVC. Raw data and weights are not stored in git.

## Performance (held-out test set, n = 4,003)
The decision threshold (0.338) was chosen **on the validation set** (Youden's J) and applied once to the test set.

| Metric | Value |
|---|---|
| AUROC (test) | **0.883** (validation 0.873) |
| Sensitivity (recall) | 86.0% (776 / 902) |
| Specificity | 72.9% (2,261 / 3,101) |
| Precision (PPV) | 48.0% (776 / 1,616) |
| Negative predictive value | 94.7% (2,261 / 2,387) |
| Accuracy | 75.9% |

Confusion matrix (rows = truth, columns = prediction):

| | Predicted normal | Predicted pneumonia |
|---|---|---|
| **Actually normal** | 2,261 | 840 |
| **Actually pneumonia** | 126 | 776 |

**How to read this:** about half of the positive flags are false alarms (PPV 48%), and 14% of true pneumonia cases are missed (126 of 902). The threshold favors sensitivity at the cost of specificity. A different threshold changes this trade-off. Accuracy alone is misleading here, because always predicting "normal" would score 77.5%.

## Limitations
1. **Label noise and definition.** RSNA labels come from radiologist annotation of "lung opacity", which also occurs in non-pneumonia conditions (edema, atelectasis, cancer). The label is a proxy for pneumonia, not a confirmed diagnosis. The "negative" class also mixes normal and abnormal-but-not-pneumonia studies.
2. **Single source, no external validation.** Train and test come from the same hospital collection. Performance on other hospitals, scanners, or protocols is unknown and is likely to be lower.
3. **Image quality.** Images are downsampled from 1024×1024 to 224×224, so small or subtle findings can be lost. The DICOMs are 8-bit, lossy JPEG-compressed secondary captures, not raw detector data.
4. **Uncalibrated scores.** The output is a sigmoid score, not a calibrated probability. "98%" does not mean a 98% chance of disease.
5. **Single image, no context.** The model sees no clinical history, prior studies, lateral view, or symptoms. A real radiologist always does.
6. **Grad-CAM is coarse and not proof.** The heatmap comes from a 7×7 feature map upsampled to the image. It indicates regions that increased the score; it does not outline the lesion and does not prove the model's reasoning is clinically valid. In the examples we checked, the highlights overlapped the annotated boxes in most positive cases but missed one case entirely (false negative, P = 0.15, heat outside the lungs).
7. **Possible shortcut learning.** Portable/AP films, support devices, and text markers correlate with sicker patients. The model may partly use such cues rather than lung findings. We did not run controlled tests for this.
8. **Limited training.** 6 epochs, no hyperparameter search, no ensembling, no repeated runs, so there is no confidence interval on the reported metrics.

## Bias and fairness
- **Not evaluated.** We did **not** measure performance by sex, age, race, or hospital site. The DICOM headers contain sex and age, so subgroup analysis is possible, and it is a necessary next step. Until it is done, nothing can be claimed about equal performance across groups.
- **Known risks in this kind of data:** (a) the NIH collection comes from a single US academic center, so the patient population is not representative of the world; (b) acquisition view (AP vs PA) and patient condition are correlated with the label, which can bias the model toward sicker-looking or bedside patients; (c) published studies of chest X-ray models have found lower sensitivity for under-represented groups, so the same risk should be assumed here.
- **Automation bias.** A confident heatmap can make a reviewer over-trust the AI. The interface therefore requires an explicit radiologist decision, shows the threshold, and logs every decision with the model version.

## Human oversight and logging
Every AI result starts as `pending`. A named reviewer must approve or reject it. Each decision is written to an append-only audit log (reviewer, decision, timestamp, model version, probability, comment) in the same database transaction as the status change.

## Recommendations for future work
Subgroup performance analysis; external validation on another dataset (for example CheXpert or NIH labels); probability calibration; threshold analysis across operating points; multiple training seeds with confidence intervals; testing for shortcut cues (masking text and devices); higher input resolution.

## Contact / citation
Student project. Dataset: RSNA Pneumonia Detection Challenge (Kaggle), RSNA, Kaggle, and NIH ChestX-ray14. Please follow each dataset's terms of use.
