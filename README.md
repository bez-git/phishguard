# PhishGuard

A Flask backend + Chrome MV3 extension for reporting suspicious URLs and (soon) returning phishing risk scores from a machine-learning model.

---

## Status

- **Backend**: Flask app with app-factory pattern and JWT-secured REST endpoints is live.  
- **Auth & Data**: Users, JWT login/refresh, and URL reporting are implemented with a relational DB.  
- **Chrome Extension (MV3)**: Popup can authenticate, fetch `/api/me`, submit URL reports, and display recent reports.  
- **ML Integration**: `/api/check` exists as a **stub**; model inference wiring is planned next.  
- **Deployment**: Deployed on Render with a custom domain.  
- **Environments**: SQLite for local dev; Postgres in production.

---

## Features (Current)

### Backend (Flask)
- App factory + Blueprints (web/auth/API)
- JWT auth and email confirm flow (enforced in prod; bypassed in dev)
- Database models: `User`, `Report (user_id, url, source, created_at)`
- Health check endpoint

### Chrome Extension (MV3)
- Login and token handling
- Report current tab URL to the backend
- View recent reports
- Switchable API base (local vs prod) via `config.js`

---

## API (Current Endpoints)

- `POST /api/login` → `{ access_token, refresh_token }`  
- `POST /api/refresh` → issue a new access token  
- `GET /api/me` → current user (requires access token)  
- `POST /api/report` → store a reported URL (requires access token)  
- `GET /api/reports` → latest reports (requires access token)  
- `POST /api/check` → **stub**: `{ url, score: 0.5, label: "unknown" }`  
- `GET /api/health` → `{ ok: true }`

> **Note:** Model inference is not live yet; `/api/check` is a placeholder until the feature extractor + model loader are integrated.

---

## Quickstart (Dev)

```bash
# From project root
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt

# Local environment
copy .env.example .env  # then edit SECRET_KEY, JWT_SECRET_KEY, SQLALCHEMY_DATABASE_URI, Mailtrap if used

# Database
$env:FLASK_APP="wsgi.py"
flask db upgrade

# Run (dev; email confirm bypassed when FLASK_DEBUG=1)
$env:FLASK_DEBUG="1"
flask run
