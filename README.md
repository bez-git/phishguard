PhishGuard

Files to Extension : 
https://drive.google.com/drive/folders/1yR-pS1MigUfD7Lxv-qdisMeh9a8LW1GN?usp=drive_link

Flask API + Chrome MV3 extension for real-time phishing risk detection.
The extension sends page/link URLs; the API serves a trained model and returns a label + score.



Status (Oct 2025)
Backend: Flask (app factory + JWT auth).
Model serving: phish_rf.joblib + imputer_phi.joblib (via Git LFS), feature_order.json (12 features), optional tld_freq.json.
Safe NaN handling + light post-processing (IP+login bump; HTTPS .gov/.edu de-escalation).
Data: /api/report stores { url, score, label, evaluated_at }.
Extension (MV3): Auto-check on tab activate/complete, badge, link auto-scan & cache, notifications, popup with login & Scan Page.
Deploy: Render (web + Postgres). Git LFS required for model binaries.



API (quick)
Auth
POST /api/login → { access_token, refresh_token }
POST /api/refresh → { access_token }
GET /api/me → current user (Bearer)

Scoring
POST /api/check → { ok, url, label, score, threshold }
GET /api/debug_check?url=... → features + imputed vector + scores
GET /api/health → model/threshold + diagnostics

Reports
POST /api/report, GET /api/reports (auth)




How to quick Start 
# Create venv & install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# .env (minimal)
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=change-me
JWT_SECRET_KEY=change-me-too
SQLALCHEMY_DATABASE_URI=sqlite:///phishguard.sqlite3
PHISH_THRESHOLD=0.90
PHISH_NAN_DEFAULT=0.5

# DB + run
$env:FLASK_APP="wsgi.py"
flask db upgrade
flask run --reload --port 5000



Extension (dev)
chrome://extensions → enable Developer mode → Load unpacked → phishguard_chrome_extension_v2/
Edit phishguard_chrome_extension_v2/config.js:
const CONFIG = { API_BASE: "http://127.0.0.1:5000" };
Open the popup → Log in → Scan this page.



Deploy (Render)
Git LFS: repo tracks .joblib artifacts via LFS.
Build command
bash scripts/render-build.sh
(Downloads portable git-lfs during build, runs git lfs pull, then pip install -r requirements.txt.)
Start command
FLASK_APP=wsgi.py flask db upgrade && \
gunicorn -w 1 -k gthread --threads 4 --timeout 120 -b 0.0.0.0:$PORT wsgi:app
1 worker keeps memory sane; threads share the same model.
Python version: runtime.txt → python-3.12.5
Env vars (prod): SECRET_KEY, JWT_SECRET_KEY, DATABASE_URL (Postgres), optional PHISH_THRESHOLD (prod currently 0.85), PHISH_NAN_DEFAULT=0.5.
Health check: GET /api/health should show n_features_in: 12 and your threshold.


Troubleshooting
Extension says “Failed to fetch” → check CORS, service status, and /api/health.
502 / OOM → ensure 1 gunicorn worker; instance with sufficient RAM (model ~160 MB + app).