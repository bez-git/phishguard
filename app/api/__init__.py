# app/__init__.py
from flask import Flask
from flask_cors import CORS

def create_app():
    app = Flask(__name__)
    # ... load config, init db/jwt/mail/etc.

    allowed_origins = [
        "https://phishguard.shop",
        "https://www.phishguard.shop",
        "chrome-extension://oobdjflidmpakodnfamfglhblmnjjnmf",  # your ext ID
        "http://127.0.0.1:5000",  # keep for local dev
    ]

    CORS(app,
         resources={r"/api/*": {"origins": allowed_origins}},
         allow_headers=["Authorization", "Content-Type"])

    from .api.routes import api_bp
    app.register_blueprint(api_bp)  # routes already have url_prefix="/api"
    return app