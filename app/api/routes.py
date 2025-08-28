# app/api/routes.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from ..extensions import db
from ..models import User

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.get("/health")
def health():
    return jsonify(status="ok"), 200

@api_bp.post("/login")
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify(error="email and password required"), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify(error="invalid credentials"), 401

    if not user.is_confirmed:
        return jsonify(error="email_not_confirmed"), 403

    # 🔧 make identity a STRING
    access = create_access_token(identity=str(user.id), additional_claims={"email": user.email})
    refresh = create_refresh_token(identity=str(user.id))
    return jsonify(access_token=access, refresh_token=refresh), 200

@api_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    # 🔧 convert back to int for DB lookup if needed
    uid = int(get_jwt_identity())
    access = create_access_token(identity=str(uid))
    return jsonify(access_token=access), 200

@api_bp.get("/me")
@jwt_required()
def me():
    # 🔧 convert back to int for DB lookup
    uid = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user:
        return jsonify(error="user_not_found"), 404
    return jsonify(id=user.id, email=user.email, confirmed=user.is_confirmed), 200

