import os
from datetime import timedelta
from flask import Flask
from dotenv import load_dotenv

from .extensions import db, login_manager, mail, migrate, jwt, cors
from .auth.routes import auth_bp
from .main.routes import main_bp
from .api.routes import api_bp  # <- our API blueprint

def create_app():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    # Load .env from project root when running locally
    load_dotenv(os.path.join(os.path.dirname(base_dir), ".env"))

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-secret"),
        SQLALCHEMY_DATABASE_URI=os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///phishguard.sqlite3"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,

        # Mail
        MAIL_SERVER=os.getenv("MAIL_SERVER", "localhost"),
        MAIL_PORT=int(os.getenv("MAIL_PORT", "25")),
        MAIL_USE_TLS=os.getenv("MAIL_USE_TLS", "false").lower() in ("1", "true", "yes"),
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_DEFAULT_SENDER=os.getenv("MAIL_DEFAULT_SENDER", "noreply@example.com"),

        # Token salts
        SECURITY_EMAIL_SALT=os.getenv("SECURITY_EMAIL_SALT", "email-confirm-salt"),
        SECURITY_RESET_SALT=os.getenv("SECURITY_RESET_SALT", "reset-password-salt"),
        TOKEN_MAX_AGE=int(os.getenv("TOKEN_MAX_AGE", "86400")),  # 24h

        # JWT
        JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY") or os.getenv("SECRET_KEY", "dev-secret"),
        JWT_TOKEN_LOCATION=["headers"],
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=7),
    )

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    jwt.init_app(app)

    # CORS (we can tighten later)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # Blueprints (no extra prefixes here)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    return app
