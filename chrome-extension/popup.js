// popup.js

// Use config.js if present; else default to prod
const API = (typeof window !== "undefined" && window.PG_API)
  ? window.PG_API
  : "https://www.phishguard.shop";

const el  = (id) => document.getElementById(id);
const out = (msg) => { el("output").textContent = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2); };

const parseJwt = (t) => {
  try { return JSON.parse(atob(t.split(".")[1])); } catch { return null; }
};

async function saveAuth(access, refresh) {
  const payload = parseJwt(access) || {};
  await chrome.storage.local.set({ auth: { access, refresh, exp: payload.exp || 0 } });
}

async function getAuth() {
  const { auth } = await chrome.storage.local.get("auth");
  return auth || null;
}

async function clearAuth() {
  await chrome.storage.local.remove("auth");
  el("token").value = "";
  out("");
}

async function apiFetch(path, opts = {}) {
  // Attach Access token
  const auth = await getAuth();
  const headers = new Headers(opts.headers || {});
  if (auth?.access) headers.set("Authorization", `Bearer ${auth.access}`);

  let res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status !== 401) return res;

  // Try refresh once on 401
  if (!auth?.refresh) return res;
  const r = await fetch(`${API}/api/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.refresh}` }
  });
  if (!r.ok) return res;

  const { access_token } = await r.json();
  await saveAuth(access_token, auth.refresh);

  const headers2 = new Headers(opts.headers || {});
  headers2.set("Authorization", `Bearer ${access_token}`);
  return fetch(`${API}${path}`, { ...opts, headers: headers2 });
}

async function getActiveTabUrl() {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      resolve(tabs?.[0]?.url || "");
    });
  });
}

/* === UI hooks === */

el("login").addEventListener("click", async () => {
  const email = el("email").value.trim();
  const password = el("password").value;
  if (!email || !password) return out("Enter email and password.");
  out("Logging in…");

  const res = await fetch(`${API}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    out(txt || "Login failed");
    return;
  }

  const data = await res.json().catch(() => ({}));
  if (data.error === "email_not_confirmed") {
    out("Account not verified. Check your email.");
    return;
  }

  const { access_token, refresh_token } = data;
  await saveAuth(access_token, refresh_token);
  el("token").value = access_token.slice(0, 30) + "...";
  out("logged in");
});

el("me").addEventListener("click", async () => {
  const res = await apiFetch("/api/me");
  const j = await res.json().catch(() => ({}));
  out(j);
});

el("refresh").addEventListener("click", async () => {
  const auth = await getAuth();
  if (!auth?.refresh) return out("No refresh token saved");

  const res = await fetch(`${API}/api/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.refresh}` }
  });
  if (!res.ok) return out(await res.text().catch(() => "Refresh failed"));

  const { access_token } = await res.json().catch(() => ({}));
  if (!access_token) return out("No access_token in refresh response");

  await saveAuth(access_token, auth.refresh);
  el("token").value = access_token.slice(0, 30) + "...";
  out("refreshed");
});

el("logout").addEventListener("click", async () => {
  await clearAuth();
  out("logged out");
});

// New: Report current page
el("report-tab").addEventListener("click", async () => {
  const url = await getActiveTabUrl();
  if (!url) return out("No active tab URL");

  const res = await apiFetch("/api/report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, source: "popup" })
  });
  if (!res.ok) return out(await res.text().catch(() => "Report failed"));
  out("reported");
});

// New: Check risk of current page
el("check-tab").addEventListener("click", async () => {
  const url = await getActiveTabUrl();
  if (!url) return out("No active tab URL");

  const res = await apiFetch("/api/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url })
  });
  const j = await res.json().catch(() => ({}));
  if (!res.ok) return out(j);

  const score = Math.round(((j.score ?? 0) * 100));
  out(`risk: ${score}% (${j.label || "unknown"})`);
});

// Auto-resume when popup opens
(async () => {
  const auth = await getAuth();
  if (auth?.access) {
    el("token").value = auth.access.slice(0, 30) + "...";
  }
})();
