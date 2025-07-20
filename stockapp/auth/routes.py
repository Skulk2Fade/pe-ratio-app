import os
from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import pyotp

from ..extensions import db, login_manager, oauth
from ..models import User
from ..utils import send_email, NotificationError
from ..forms import SignupForm, LoginForm

auth_bp = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignupForm()
    error = None
    message = None
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        phone = form.phone.data
        sms_opt_in = form.sms_opt_in.data
        if User.query.filter_by(username=username).first():
            error = "Username already exists"
        else:
            token = secrets.token_urlsafe(16)
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
                phone_number=phone,
                sms_opt_in=sms_opt_in,
                verification_token=token,
                verification_token_sent=datetime.utcnow(),
            )
            db.session.add(user)
            db.session.commit()
            verify_link = url_for("auth.verify_email", token=token, _external=True)
            try:
                send_email(
                    email,
                    "Verify your account",
                    f"Please click the link to verify your account: {verify_link}",
                )
                message = "Check your email to verify your account."
            except NotificationError as e:
                error = f"Email failed: {e}"
    return render_template("signup.html", form=form, error=error, message=message)


@auth_bp.route("/verify/<token>")
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if (
        user
        and user.verification_token_sent
        and datetime.utcnow() - user.verification_token_sent <= timedelta(hours=24)
    ):
        user.is_verified = True
        user.verification_token = None
        user.verification_token_sent = None
        db.session.commit()
        msg = "Email verified. You can now log in."
    else:
        msg = "Invalid or expired verification link."
    return render_template("verify_email.html", message=msg)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    error = None
    message = None
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                message = "Please verify your email before logging in."
            elif user.mfa_enabled and user.mfa_secret:
                session["mfa_user_id"] = user.id
                return redirect(url_for("auth.mfa_verify"))
            else:
                login_user(user)
                return redirect(url_for("main.index"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", form=form, error=error, message=message)


@auth_bp.route("/login/<provider>")
def oauth_login(provider: str):
    if provider not in ("google", "github"):
        return redirect(url_for("auth.login"))
    redirect_uri = url_for("auth.oauth_callback", provider=provider, _external=True)
    client = oauth.create_client(provider)
    if not client:
        return redirect(url_for("auth.login"))
    return client.authorize_redirect(redirect_uri)


@auth_bp.route("/oauth_callback/<provider>")
def oauth_callback(provider: str):
    if provider not in ("google", "github"):
        return redirect(url_for("auth.login"))
    client = oauth.create_client(provider)
    if not client:
        return redirect(url_for("auth.login"))
    token = client.authorize_access_token()
    if provider == "google":
        user_info = client.parse_id_token(token)
        oauth_id = user_info.get("sub")
        email = user_info.get("email")
    else:
        resp = client.get("user", token=token)
        data = resp.json()
        oauth_id = data.get("id")
        email = data.get("email") or data.get("login")

    user = User.query.filter_by(oauth_provider=provider, oauth_id=str(oauth_id)).first()
    if not user:
        username = email.split("@")[0] if email else f"{provider}_{oauth_id}"
        if User.query.filter_by(username=username).first():
            username = f"{username}_{provider}"
        user = User(
            username=username,
            email=email,
            oauth_provider=provider,
            oauth_id=str(oauth_id),
            password_hash=generate_password_hash(os.urandom(8).hex()),
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for("main.index"))


@auth_bp.route("/mfa_verify", methods=["GET", "POST"])
def mfa_verify():
    error = None
    user_id = session.get("mfa_user_id")
    if not user_id:
        return redirect(url_for("auth.login"))
    user = User.query.get(user_id)
    if not user or not user.mfa_enabled or not user.mfa_secret:
        return redirect(url_for("auth.login"))
    if request.method == "POST":
        code = request.form.get("code", "")
        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code):
            login_user(user)
            session.pop("mfa_user_id", None)
            return redirect(url_for("main.index"))
        else:
            error = "Invalid code"
    return render_template("mfa_verify.html", error=error)


@auth_bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    error = None
    message = None
    if request.method == "POST":
        email = request.form.get("email")
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(16)
            user.reset_token = token
            user.reset_token_sent = datetime.utcnow()
            db.session.commit()
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            try:
                send_email(
                    email,
                    "Password reset",
                    f"Click the link to reset your password: {reset_link}",
                )
                message = "Check your email for a password reset link."
            except NotificationError as e:
                error = f"Email failed: {e}"
        else:
            error = "Email not found"
    return render_template("forgot_password.html", error=error, message=message)


@auth_bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    error = None
    message = None
    user = User.query.filter_by(reset_token=token).first()
    if (
        not user
        or not user.reset_token_sent
        or datetime.utcnow() - user.reset_token_sent > timedelta(hours=1)
    ):
        error = "Invalid or expired token"
        return render_template("reset_password.html", error=error)
    if request.method == "POST":
        password = request.form.get("password")
        if password:
            user.password_hash = generate_password_hash(password)
            user.reset_token = None
            user.reset_token_sent = None
            db.session.commit()
            message = "Password updated. You can now log in."
        else:
            error = "Password required"
    return render_template("reset_password.html", error=error, message=message)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
