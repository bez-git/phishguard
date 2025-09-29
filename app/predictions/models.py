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

    id = db.Column(db.Integer, primary_key=True)  # Unique user ID (primary key)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)  # User email (unique, indexed)
    password_hash = db.Column(db.String(255), nullable=False)  # Hashed password
    is_active = db.Column(db.Boolean, default=True)  # User account active status
    email_confirmed_at = db.Column(db.DateTime, nullable=True)  # Timestamp when email was confirmed
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Account creation timestamp

    # Link to Report objects; delete reports when user is deleted
    reports = db.relationship(
        "Report",                  # Related model
        backref="user",            # Adds .user to Report for easy access
        cascade="all, delete-orphan",  # Delete reports if user is deleted
        passive_deletes=True,      # Let DB handle cascade deletes
        lazy="dynamic",            # Query returns a query object, not a list
    )

    def set_password(self, password: str) -> None:
        # Hash and store the user's password securely
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        # Verify a password against the stored hash
        return check_password_hash(self.password_hash, password)

    @property
    def is_confirmed(self) -> bool:
        # Returns True if the user's email has been confirmed
        return self.email_confirmed_at is not None

    def __repr__(self) -> str:  # helpful for debugging
        # String representation for debugging/logging
        return f"<User id={self.id} email={self.email} confirmed={self.is_confirmed}>"


# Flask-Login user loader callback
# This function is called by Flask-Login to load a user from the session.
@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    try:
        # Query the database for the user by ID
        return User.query.get(int(user_id))
    except Exception:
        # If there's an error (e.g., invalid ID), return None
        return None


# ---------------------------------------
# Report model (with ML evaluation fields)
# ---------------------------------------
class Report(db.Model):
    __tablename__ = "report"

    id = db.Column(db.Integer, primary_key=True)  # Unique report ID (primary key)

    # Foreign key to User; ensures reports are linked to a user.
    # Cascade delete at DB level: if user is deleted, their reports are deleted too.
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    url = db.Column(db.String(2048), nullable=False, index=True)  # Reported URL (indexed for fast lookup)
    source = db.Column(db.String(32), nullable=False, default="popup", index=True)  # How the report was submitted (e.g., popup, API)
    note = db.Column(db.String(512))  # Optional user note or description

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Timestamp when report was created

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
        # Lazy import to prevent circular dependencies and avoid loading the ML model at app import time.
        from .predictions.predict import score_url, label_url  # type: ignore

        url = self.url  # Get the URL from the report
        s = float(score_url(url))  # Run ML scoring function to get phishing probability
        l = str(label_url(url))    # Get label ("phish" or "legit") using saved threshold

        now = datetime.utcnow()    # Timestamp for when evaluation occurs
        self.score = s             # Store score in the report
        self.label = l             # Store label in the report
        self.evaluated_at = now    # Store evaluation timestamp

        db.session.add(self)       # Add changes to the session
        if commit:
            db.session.commit()    # Commit changes if requested

            # Return evaluation results as a dictionary
            return {"url": url, "score": s, "label": l, "evaluated_at": now}
    
        def clear_evaluation(self, commit: bool = False) -> None:
            """
            Reset stored ML results (score, label, evaluated_at) for this report.
            Useful if you want to re-run inference with a new model or threshold.
            """
            self.score = None           # Remove stored score
            self.label = None           # Remove stored label
            self.evaluated_at = None    # Remove evaluation timestamp
            db.session.add(self)        # Add changes to the session
            if commit:
                db.session.commit()     # Commit changes if requested
    
        def __repr__(self) -> str:
            # String representation for debugging/logging
            return (
                f"<Report id={self.id} user_id={self.user_id} "
                f"url={self.url!r} label={self.label} score={self.score}>"
            )
