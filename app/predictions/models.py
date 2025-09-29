from __future__ import annotations

from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from ..extensions import db, login_manager


# ---------------------------------------
# User model
# ---------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    email_confirmed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Link to Report objects; delete reports when user is deleted
    reports = db.relationship(
        "Report",
        backref="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="dynamic",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_confirmed(self) -> bool:
        return self.email_confirmed_at is not None

    def __repr__(self) -> str:  # helpful for debugging
        return f"<User id={self.id} email={self.email} confirmed={self.is_confirmed}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


# ---------------------------------------
# Report model (with ML evaluation fields)
# ---------------------------------------
class Report(db.Model):
    __tablename__ = "report"

    id = db.Column(db.Integer, primary_key=True)

    # FK to user; cascade delete at DB level
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url = db.Column(db.String(2048), nullable=False, index=True)
    source = db.Column(db.String(32), nullable=False, default="popup", index=True)
    note = db.Column(db.String(512))

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # --- ML scoring persistence (new) ---
    # These let you store the last inference result for the URL at the time of report.
    score = db.Column(db.Float, nullable=True)              # probability of phishing (0..1)
    label = db.Column(db.String(8), nullable=True)          # "phish" | "legit"
    evaluated_at = db.Column(db.DateTime, nullable=True)    # when the model was applied

    def evaluate(self, commit: bool = False) -> dict:
        """
        Run ML inference on this report's URL using app/predictions code.
        This does a local import to avoid circular imports and heavy startup costs.
        Returns a dict with {"url", "score", "label", "evaluated_at"}.
        """
        # Lazy import to prevent circular deps and avoid loading the model at app import time.
        from .predictions.predict import score_url, label_url  # type: ignore

        url = self.url
        s = float(score_url(url))
        l = str(label_url(url))  # uses saved threshold inside predictions code

        now = datetime.utcnow()
        self.score = s
        self.label = l
        self.evaluated_at = now

        db.session.add(self)
        if commit:
            db.session.commit()

        return {"url": url, "score": s, "label": l, "evaluated_at": now}

    def clear_evaluation(self, commit: bool = False) -> None:
        """Reset stored ML results (useful if you re-run with a new model)."""
        self.score = None
        self.label = None
        self.evaluated_at = None
        db.session.add(self)
        if commit:
            db.session.commit()

    def __repr__(self) -> str:
        return (
            f"<Report id={self.id} user_id={self.user_id} "
            f"url={self.url!r} label={self.label} score={self.score}>"
        )
