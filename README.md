# PhishGuard (Flask Auth Starter)

A minimal, production-friendly Flask starter with user accounts, email verification, and password reset.
Designed for team collaboration and future Chrome Extension + ML integration.

## Quickstart (Windows PowerShell)

```powershell
# From your project folder
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Copy env template and edit values
copy .env.example .env
# Open .env in VSCode and set SECRET_KEY and SMTP creds

# Initialize database
$env:FLASK_APP="wsgi.py"
flask db init
flask db migrate -m "init"
flask db upgrade

# Run dev server
flask run
```

Visit http://127.0.0.1:5000/

## Features
- Register, login, logout
- Email confirmation (link expires after 1 day by default)
- Password reset via email
- CSRF protection
- Bootstrap 5 UI
- App factory pattern & Blueprints
- Flask-Migrate for DB migrations
- Ready for GitHub & deployment

## Next Steps
- Add REST API + JWT for Chrome Extension
- Build Chrome extension that talks to Flask
- Add ML phishing model endpoints (next week)
- Switch SQLite -> Postgres in production

## License
MIT
