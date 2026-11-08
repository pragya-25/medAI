"""REST API the React viewer will call.   Run: uvicorn service.api:app --port 8000"""
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from service import db

app = FastAPI(title="MedAI API", description="FOR EDUCATION ONLY. NOT FOR CLINICAL USE.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
db.init()


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
    s = get_study(study_id)
    return FileResponse(s["heatmap_path"], media_type="image/png")


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
    s = get_study(study_id)
    return FileResponse(s["heatmap_path"].replace(".png", "_orig.png"), media_type="image/png")
