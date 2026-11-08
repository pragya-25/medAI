const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function req(path, options) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export const api = {
  base: BASE,
  studies: () => req("/studies"),
  study: (id) => req(`/studies/${id}`),
  audit: (id) => req(`/studies/${id}/audit`),
  decide: (id, body) =>
    req(`/studies/${id}/decision`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  imageUrl: (id) => `${BASE}/studies/${id}/image`,
  heatmapUrl: (id) => `${BASE}/studies/${id}/heatmap`,
};
