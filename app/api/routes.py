from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from urllib.parse import urlparse

from ..extensions import db
from ..models import Report

# Mount this blueprint at /api
api_bp = Blueprint("api", __name__, url_prefix="/api")


def _is_url(s: str) -> bool:
    try:
        p = urlparse(s)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


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
    rows = (
        Report.query
        .filter_by(user_id=uid)
        .order_by(Report.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify([
        {
            "id": r.id,
            "url": r.url,
            "source": r.source,
            "created_at": r.created_at.isoformat()
        } for r in rows
    ])


# Stub for ML – will replace with Random Forest
@api_bp.route("/check", methods=["POST"])
@jwt_required()
def check_url():
    data = request.get_json() or {}
    url = (data.get("url") or "").strip()
    if not _is_url(url):
        return jsonify({"error": "invalid_url"}), 400
    return jsonify({"url": url, "score": 0.50, "label": "unknown"})
