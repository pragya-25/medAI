# API Reference

Base URL: `http://localhost:8000`. Interactive docs (Swagger UI): `http://localhost:8000/docs`.

> FOR EDUCATION ONLY. NOT FOR CLINICAL USE. There is no authentication in this demo.

## Studies
| Method | Path | Description |
|---|---|---|
| GET | `/studies` | List analysed studies (newest first): `study_id`, `probability`, `predicted_positive`, `status`, `created_at` |
| GET | `/studies/{study_id}` | Full record, including `threshold`, `model_version`, `heatmap_path` |
| GET | `/studies/{study_id}/image` | Original scan as PNG (224×224) |
| GET | `/studies/{study_id}/heatmap` | Grad-CAM overlay as PNG |

`status` is `pending`, `approved`, or `rejected`. `study_id` is the Orthanc study ID.

## Decisions and audit
| Method | Path | Description |
|---|---|---|
| POST | `/studies/{study_id}/decision` | Record a radiologist decision |
| GET | `/studies/{study_id}/audit` | Decisions for one study (newest first) |
| GET | `/audit` | Every decision, all studies (newest first) |

`POST /studies/{study_id}/decision`
```json
{ "reviewer": "Dr. Jane Doe", "decision": "approved", "comment": "Consistent with right lower lobe opacity" }
```
- `reviewer`: 1–80 characters, required. `decision`: `"approved"` or `"rejected"`. `comment`: up to 500 characters, optional.
- Success: `200 {"study_id": "...", "status": "approved"}`
- Unknown study: `404`. Invalid body: `422`. On any failure nothing is written.

Audit row fields: `id`, `study_id`, `reviewer`, `decision`, `model_version`, `probability`, `comment`, `created_at` (UTC).

## Database schema
```
results   (study_id PK, probability, predicted_positive, threshold, model_version, heatmap_path, status, created_at)
audit_log (id PK AUTOINCREMENT, study_id, reviewer, decision, model_version, probability, comment, created_at)
state     (key PK, value)          -- worker progress: last Orthanc change sequence
```

## Orthanc endpoints used by the worker
`GET /changes?since=N`, `GET /studies/{id}/instances`, `GET /instances/{id}/file`, `POST /instances` (upload).
