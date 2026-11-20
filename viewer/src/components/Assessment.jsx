import React from "react";
import { StatusBadge, pct } from "./Worklist.jsx";

function Ring({ probability, threshold }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  const positive = probability >= threshold;
  return (
    <svg viewBox="0 0 140 140" className="ring" role="img" aria-label={`AI confidence ${pct(probability)}`}>
      <circle cx="70" cy="70" r={r} className="ring-track" />
      <circle cx="70" cy="70" r={r} className={`ring-fill ${positive ? "pos" : "neg"}`}
              strokeDasharray={`${c * probability} ${c}`} transform="rotate(-90 70 70)" />
      {/* white tick = decision threshold */}
      <line x1="70" y1="9" x2="70" y2="25" className="ring-tick" transform={`rotate(${threshold * 360} 70 70)`} />
      <text x="70" y="68" textAnchor="middle" className="ring-value">{(probability * 100).toFixed(0)}%</text>
      <text x="70" y="88" textAnchor="middle" className="ring-label">confidence</text>
    </svg>
  );
}

export default function Assessment({ study }) {
  const positive = !!study.predicted_positive;
  return (
    <section className="card assess">
      <div className="card-head"><h3>AI assessment</h3><StatusBadge status={study.status} /></div>
      <div className="assess-body">
        <Ring probability={study.probability} threshold={study.threshold} />
        <div>
          <div className={`verdict ${positive ? "pos" : "neg"}`}>{positive ? "Pneumonia suspected" : "No pneumonia detected"}</div>
          <p className="muted small">
            Score {pct(study.probability)} vs. threshold {pct(study.threshold)}. The white tick on the ring marks the threshold.
          </p>
        </div>
      </div>
      <dl className="facts">
        <dt>Model</dt><dd>{study.model_version}</dd>
        <dt>Study</dt><dd className="mono">{study.study_id.slice(0, 18)}…</dd>
        <dt>Analysed</dt><dd>{new Date(study.created_at.replace(" ", "T") + "Z").toLocaleString()}</dd>
      </dl>
      <p className="caveat">Scores are not calibrated probabilities. See the model card for limitations.</p>
    </section>
  );
}
