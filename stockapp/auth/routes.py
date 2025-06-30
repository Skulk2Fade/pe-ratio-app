from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime, timedelta
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

from ..extensions import db, login_manager
from ..models import User
from ..utils import send_email

auth_bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    message = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email')
        password = request.form['password']
        if User.query.filter_by(username=username).first():
            error = 'Username already exists'
        else:
            token = secrets.token_urlsafe(16)
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
                verification_token=token,
            )
            db.session.add(user)
            db.session.commit()
            verify_link = url_for('auth.verify_email', token=token, _external=True)
            send_email(email, 'Verify your account', f'Please click the link to verify your account: {verify_link}')
            message = 'Check your email to verify your account.'
    return render_template('signup.html', error=error, message=message)


@auth_bp.route('/verify/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.is_verified = True
        user.verification_token = None
        db.session.commit()
        msg = 'Email verified. You can now log in.'
    else:
        msg = 'Invalid or expired verification link.'
    return render_template('verify_email.html', message=msg)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    message = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            if not user.is_verified:
                message = 'Please verify your email before logging in.'
            elif user.mfa_enabled:
                code = f"{secrets.randbelow(1000000):06}"
                user.mfa_code = generate_password_hash(code)
                user.mfa_expiry = datetime.utcnow() + timedelta(minutes=5)
                db.session.commit()
                session['mfa_user_id'] = user.id
                send_email(user.email, 'Your verification code', f'Your login code is {code}')
                return redirect(url_for('auth.mfa_verify'))
            else:
                login_user(user)
                return redirect(url_for('main.index'))
        else:
            error = 'Invalid credentials'
    return render_template('login.html', error=error, message=message)


@auth_bp.route('/mfa_verify', methods=['GET', 'POST'])
def mfa_verify():
    error = None
    user_id = session.get('mfa_user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    user = User.query.get(user_id)
    if not user or not user.mfa_enabled:
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        code = request.form.get('code', '')
        if user.mfa_expiry and user.mfa_expiry < datetime.utcnow():
            error = 'Code expired'
        elif user.mfa_code and check_password_hash(user.mfa_code, code):
            user.mfa_code = None
            user.mfa_expiry = None
            db.session.commit()
            login_user(user)
            session.pop('mfa_user_id', None)
            return redirect(url_for('main.index'))
        else:
            error = 'Invalid code'
    return render_template('mfa_verify.html', error=error)


@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    error = None
    message = None
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(16)
            user.reset_token = token
            db.session.commit()
            reset_link = url_for('auth.reset_password', token=token, _external=True)
            send_email(email, 'Password reset', f'Click the link to reset your password: {reset_link}')
            message = 'Check your email for a password reset link.'
        else:
            error = 'Email not found'
    return render_template('forgot_password.html', error=error, message=message)


@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    error = None
    message = None
    user = User.query.filter_by(reset_token=token).first()
    if not user:
        error = 'Invalid or expired token'
        return render_template('reset_password.html', error=error)
    if request.method == 'POST':
        password = request.form.get('password')
        if password:
            user.password_hash = generate_password_hash(password)
            user.reset_token = None
            db.session.commit()
            message = 'Password updated. You can now log in.'
        else:
            error = 'Password required'
    return render_template('reset_password.html', error=error, message=message)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
