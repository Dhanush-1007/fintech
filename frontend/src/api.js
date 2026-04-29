const API_BASE = "http://localhost:4000";

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!res.ok) {
    const message = await res.text();
    throw new Error(message || "Request failed");
  }
  return res.json();
}

export const apiClient = {
  health: () => api("/health"),
  getIssuer: () => api("/api/issuer"),
  startKyc: () => api("/api/kyc/start", { method: "POST" }),
  verifyKyc: (payload) => api("/api/kyc/verify", { method: "POST", body: JSON.stringify(payload) }),
  issueVc: (payload) => api("/api/vc/issue", { method: "POST", body: JSON.stringify(payload) }),
  verifyVc: (payload) => api("/api/vc/verify", { method: "POST", body: JSON.stringify(payload) }),
  verifyZkp: (payload) => api("/api/zkp/verify", { method: "POST", body: JSON.stringify(payload) }),
  graphCheck: (payload) => api("/api/graph/check", { method: "POST", body: JSON.stringify(payload) })
};
