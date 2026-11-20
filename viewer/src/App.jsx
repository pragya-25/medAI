import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api.js";
import Header from "./components/Header.jsx";
import Worklist from "./components/Worklist.jsx";
import Viewer from "./components/Viewer.jsx";
import Assessment from "./components/Assessment.jsx";
import ReviewPanel from "./components/ReviewPanel.jsx";
import Toast from "./components/Toast.jsx";

export default function App() {
  const [studies, setStudies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [theme, setTheme] = useState(localStorage.getItem("theme") || "dark");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("theme", theme);
  }, [theme]);

  const refresh = useCallback(() => {
    api.studies()
      .then((d) => { setStudies(d); setError(""); })
      .catch(() => setError("Cannot reach the API at " + api.base));
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000); // pick up newly analysed studies
    return () => clearInterval(t);
  }, [refresh]);

  const stats = useMemo(() => ({
    total: studies.length,
    pending: studies.filter((s) => s.status === "pending").length,
    approved: studies.filter((s) => s.status === "approved").length,
    rejected: studies.filter((s) => s.status === "rejected").length,
    flagged: studies.filter((s) => s.predicted_positive).length,
  }), [studies]);

  const visible = useMemo(() => studies.filter((s) => {
    if (filter === "pending" && s.status !== "pending") return false;
    if (filter === "flagged" && !s.predicted_positive) return false;
    if (filter === "reviewed" && s.status === "pending") return false;
    return s.study_id.toLowerCase().includes(query.trim().toLowerCase());
  }), [studies, filter, query]);

  useEffect(() => {
    if (!selected && studies.length) setSelected(studies[0].study_id);
  }, [studies, selected]);

  const current = studies.find((s) => s.study_id === selected);
  useEffect(() => {
    if (current) api.study(current.study_id).then(setDetail).catch(() => {});
    else setDetail(null);
  }, [current?.study_id, current?.status]);

  // J / K (or arrow keys) move through the worklist
  useEffect(() => {
    const onKey = (e) => {
      if (["INPUT", "TEXTAREA"].includes(e.target.tagName)) return;
      const i = visible.findIndex((s) => s.study_id === selected);
      if (e.key === "j" || e.key === "ArrowDown") setSelected(visible[Math.min(visible.length - 1, i + 1)]?.study_id ?? selected);
      if (e.key === "k" || e.key === "ArrowUp") setSelected(visible[Math.max(0, i - 1)]?.study_id ?? selected);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [visible, selected]);

  const onDecided = (decision) => {
    setToast({ text: `Decision recorded: ${decision}`, kind: decision, id: Date.now() });
    refresh();
  };

  return (
    <div className="app">
      <div className="banner">
        <strong>FOR EDUCATION ONLY. NOT FOR CLINICAL USE.</strong> Do not use for diagnosis or treatment decisions.
      </div>
      <Header stats={stats} theme={theme} onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")} error={error} />
      <main className="layout">
        <Worklist studies={visible} stats={stats} selected={selected} onSelect={setSelected}
                  filter={filter} setFilter={setFilter} query={query} setQuery={setQuery} />
        {detail ? (
          <>
            <Viewer study={detail} />
            <div className="side">
              <Assessment study={detail} />
              <ReviewPanel study={detail} onDecided={onDecided} />
            </div>
          </>
        ) : (
          <div className="placeholder">
            <div className="placeholder-icon">🩻</div>
            <h3>No study selected</h3>
            <p>{studies.length ? "Select a study from the worklist." : "Upload a DICOM file to Orthanc and it will appear here after the AI analysis."}</p>
          </div>
        )}
      </main>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </div>
  );
}
