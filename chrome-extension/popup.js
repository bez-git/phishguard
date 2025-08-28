(async function() {
  const emailEl = document.getElementById('email');
  const passwordEl = document.getElementById('password');
  const loginBtn = document.getElementById('loginBtn');
  const meBtn = document.getElementById('meBtn');
  const refreshBtn = document.getElementById('refreshBtn');
  const output = document.getElementById('output');
  const accessOut = document.getElementById('accessOut');
  const status = document.getElementById('status');

  function show(msg, ok=false) {
    output.textContent = typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2);
    status.textContent = ok ? 'OK' : '';
    status.className = ok ? 'small ok' : 'small err';
  }

  function truncate(token) {
    if (!token) return '';
    return token.slice(0, 25) + '...';
  }

  async function saveTokens(access, refresh) {
    await chrome.storage.local.set({ access, refresh });
    accessOut.textContent = truncate(access);
  }

  async function getTokens() {
    const { access, refresh } = await chrome.storage.local.get(['access', 'refresh']);
    accessOut.textContent = truncate(access);
    return { access, refresh };
  }

  async function login() {
    const email = emailEl.value.trim().toLowerCase();
    const password = passwordEl.value;
    if (!email || !password) { show('Please enter email and password'); return; }
    try {
      const res = await fetch(`${CONFIG.API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();
      if (!res.ok) {
        show(data.error || res.statusText);
        return;
      }
      await saveTokens(data.access_token, data.refresh_token);
      show('Logged in', true);
    } catch (e) {
      show(String(e));
    }
  }

  async function me() {
    const { access } = await getTokens();
    if (!access) { show('No access token. Log in first.'); return; }
    try {
      const res = await fetch(`${CONFIG.API_BASE}/api/me`, {
        headers: { 'Authorization': `Bearer ${access}` }
      });
      const data = await res.json();
      if (!res.ok) { show(data); return; }
      show(data, true);
    } catch (e) {
      show(String(e));
    }
  }

  async function refresh() {
    const { refresh } = await getTokens();
    if (!refresh) { show('No refresh token. Log in first.'); return; }
    try {
      const res = await fetch(`${CONFIG.API_BASE}/api/refresh`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${refresh}` }
      });
      const data = await res.json();
      if (!res.ok) { show(data); return; }
      await saveTokens(data.access_token, (await getTokens()).refresh);
      show('Access token refreshed', true);
    } catch (e) {
      show(String(e));
    }
  }

  loginBtn.addEventListener('click', login);
  meBtn.addEventListener('click', me);
  refreshBtn.addEventListener('click', refresh);

  await getTokens();
})();
