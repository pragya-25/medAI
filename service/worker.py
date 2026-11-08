"""Polls Orthanc for new studies, runs the AI, and stores the results.

Run:  python -m service.worker
"""
import os
import time
import requests
from PIL import Image

from service import db
from service.inference import Predictor

ORTHANC = os.environ.get("ORTHANC_URL", "http://localhost:8042")
OUT_DIR = os.environ.get("MEDAI_OUT", "service/data/heatmaps")
POLL_SECONDS = 5


def process_study(study_id, predictor):
    # A study contains instances (images). We analyze the first one: a chest X-ray study has one image.
    instances = requests.get(f"{ORTHANC}/studies/{study_id}/instances", timeout=30).json()
    if not instances:
        return
    raw = requests.get(f"{ORTHANC}/instances/{instances[0]['ID']}/file", timeout=60).content
    res = predictor.run(raw)

    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{study_id}.png")
    Image.fromarray(res["heatmap"]).save(path)
    Image.fromarray(res["original"]).save(os.path.join(OUT_DIR, f"{study_id}_orig.png"))

    with db.conn() as c:
        c.execute(
            """INSERT OR REPLACE INTO results
               (study_id, probability, predicted_positive, threshold, model_version, heatmap_path)
               VALUES (?,?,?,?,?,?)""",
            (study_id, res["probability"], res["predicted_positive"], predictor.threshold,
             predictor.version, path),
        )
    print(f"[ok] study {study_id[:8]} P(pneumonia)={res['probability']:.3f}")


def main():
    db.init()
    predictor = Predictor()
    print("Model loaded:", predictor.version, "| watching", ORTHANC)
    while True:
        try:
            since = int(db.get_state("last_seq", "0"))
            r = requests.get(f"{ORTHANC}/changes", params={"since": since, "limit": 100}, timeout=30).json()
            for ch in r["Changes"]:
                # StableStudy fires once a study has stopped receiving new images, so it is complete.
                if ch["ChangeType"] == "StableStudy":
                    process_study(ch["ID"], predictor)
            db.set_state("last_seq", r["Last"])   # remember progress so a restart does not reprocess
        except requests.RequestException as e:
            print("Orthanc not reachable, retrying:", e)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
