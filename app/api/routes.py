# app/api/routes.py
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, create_refresh_token
from urllib.parse import urlparse

from ..extensions import db
from ..predictions.models import User, Report


api_bp = Blueprint("api", __name__, url_prefix="/api")

def _is_url(s: str) -> bool:
    try:
        p = urlparse(s)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def _is_dev() -> bool:
    return os.getenv("FLASK_DEBUG") == "1" or os.getenv("FLASK_ENV") == "development"

@api_bp.route("/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"error": "missing_credentials"}), 400
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "invalid credentials"}), 401
    if not user.is_confirmed and not _is_dev():
        return jsonify({"error": "email_not_confirmed"}), 403
    access  = create_access_token(identity=str(user.id), additional_claims={"email": user.email})
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify({"access_token": access, "refresh_token": refresh})

@api_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    uid = int(get_jwt_identity())
    u = User.query.get(uid)
    return jsonify({"id": u.id, "email": u.email, "confirmed": u.is_confirmed})

@api_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()
    new_access = create_access_token(identity=str(uid))
    return jsonify({"access_token": new_access})

@api_bp.route("/report", methods=["POST"])
@jwt_required()
def make_report():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    source = (data.get("source") or "popup")[:32]
    if not _is_url(url):
        return jsonify({"error": "invalid_url"}), 400
    uid = int(get_jwt_identity())
    r = Report(user_id=uid, url=url[:2048], source=source)
    db.session.add(r)
    db.session.commit()
    return jsonify({"ok": True, "id": r.id})

@api_bp.route("/reports", methods=["GET"])
@jwt_required()
def list_reports():
    uid = int(get_jwt_identity())
    rows = (Report.query.filter_by(user_id=uid)
            .order_by(Report.created_at.desc())
            .limit(50).all())
    return jsonify([
        {"id": r.id, "url": r.url, "source": r.source, "created_at": r.created_at.isoformat()}
        for r in rows
    ])

@api_bp.route("/check", methods=["POST"])
@jwt_required()
def check_url():
    # Lazy import so migrations / CLI don't pull in heavy ML deps at import time
    from ..predictions.predict import score_url, label_url

    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    if not _is_url(url):
        return jsonify({"error": "invalid_url"}), 400
    try:
        s = float(score_url(url))
        l = label_url(url)
        return jsonify({"url": url, "score": round(s, 6), "label": l}), 200
    except Exception as e:
        return jsonify({"error": f"ml_inference_failed: {e}"}), 500
