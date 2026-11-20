import React from "react";
import { api } from "../api.js";

export const pct = (p) => `${(p * 100).toFixed(1)}%`;

export function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function ago(s) {
  const secs = Math.max(0, (Date.now() - new Date(s.replace(" ", "T") + "Z").getTime()) / 1000);
  if (secs < 60) return "just now";
  if (secs < 3600) return `${Math.floor(secs / 60)} min ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)} h ago`;
  return `${Math.floor(secs / 86400)} d ago`;
}

const FILTERS = [
  ["all", "All"],
  ["pending", "Pending"],
  ["flagged", "Flagged"],
  ["reviewed", "Reviewed"],
];

export default function Worklist({ studies, stats, selected, onSelect, filter, setFilter, query, setQuery }) {
  const counts = { all: stats.total, pending: stats.pending, flagged: stats.flagged, reviewed: stats.approved + stats.rejected };
  return (
    <aside className="worklist card">
      <div className="card-head">
        <h2>Worklist</h2>
        <span className="pill">{studies.length}</span>
      </div>
      <input className="search" placeholder="Search study ID…" value={query} onChange={(e) => setQuery(e.target.value)} />
      <div className="segmented">
        {FILTERS.map(([k, label]) => (
          <button key={k} className={filter === k ? "seg active" : "seg"} onClick={() => setFilter(k)}>
            {label} <small>{counts[k]}</small>
          </button>
        ))}
      </div>
      {studies.length === 0 && <p className="empty">No studies match.</p>}
      <ul className="study-list">
        {studies.map((s) => (
          <li key={s.study_id} className={s.study_id === selected ? "study active" : "study"} onClick={() => onSelect(s.study_id)}>
            <img src={api.imageUrl(s.study_id)} alt="" className="thumb" loading="lazy" />
            <div className="study-meta">
              <div className="study-top">
                <strong className="mono">{s.study_id.slice(0, 8)}</strong>
                <StatusBadge status={s.status} />
              </div>
              <div className={`finding ${s.predicted_positive ? "pos" : "neg"}`}>
                {s.predicted_positive ? "Pneumonia suspected" : "No finding"}
              </div>
              <div className="mini-bar"><div className={s.predicted_positive ? "pos" : "neg"} style={{ width: pct(s.probability) }} /></div>
              <div className="study-foot">
                <span>{pct(s.probability)}</span>
                <span>{ago(s.created_at)}</span>
              </div>
            </div>
          </li>
        ))}
      </ul>
      <p className="hint">Tip: press <kbd>J</kbd> / <kbd>K</kbd> to move between studies.</p>
    </aside>
  );
}
