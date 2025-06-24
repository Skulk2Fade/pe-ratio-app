from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from .models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        email = request.form.get("email")
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            error = "Username already exists"
        else:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("main.index"))
    return render_template("signup.html", error=error)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("main.index"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("main.index"))
