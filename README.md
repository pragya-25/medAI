# AI-Assisted Medical Imaging and Diagnosis System

> ⚠️ **FOR EDUCATION ONLY. NOT FOR CLINICAL USE.** This is a student project. Do not use it to make medical decisions.

Chest X-ray pneumonia detection (RSNA dataset) with Grad-CAM explanations, an Orthanc DICOM server, and a React viewer where a radiologist approves or rejects each AI result.

## Structure
- `ml/` – DICOM utilities, preprocessing, training, Grad-CAM
- `notebooks/` – Colab notebooks (training runs on Colab GPU)
- `service/` – Orthanc poller + inference API
- `viewer/` – React app
- `docs/` – architecture, API docs, model card
- `tests/` – unit tests

## Progress
- [x] Step 1: Setup, dataset choice, DICOM basics
- [ ] Step 2: Preprocessing and DVC
- [ ] Step 3: Training
- [ ] Step 4: Grad-CAM
- [ ] Step 5: Orthanc + inference service
- [ ] Step 6: React viewer + audit log
- [ ] Step 7: Docker + model card
