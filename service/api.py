"""REST API the React viewer will call.   Run: uvicorn service.api:app --port 8000"""
import os
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from service import db

app = FastAPI(title="MedAI API", description="FOR EDUCATION ONLY. NOT FOR CLINICAL USE.")
ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080").split(",")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["*"], allow_headers=["*"])
db.init()
HEATMAP_DIR = os.environ.get("MEDAI_OUT", "service/data/heatmaps")


@app.get("/studies")
def list_studies():
    with db.conn() as c:
        rows = c.execute("SELECT study_id, probability, predicted_positive, status, created_at "
                         "FROM results ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/studies/{study_id}")
def get_study(study_id: str):
    with db.conn() as c:
        r = c.execute("SELECT * FROM results WHERE study_id=?", (study_id,)).fetchone()
    if not r:
        raise HTTPException(404, "Study not found")
    return dict(r)


@app.get("/studies/{study_id}/heatmap")
def heatmap(study_id: str):
    return _png(study_id, ".png")


def _png(study_id: str, suffix: str):
    """Resolve the image by file NAME inside the heatmap folder.

    Older rows stored full Windows paths (backslashes), which do not resolve on Linux/Docker.
    Taking only the file name makes every row work on every OS.
    """
    s = get_study(study_id)
    name = os.path.basename(s["heatmap_path"].replace("\\", "/"))
    if suffix != ".png":
        name = name[: -len(".png")] + suffix
    path = os.path.join(HEATMAP_DIR, name)
    if not os.path.isfile(path):
        raise HTTPException(404, "Image file not found")
    return FileResponse(path, media_type="image/png")


class Decision(BaseModel):
    reviewer: str = Field(min_length=1, max_length=80)
    decision: Literal["approved", "rejected"]
    comment: str = Field(default="", max_length=500)


@app.post("/studies/{study_id}/decision")
def decide(study_id: str, body: Decision):
    """Record the radiologist's decision. Status update and audit entry happen in ONE transaction,
    so a decision can never exist without its audit record."""
    with db.conn() as c:
        r = c.execute("SELECT * FROM results WHERE study_id=?", (study_id,)).fetchone()
        if not r:
            raise HTTPException(404, "Study not found")
        c.execute("UPDATE results SET status=? WHERE study_id=?", (body.decision, study_id))
        c.execute(
            """INSERT INTO audit_log (study_id, reviewer, decision, model_version, probability, comment)
               VALUES (?,?,?,?,?,?)""",
            (study_id, body.reviewer.strip(), body.decision, r["model_version"], r["probability"], body.comment),
        )
    return {"study_id": study_id, "status": body.decision}


@app.get("/studies/{study_id}/audit")
def study_audit(study_id: str):
    with db.conn() as c:
        rows = c.execute("SELECT * FROM audit_log WHERE study_id=? ORDER BY id DESC", (study_id,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/audit")
def full_audit():
    """Complete append-only history of every decision (the API never updates or deletes rows)."""
    with db.conn() as c:
        rows = c.execute("SELECT * FROM audit_log ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


@app.get("/studies/{study_id}/image")
def image(study_id: str):
    return _png(study_id, "_orig.png")
