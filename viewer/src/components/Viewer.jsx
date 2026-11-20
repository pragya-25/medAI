import React, { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../api.js";

/** Shared zoom + pan state so side-by-side images move together. */
function usePanZoom() {
  const [t, setT] = useState({ s: 1, x: 0, y: 0 });
  const drag = useRef(null);
  const zoomBy = useCallback((f) => setT((p) => {
    const s = Math.min(6, Math.max(1, p.s * f));
    return s <= 1 ? { s: 1, x: 0, y: 0 } : { ...p, s };   // snap back to center at 100%
  }), []);
  const reset = useCallback(() => setT({ s: 1, x: 0, y: 0 }), []);
  const handlers = {
    onPointerDown: (e) => {
      drag.current = { x: e.clientX, y: e.clientY, ox: t.x, oy: t.y };
      e.currentTarget.setPointerCapture(e.pointerId);
    },
    onPointerMove: (e) => {
      if (!drag.current) return;
      const d = drag.current;
      setT((p) => (p.s > 1 ? { ...p, x: d.ox + e.clientX - d.x, y: d.oy + e.clientY - d.y } : p));
    },
    onPointerUp: () => { drag.current = null; },
    onPointerCancel: () => { drag.current = null; },
  };
  return { t, zoomBy, reset, handlers };
}

function Stage({ base, overlay, opacity, pz, filter, caption }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    const onWheel = (e) => { e.preventDefault(); pz.zoomBy(e.deltaY < 0 ? 1.12 : 1 / 1.12); };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [pz.zoomBy]);
  const style = { transform: `translate(${pz.t.x}px, ${pz.t.y}px) scale(${pz.t.s})`, filter };
  return (
    <figure className="stage-wrap">
      <div ref={ref} className={`stage ${pz.t.s > 1 ? "grab" : ""}`} {...pz.handlers}>
        <img src={base} alt="Chest X-ray" style={style} draggable={false} />
        {overlay && <img src={overlay} alt="Grad-CAM overlay" className="layer" style={{ ...style, opacity }} draggable={false} />}
      </div>
      <figcaption>{caption}</figcaption>
    </figure>
  );
}

export default function Viewer({ study }) {
  const id = study.study_id;
  const [mode, setMode] = useState("overlay");
  const [opacity, setOpacity] = useState(1);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [invert, setInvert] = useState(false);
  const pz = usePanZoom();

  useEffect(() => { pz.reset(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  const filter = `brightness(${brightness}%) contrast(${contrast}%) invert(${invert ? 1 : 0})`;
  const img = api.imageUrl(id);
  const heat = api.heatmapUrl(id);
  const resetAll = () => { pz.reset(); setBrightness(100); setContrast(100); setInvert(false); setOpacity(1); };

  return (
    <section className="viewer card">
      <div className="toolbar">
        <div className="segmented">
          {[["original", "Original"], ["overlay", "AI overlay"], ["side", "Side by side"]].map(([k, label]) => (
            <button key={k} className={mode === k ? "seg active" : "seg"} onClick={() => setMode(k)}>{label}</button>
          ))}
        </div>
        <div className="zoom">
          <button className="icon-btn sm" onClick={() => pz.zoomBy(1 / 1.25)} title="Zoom out">−</button>
          <span className="zoom-val">{Math.round(pz.t.s * 100)}%</span>
          <button className="icon-btn sm" onClick={() => pz.zoomBy(1.25)} title="Zoom in">+</button>
          <button className="icon-btn sm text" onClick={resetAll} title="Reset view">Reset</button>
        </div>
      </div>

      <div className={`stages ${mode === "side" ? "two" : ""}`}>
        {mode === "original" && <Stage base={img} pz={pz} filter={filter} caption="Original scan" />}
        {mode === "overlay" && <Stage base={img} overlay={heat} opacity={opacity} pz={pz} filter={filter}
                                      caption="Grad-CAM: red/yellow = regions that increased the pneumonia score" />}
        {mode === "side" && (
          <>
            <Stage base={img} pz={pz} filter={filter} caption="Original" />
            <Stage base={img} overlay={heat} opacity={opacity} pz={pz} filter={filter} caption="AI overlay" />
          </>
        )}
      </div>

      <div className="controls">
        <label className={mode === "original" ? "ctrl disabled" : "ctrl"}>
          <span>Overlay opacity <b>{Math.round(opacity * 100)}%</b></span>
          <input type="range" min="0" max="100" value={opacity * 100} disabled={mode === "original"} onChange={(e) => setOpacity(e.target.value / 100)} />
        </label>
        <label className="ctrl">
          <span>Brightness <b>{brightness}%</b></span>
          <input type="range" min="50" max="170" value={brightness} onChange={(e) => setBrightness(+e.target.value)} />
        </label>
        <label className="ctrl">
          <span>Contrast <b>{contrast}%</b></span>
          <input type="range" min="50" max="200" value={contrast} onChange={(e) => setContrast(+e.target.value)} />
        </label>
        <button className={invert ? "chip active" : "chip"} onClick={() => setInvert(!invert)}>Invert</button>
      </div>
      <p className="hint">Scroll to zoom · drag to pan when zoomed · the heatmap is an explanation aid, not a lesion outline.</p>
    </section>
  );
}
