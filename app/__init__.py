import os
import atexit
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from apscheduler.schedulers.background import BackgroundScheduler

# Extensions
db = SQLAlchemy()
login_manager = LoginManager()
scheduler = BackgroundScheduler()


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change_this_secret")

    db_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SMTP_SERVER"] = os.environ.get("SMTP_SERVER", "smtp.example.com")
    app.config["SMTP_PORT"] = int(os.environ.get("SMTP_PORT", 587))
    app.config["SMTP_USERNAME"] = os.environ.get("SMTP_USERNAME", "user@example.com")
    app.config["SMTP_PASSWORD"] = os.environ.get("SMTP_PASSWORD", "password")

    api_key = os.environ.get("API_KEY")
    if not api_key:
        raise RuntimeError("API_KEY environment variable not set")
    app.config["API_KEY"] = api_key

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    with app.app_context():
        from . import models, tasks
        db.create_all()
        scheduler.add_job(tasks.check_watchlists, "interval", hours=1)
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())

    # Register blueprints
    from .auth import auth_bp
    from .main import main_bp
    from .user import user_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)

    return app

