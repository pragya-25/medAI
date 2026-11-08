import React, { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";

const pct = (p) => `${(p * 100).toFixed(1)}%`;
const when = (s) => new Date(s.replace(" ", "T") + "Z").toLocaleString();

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function StudyList({ studies, selected, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-head">
        <h2>Worklist</h2>
        <span className="count">{studies.length}</span>
      </div>
      {studies.length === 0 && <p className="empty">No studies yet. Upload a DICOM to Orthanc.</p>}
      <ul>
        {studies.map((s) => (
          <li key={s.study_id} className={s.study_id === selected ? "active" : ""} onClick={() => onSelect(s.study_id)}>
            <img src={api.imageUrl(s.study_id)} alt="" className="thumb" />
            <div className="meta">
              <div className="row">
                <strong>{s.study_id.slice(0, 8)}</strong>
                <StatusBadge status={s.status} />
              </div>
              <div className={`finding ${s.predicted_positive ? "pos" : "neg"}`}>
                {s.predicted_positive ? "Pneumonia suspected" : "No finding"} · {pct(s.probability)}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}

function ConfidenceMeter({ probability, threshold }) {
  return (
    <div className="meter">
      <div className="meter-label">
        <span>AI confidence (pneumonia)</span>
        <strong>{pct(probability)}</strong>
      </div>
      <div className="meter-track">
        <div className={`meter-fill ${probability >= threshold ? "pos" : "neg"}`} style={{ width: pct(probability) }} />
        <div className="meter-threshold" style={{ left: pct(threshold) }} title={`Decision threshold ${pct(threshold)}`} />
      </div>
      <div className="meter-scale">
        <span>0%</span>
        <span>threshold {pct(threshold)}</span>
        <span>100%</span>
      </div>
    </div>
  );
}

function Viewer({ study }) {
  const [mode, setMode] = useState("overlay");
  const id = study.study_id;
  return (
    <section className="viewer">
      <div className="tabs">
        {[
          ["original", "Original"],
          ["overlay", "AI heatmap"],
          ["side", "Side by side"],
        ].map(([k, label]) => (
          <button key={k} className={mode === k ? "tab active" : "tab"} onClick={() => setMode(k)}>
            {label}
          </button>
        ))}
      </div>
      <div className={`canvas ${mode === "side" ? "two" : ""}`}>
        {(mode === "original" || mode === "side") && (
          <figure>
            <img src={api.imageUrl(id)} alt="Original chest X-ray" />
            <figcaption>Original</figcaption>
          </figure>
        )}
        {(mode === "overlay" || mode === "side") && (
          <figure>
            <img src={api.heatmapUrl(id)} alt="Grad-CAM overlay" />
            <figcaption>Grad-CAM: red = regions that raised the pneumonia score</figcaption>
          </figure>
        )}
      </div>
    </section>
  );
}

function ReviewPanel({ study, onDecided }) {
  const [reviewer, setReviewer] = useState(localStorage.getItem("reviewer") || "");
  const [comment, setComment] = useState("");
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const id = study.study_id;

  const loadAudit = useCallback(() => api.audit(id).then(setAudit).catch(() => {}), [id]);
  useEffect(() => {
    setComment("");
    setError("");
    loadAudit();
  }, [id, loadAudit]);

  async function decide(decision) {
    if (!reviewer.trim()) return setError("Enter your name before deciding. It is recorded in the audit log.");
    setBusy(true);
    setError("");
    try {
      localStorage.setItem("reviewer", reviewer.trim());
      await api.decide(id, { reviewer: reviewer.trim(), decision, comment });
      setComment("");
      await loadAudit();
      onDecided();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="panel">
      <div className="card">
        <h3>AI assessment</h3>
        <div className={`verdict ${study.predicted_positive ? "pos" : "neg"}`}>
          {study.predicted_positive ? "Pneumonia suspected" : "No pneumonia detected"}
        </div>
        <ConfidenceMeter probability={study.probability} threshold={study.threshold} />
        <dl className="facts">
          <dt>Status</dt>
          <dd><StatusBadge status={study.status} /></dd>
          <dt>Model</dt>
          <dd>{study.model_version}</dd>
          <dt>Study</dt>
          <dd className="mono">{id.slice(0, 18)}…</dd>
        </dl>
      </div>

      <div className="card">
        <h3>Radiologist review</h3>
        <label>Reviewer name</label>
        <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Dr. Jane Doe" />
        <label>Comment (optional)</label>
        <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Reason or notes" />
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button className="btn approve" disabled={busy} onClick={() => decide("approved")}>✓ Approve AI result</button>
          <button className="btn reject" disabled={busy} onClick={() => decide("rejected")}>✕ Reject</button>
        </div>
      </div>

      <div className="card">
        <h3>Audit log</h3>
        {audit.length === 0 && <p className="empty">No decisions recorded.</p>}
        <ul className="audit">
          {audit.map((a) => (
            <li key={a.id}>
              <StatusBadge status={a.decision} />
              <div>
                <strong>{a.reviewer}</strong>
                <span className="muted"> · {when(a.created_at)}</span>
                {a.comment && <p>{a.comment}</p>}
                <small className="muted">{a.model_version} · p={pct(a.probability)}</small>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}

export default function App() {
  const [studies, setStudies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");

  const refresh = useCallback(() => {
    api.studies().then((d) => { setStudies(d); setError(""); }).catch(() => setError("Cannot reach the API at " + api.base));
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000); // pick up newly analysed studies
    return () => clearInterval(t);
  }, [refresh]);

  useEffect(() => {
    if (!selected && studies.length) setSelected(studies[0].study_id);
  }, [studies, selected]);

  const study = studies.find((s) => s.study_id === selected);
  const [detail, setDetail] = useState(null);
  useEffect(() => {
    if (study) api.study(study.study_id).then(setDetail).catch(() => {});
  }, [study?.study_id, study?.status]);

  return (
    <div className="app">
      <div className="banner">
        ⚠ FOR EDUCATION ONLY. NOT FOR CLINICAL USE. Do not use for diagnosis or treatment decisions.
      </div>
      <header className="topbar">
        <div className="logo">Med<span>AI</span></div>
        <div className="subtitle">AI-assisted chest X-ray review</div>
        {error && <div className="conn-error">{error}</div>}
      </header>
      <main className="layout">
        <StudyList studies={studies} selected={selected} onSelect={setSelected} />
        {detail && study ? (
          <>
            <Viewer study={detail} />
            <ReviewPanel study={detail} onDecided={refresh} />
          </>
        ) : (
          <div className="placeholder">Select a study from the worklist.</div>
        )}
      </main>
    </div>
  );
}
