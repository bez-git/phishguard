import os
from flask import current_app, render_template, url_for
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, BadTimeSignature, SignatureExpired
from .extensions import mail

def _serializer(purpose: str) -> URLSafeTimedSerializer:
    secret_key = current_app.config["SECRET_KEY"]
    salt = (current_app.config["SECURITY_EMAIL_SALT"] if purpose == "confirm" 
            else current_app.config["SECURITY_RESET_SALT"])
    return URLSafeTimedSerializer(secret_key=secret_key, salt=salt)

def generate_token(email: str, purpose: str) -> str:
    return _serializer(purpose).dumps(email)

def verify_token(token: str, purpose: str, max_age=None) -> str | None:
    s = _serializer(purpose)
    max_age = max_age or current_app.config["TOKEN_MAX_AGE"]
    try:
        return s.loads(token, max_age=max_age)
    except (BadTimeSignature, SignatureExpired):
        return None

def send_email(subject: str, recipients: list[str], html_template: str, **context):
    msg = Message(subject=subject, recipients=recipients)
    msg.html = render_template(html_template, **context)
    mail.send(msg)
