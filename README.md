# AI-Assisted Medical Imaging and Diagnosis System

> ## ⚠️ FOR EDUCATION ONLY. NOT FOR CLINICAL USE.
> This is a student project. It is not a medical device and has not been clinically validated.
> Never use it to diagnose, treat, or make decisions about real patients.

A platform where chest X-rays are uploaded to an **Orthanc** DICOM server, analysed by a **PyTorch** deep-learning model,
shown with **Grad-CAM** explanation heatmaps in a **React** viewer, and reviewed by a radiologist who approves or rejects
each result. Every decision is written to an audit log.

## Results (RSNA Pneumonia, held-out test set, 4,003 patients)
| Metric | Value |
|---|---|
| AUROC | **0.883** |
| Sensitivity / Specificity | 86.0% / 72.9% (threshold 0.338, chosen on validation) |
| Precision (PPV) / NPV | 48.0% / 94.7% |

Limits, bias and caveats: **[docs/MODEL_CARD.md](docs/MODEL_CARD.md)**. Read it before drawing conclusions.

## Architecture
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (diagrams) and [docs/API.md](docs/API.md) (endpoints).

```
DICOM -> Orthanc -> worker (DenseNet121 + Grad-CAM) -> SQLite <- FastAPI <- React viewer <- Radiologist
```

## Tech stack
PyTorch · MONAI (augmentation transforms) · torchvision DenseNet121 · Grad-CAM · Orthanc · DVC · FastAPI · React (Vite) · Docker

## Repository layout
| Path | Contents |
|---|---|
| `ml/` | DICOM utils, dataset and augmentation, training, Grad-CAM |
| `notebooks/` | Colab notebooks 01–04 (data, preprocessing + DVC, training, Grad-CAM) |
| `service/` | Orthanc worker, inference, API, database |
| `viewer/` | React app |
| `tools/` | `upload_dicom.py` |
| `tests/` | pytest suite |
| `docs/` | Model card, architecture, API |

## Quick start (Docker)
Requirements: Docker Desktop (running).

1. Get the trained weights. Place `best.pt` and `metrics.json` in `service/models/`
   (they are produced by `notebooks/03_train.ipynb` and saved to `MyDrive/medai_ckpt`; weights are not stored in git).
2. Start everything:
   ```
   docker compose up --build
   ```
3. Upload DICOM files (needs Python and `pip install requests`):
   ```
   python tools/upload_dicom.py path/to/dicom_folder
   ```
4. Open the viewer at **http://localhost:8080**. Orthanc is at http://localhost:8042 and the API docs at http://localhost:8000/docs.

## Run without Docker for the app (development)
```
pip install -r requirements.txt
docker compose up -d orthanc          # only Orthanc in Docker
python -m service.worker              # terminal 2
uvicorn service.api:app --port 8000   # terminal 3
cd viewer && npm install && npm run dev   # terminal 4, then open http://localhost:5173
```

## Reproduce training (Google Colab, T4 GPU)
1. `notebooks/01_setup_and_dicom_explore.ipynb`: download RSNA data with a Kaggle API token and inspect DICOM.
2. `notebooks/02_preprocess_dvc.ipynb`: patient-level splits, 224×224 PNGs, DVC versioning (remote on Google Drive).
3. `notebooks/03_train.ipynb`: DenseNet121 transfer learning, saves `best.pt` and `metrics.json`.
4. `notebooks/04_gradcam.ipynb`: heatmap examples.

## Tests
```
pip install pytest httpx
python -m pytest tests -q
```
Covers API decision and audit behavior, input validation, Grad-CAM output shape and range, and DICOM preprocessing.

## Data and privacy
Data: RSNA Pneumonia Detection Challenge (Kaggle). Follow its terms of use; the data and weights are not in this repository.
The demo has no authentication, so do not expose it to a network or upload real patient data.

## Responsible use
The viewer shows a permanent education-only banner. AI output is advisory and always `pending` until a named reviewer
approves or rejects it. See the model card for known limitations and un-evaluated subgroups.

## Scope notes
- Classification (DenseNet121) is fully implemented. The optional 3D U-Net segmentation (MONAI, Medical Segmentation Decathlon) is **not implemented**; MONAI is used here for the augmentation transforms.
- Docker files were written but should be verified with `docker compose up --build` on your machine.
