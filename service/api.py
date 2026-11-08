"""REST API the React viewer will call.   Run: uvicorn service.api:app --port 8000"""
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from service import db

app = FastAPI(title="MedAI API", description="FOR EDUCATION ONLY. NOT FOR CLINICAL USE.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
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


@app.get("/studies/{study_id}/image")
def image(study_id: str):
    s = get_study(study_id)
    return FileResponse(s["heatmap_path"].replace(".png", "_orig.png"), media_type="image/png")
