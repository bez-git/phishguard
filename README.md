# PhishGuard

Flask backend + Chrome MV3 extension for reporting suspicious URLs and (soon) checking risk scores via a phishing ML model.

---

## Project Recap (Current State)

**Backend (Flask)**
- App factory pattern (`app/__init__.py`), blueprints for web/auth/API.
- JWT-protected REST API at `/api/*`.
- Email confirmation enforced in **prod**; bypassed in **dev** when `FLASK_DEBUG=1`.
- Database models: `User`, `Report(user_id, url, source, created_at)`.
- Deployed on **Render** with a custom domain: **https://www.phishguard.shop**.
- Prod DB: **Render Postgres** (External DB URL set in env).

**Chrome Extension (MV3)**
- Popup supports: **Login**, **/api/me**, **Report current page**, **Recent reports**.
- Points to **local** or **prod** via `config.js`:
  - Dev: `const CONFIG = { API_BASE: "http://127.0.0.1:5000" };`
  - Prod: `const CONFIG = { API_BASE: "https://www.phishguard.shop" };`

**What’s Live (Endpoints)**
- `POST /api/login` → `{ access_token, refresh_token }`
- `POST /api/refresh` (refresh JWT)
- `GET  /api/me` (access JWT)
- `POST /api/report` (access JWT) → store a URL
- `GET  /api/reports` (access JWT) → latest reports (up to 50)
- `POST /api/check` → **stub** `{ url, score: 0.5, label: "unknown" }`
- `GET  /api/health` → `{ ok: true }`

---

## Quickstart (Dev on Windows PowerShell)

```powershell
# From project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Local env
copy .env.example .env
# Edit .env (SECRET_KEY, JWT_SECRET_KEY, SQLALCHEMY_DATABASE_URI=sqlite:///phishguard.sqlite3, Mailtrap if needed)

# DB
$env:FLASK_APP="wsgi.py"
flask db upgrade

# Run (dev; bypasses email confirm)
$env:FLASK_DEBUG="1"
flask run




Chrome Extension (Dev)
----------------------
    
*   Load unpacked at chrome://extensions, then **Reload**.
> **CORS note:** Unpacked extensions have different IDs per machine. In prod, allowlist the **published** extension ID. For dev on multiple machines, you can temporarily allow chrome-extension://\* via a regex in CORS.





Deploy (Render)
---------------

*   Service is connected to this repo/branch.
*   **Environment variables (prod)**
    *   SECRET\_KEY, JWT\_SECRET\_KEY → strong randoms
    *   SQLALCHEMY\_DATABASE\_URI → External Postgres URL
    *   Mailtrap SMTP vars (for confirm flow if/when enabled)
    *   **Do not** set FLASK\_DEBUG in prod
        
*   Start command: gunicorn wsgi:app





Data & Storage
--------------

*   **Dev**: SQLite (phishguard.sqlite3) as configured in .env.
*   **Prod**: Render Postgres (External DB URL).
*   All POST /api/report writes go to the DB of the environment you’re calling.
    
*   **Do not** store ML models or datasets in Postgres (size limits). Use:
    *   Repo (if the model is small), or
    *   Object storage (S3/Backblaze) and download/cache at startup, or
    *   Render persistent disk (paid).
        



ML Model (Random Forest) — Planned
----------------------------------

*   /api/check is currently a **stub**.
*   Team is sourcing phishing datasets and will train an RF model.
*   Inference plan:
    
    *   Load phish\_rf.joblib at startup (or on first request).
    *   Extract features from URL/context.
    *   predict\_proba → return { score, label }.
        

**Note on size limits:** Keep datasets out of the repo/DB; store the model artifact as a file (not in Postgres). If report volume grows, consider pruning/archiving or upgrading the DB.





What’s Next
-----------

*   **Email Confirm Flow**: add /api/resend-confirm and /api/confirm/ (Mailtrap) and keep confirm enforced in prod.
*   **Extension UX**: context menu “Report this page” + badge (✓/!).
*   **Reports API**: accept ?limit=5 to reduce payload for the popup.
*   **Model Integration**: real feature extractor + RF model in /api/check.
*   **Hardening**: rate limiting on /api/\*, keep CORS allowlist tight in prod.
*   **Dashboard**: admin/reporter view.





License
-------

MIT

::contentReference\[oaicite:0\]{index=0}