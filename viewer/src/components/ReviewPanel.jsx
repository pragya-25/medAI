import React, { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { StatusBadge, pct } from "./Worklist.jsx";

const when = (s) => new Date(s.replace(" ", "T") + "Z").toLocaleString();
const QUICK = ["Consistent with AI finding", "No opacity seen, disagree", "Needs follow-up imaging", "Poor image quality"];

export default function ReviewPanel({ study, onDecided }) {
  const id = study.study_id;
  const [reviewer, setReviewer] = useState(localStorage.getItem("reviewer") || "");
  const [comment, setComment] = useState("");
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const loadAudit = useCallback(() => api.audit(id).then(setAudit).catch(() => {}), [id]);
  useEffect(() => { setComment(""); setError(""); loadAudit(); }, [id, loadAudit]);

  async function decide(decision) {
    if (!reviewer.trim()) return setError("Enter your name first. It is recorded in the audit log.");
    setBusy(true);
    setError("");
    try {
      localStorage.setItem("reviewer", reviewer.trim());
      await api.decide(id, { reviewer: reviewer.trim(), decision, comment });
      setComment("");
      await loadAudit();
      onDecided(decision);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <section className="card review">
        <div className="card-head"><h3>Radiologist review</h3></div>
        {study.status !== "pending" && (
          <p className="notice">Current status: <StatusBadge status={study.status} /> A new decision is appended to the audit log and replaces the status.</p>
        )}
        <label>Reviewer name</label>
        <input value={reviewer} onChange={(e) => setReviewer(e.target.value)} placeholder="Dr. Jane Doe" />
        <label>Comment <span className="muted">(optional)</span></label>
        <textarea rows={3} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Findings, reasoning, follow-up…" />
        <div className="chips">
          {QUICK.map((q) => <button key={q} className="chip" onClick={() => setComment(q)}>{q}</button>)}
        </div>
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button className="btn approve" disabled={busy} onClick={() => decide("approved")}>✓ Approve AI result</button>
          <button className="btn reject" disabled={busy} onClick={() => decide("rejected")}>✕ Reject</button>
        </div>
      </section>

      <section className="card">
        <div className="card-head"><h3>Audit trail</h3><span className="pill">{audit.length}</span></div>
        {audit.length === 0 && <p className="empty">No decisions recorded for this study.</p>}
        <ol className="timeline">
          {audit.map((a) => (
            <li key={a.id} className={a.decision}>
              <span className="dot" />
              <div>
                <div className="tl-top"><strong>{a.reviewer}</strong><StatusBadge status={a.decision} /></div>
                <div className="muted small">{when(a.created_at)}</div>
                {a.comment && <p className="tl-comment">“{a.comment}”</p>}
                <div className="muted tiny">{a.model_version} · AI score {pct(a.probability)}</div>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </>
  );
}
