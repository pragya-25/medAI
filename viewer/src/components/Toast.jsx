import React, { useEffect } from "react";

export default function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(onClose, 3000);
    return () => clearTimeout(t);
  }, [toast, onClose]);
  if (!toast) return null;
  return <div className={`toast ${toast.kind}`} role="status">{toast.kind === "approved" ? "✓" : "✕"} {toast.text}</div>;
}
