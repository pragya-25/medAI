# Architecture

> FOR EDUCATION ONLY. NOT FOR CLINICAL USE.

## System overview
```mermaid
flowchart LR
    subgraph Source
        S[DICOM files / modality]
    end
    subgraph Docker Compose
        O[(Orthanc DICOM server\n:8042 REST, :4242 DICOM)]
        W[Worker\nservice/worker.py]
        M[[DenseNet121 + Grad-CAM\nservice/inference.py]]
        DB[(SQLite\nresults + audit_log)]
        A[FastAPI\nservice/api.py :8000]
        V[React viewer\n:8080]
    end
    R((Radiologist))

    S -->|upload| O
    W -->|poll /changes: StableStudy| O
    W -->|download instance| O
    W --> M
    M -->|probability + heatmap PNG| W
    W -->|write result| DB
    V -->|HTTP JSON + images| A
    A --> DB
    R --> V
    V -->|POST decision| A
    A -->|status + audit row, one transaction| DB
```

## Sequence for one scan
```mermaid
sequenceDiagram
    participant U as Uploader
    participant O as Orthanc
    participant W as Worker
    participant D as Database
    participant V as Viewer
    participant R as Radiologist
    U->>O: POST /instances (DICOM)
    W->>O: GET /changes?since=last_seq
    O-->>W: StableStudy event
    W->>O: GET /instances/{id}/file
    W->>W: preprocess, predict, Grad-CAM
    W->>D: INSERT result (status = pending)
    V->>D: GET /studies (via API, polled every 5 s)
    R->>V: open study, review AI overlay
    R->>V: Approve or Reject + name + comment
    V->>D: POST decision: UPDATE status + INSERT audit_log
```

## Components
| Component | Folder | Role |
|---|---|---|
| ML code | `ml/` | DICOM reading, preprocessing, dataset, training, Grad-CAM |
| Notebooks | `notebooks/` | Colab runs: data download, preprocessing and DVC, training, Grad-CAM |
| Worker | `service/worker.py` | Watches Orthanc, runs inference, stores results |
| Inference | `service/inference.py` | Loads weights, same preprocessing as training |
| API | `service/api.py` | Studies, images, decisions, audit log |
| Database | `service/db.py` | SQLite: `results`, `audit_log`, `state` |
| Viewer | `viewer/` | React UI: worklist, overlay, confidence, approve/reject, audit history |

## Design decisions
- **`StableStudy` trigger.** Orthanc emits it only after a study stops receiving images, so we never analyze half-uploaded studies.
- **`last_seq` in the database.** The worker remembers its position in Orthanc's change feed, so restarts do not reprocess old studies.
- **Decision and audit row in one transaction.** A decision cannot exist without its audit record.
- **Append-only audit.** The API exposes no update or delete for audit rows.
- **Weights outside the image.** `best.pt` is mounted as a volume, so images stay small and weights stay out of git.
- **Training-time preprocessing is reused at inference.** A mismatch here silently degrades accuracy, and a unit test covers the key steps.
