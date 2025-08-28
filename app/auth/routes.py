from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db
from ..models import User
from .forms import RegisterForm, LoginForm, RequestResetForm, ResetPasswordForm
from ..email_utils import generate_token, verify_token, send_email

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "warning")
            return redirect(url_for("auth.login"))
        user = User(email=email)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        token = generate_token(user.email, "confirm")
        confirm_url = url_for("auth.confirm_email", token=token, _external=True)
        send_email("Confirm your PhishGuard account", [user.email],
                   "emails/confirm.html", confirm_url=confirm_url)
        flash("Account created! Check your inbox for a confirmation link.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

@auth_bp.route("/confirm/<token>")
def confirm_email(token):
    email = verify_token(token, "confirm")
    if not email:
        flash("Confirmation link is invalid or expired.", "danger")
        return redirect(url_for("auth.resend_confirmation"))
    user = User.query.filter_by(email=email).first_or_404()
    if user.is_confirmed:
        flash("Email already confirmed. Please log in.", "info")
    else:
        user.email_confirmed_at = datetime.utcnow()
        db.session.commit()
        flash("Your email has been confirmed!", "success")
    return redirect(url_for("auth.login"))

@auth_bp.route("/resend-confirmation")
def resend_confirmation():
    if not current_user.is_authenticated:
        flash("Log in to resend your confirmation email.", "warning")
        return redirect(url_for("auth.login"))
    if current_user.is_confirmed:
        flash("Your email is already confirmed.", "info")
        return redirect(url_for("main.index"))
    token = generate_token(current_user.email, "confirm")
    confirm_url = url_for("auth.confirm_email", token=token, _external=True)
    send_email("Confirm your PhishGuard account", [current_user.email],
               "emails/confirm.html", confirm_url=confirm_url)
    flash("Confirmation email sent!", "success")
    return redirect(url_for("main.index"))

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Welcome back!", "success")
            next_page = request.args.get("next") or url_for("main.index")
            return redirect(next_page)
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form)

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

@auth_bp.route("/reset", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = RequestResetForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            token = generate_token(user.email, "reset")
            reset_url = url_for("auth.reset_token", token=token, _external=True)
            send_email("Reset your PhishGuard password", [user.email],
                       "emails/reset_password.html", reset_url=reset_url)
        flash("If that email exists, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password_request.html", form=form)

@auth_bp.route("/reset/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    email = verify_token(token, "reset")
    if not email:
        flash("Reset link is invalid or expired.", "danger")
        return redirect(url_for("auth.reset_request"))
    user = User.query.filter_by(email=email).first_or_404()
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("Password updated. You can now log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/reset_password.html", form=form)
