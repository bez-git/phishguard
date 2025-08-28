// popup.js
const API = "https://www.phishguard.shop"; // keep in sync with config.js if you use it

const el = (id) => document.getElementById(id);
const out = (msg) => (el("output").textContent = typeof msg === "string" ? msg : JSON.stringify(msg, null, 2));

const parseJwt = (t) => {
  try { return JSON.parse(atob(t.split('.')[1])); } catch { return null; }
};

async function saveAuth(access, refresh) {
  const payload = parseJwt(access) || {};
  await chrome.storage.local.set({
    auth: { access, refresh, exp: payload.exp || 0 }
  });
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
  // attaches token, auto-refreshes on 401
  const auth = await getAuth();
  const headers = new Headers(opts.headers || {});
  if (auth?.access) headers.set("Authorization", `Bearer ${auth.access}`);

  let res = await fetch(`${API}${path}`, { ...opts, headers });
  if (res.status !== 401) return res;

  // try refresh once
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

// UI hooks
el("login").addEventListener("click", async () => {
  const email = el("email").value.trim();
  const password = el("password").value;
  out("Logging in…");
  const res = await fetch(`${API}/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password })
  });

  if (!res.ok) {
    const msg = await res.text();
    out(msg || "Login failed");
    return;
  }
  const data = await res.json();

  // Handle “email_not_confirmed”
  if (data.error === "email_not_confirmed") {
    out("Account not verified yet. Check your inbox for the confirmation email.");
    return;
  }

  const { access_token, refresh_token } = data;
  await saveAuth(access_token, refresh_token);
  el("token").value = access_token.slice(0, 30) + "...";
  out("logged in");
});

el("me").addEventListener("click", async () => {
  const res = await apiFetch("/api/me");
  out(await res.json());
});

el("refresh").addEventListener("click", async () => {
  const auth = await getAuth();
  if (!auth?.refresh) return out("No refresh token saved");
  const res = await fetch(`${API}/api/refresh`, {
    method: "POST",
    headers: { Authorization: `Bearer ${auth.refresh}` }
  });
  if (!res.ok) return out(await res.text());
  const { access_token } = await res.json();
  await saveAuth(access_token, auth.refresh);
  el("token").value = access_token.slice(0, 30) + "...";
  out("refreshed");
});

el("logout").addEventListener("click", async () => {
  await clearAuth();
  out("logged out");
});

// Auto-resume when popup opens
(async () => {
  const auth = await getAuth();
  if (!auth?.access) return;
  el("token").value = auth.access.slice(0, 30) + "...";
})();


