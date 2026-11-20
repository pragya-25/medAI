import React from "react";

function Stat({ label, value, tone }) {
  return (
    <div className={`stat ${tone || ""}`}>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

export default function Header({ stats, theme, onToggleTheme, error }) {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 12h4l2-6 4 12 2-6h6" />
          </svg>
        </div>
        <div>
          <div className="brand-name">Med<span>AI</span> Review</div>
          <div className="brand-sub">AI-assisted chest X-ray reading</div>
        </div>
      </div>
      <div className="stats">
        <Stat label="Studies" value={stats.total} />
        <Stat label="Pending" value={stats.pending} tone="warn" />
        <Stat label="Flagged by AI" value={stats.flagged} tone="bad" />
        <Stat label="Approved" value={stats.approved} tone="good" />
        <Stat label="Rejected" value={stats.rejected} tone="bad" />
      </div>
      <div className="top-actions">
        {error && <span className="conn-error">● {error}</span>}
        <button className="icon-btn" onClick={onToggleTheme} title="Toggle light / dark theme" aria-label="Toggle theme">
          {theme === "dark" ? "☀" : "☾"}
        </button>
      </div>
    </header>
  );
}
