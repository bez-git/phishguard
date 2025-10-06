# PhishGuard

A Flask backend + Chrome MV3 extension for **real-time phishing risk detection**.  
The extension sends page/link URLs to the API; the API serves a trained ML model and returns a **label + score**.

---

## Status (Oct 2025)

- **Backend**: Flask app (app-factory + Blueprints) with **JWT auth** is live.
- **ML Serving**: Model **wired in** (`rf_phi.pkl` + `imputer_phi.pkl`) with `feature_order.json` and optional `tld_freq.json`. Safe NaN handling and light post-processing (IP+login bump; HTTPS .gov/.edu de-escalation).
- **Data**: `/api/report` persists URL + `score`, `label`, `evaluated_at` (migration added).
- **Extension (MV3)**: Auto check on tab change/complete, **badge** (PH/! or count), notifications, link autoscan & caching, popup with login and “Scan Page”.
- **Deploy**: App + Postgres on **Render** (custom domain), CORS set; Mailtrap for dev mail.

---

## API (quick list)

**Auth**
- `POST /api/login` → `{ access_token, refresh_token }`
- `POST /api/refresh` → `{ access_token }`
- `GET  /api/me` → current user (Bearer access token)

**Scoring**
- `POST /api/check` → `{ ok, url, label: phish|suspicious|legit, score, threshold }`
- `GET  /api/health` → model/threshold info
- `GET  /api/debug_check?url=...` → features + imputed vector + scores

**Reports**
- `POST /api/report`   → store a report (auth)
- `GET  /api/reports`  → recent reports (auth)

---


## Quickstart (dev)

```powershell
# Windows PowerShell (on macOS/Linux: create venv + activate accordingly)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt


Create .env in repo root (minimal):

FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too
SQLALCHEMY_DATABASE_URI=sqlite:///phishguard.sqlite3
PHISH_THRESHOLD=0.90
PHISH_NAN_DEFAULT=0.5

Run DB + server:

$env:FLASK_APP = "wsgi.py"
flask db upgrade
flask run --reload --port 5000


Smoke test:

Invoke-RestMethod http://127.0.0.1:5000/api/health


1 Chrome extension (dev)
2 Open chrome://extensions → enable Developer mode → Load unpacked → phishguard_chrome_extension_v2/.
Edit phishguard_chrome_extension_v2/config.js:
const CONFIG = { API_BASE: "http://127.0.0.1:5000" }; // use prod URL on deployment
3 Click the extension → Log in → Scan Page. Badge + notifications will appear as you browse.




Deploy (Render)

Set env vars: FLASK_ENV=production, strong SECRET_KEY & JWT_SECRET_KEY, SQLALCHEMY_DATABASE_URI (Postgres), optional PHISH_THRESHOLD, Mailtrap.
After build, run: FLASK_APP=wsgi.py flask db upgrade.
Point the extension API_BASE to your domain (e.g., https://www.phishguard.shop).