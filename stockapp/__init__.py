import os
from flask import Flask
from .extensions import db, login_manager, csrf
from .auth import auth_bp
from .main import main_bp
from .watchlists import watch_bp
from .tasks import start_scheduler


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_this_secret')

    db_url = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    app.config['SMTP_SERVER'] = os.environ.get('SMTP_SERVER', 'smtp.example.com')
    app.config['SMTP_PORT'] = int(os.environ.get('SMTP_PORT', 587))
    app.config['SMTP_USERNAME'] = os.environ.get('SMTP_USERNAME', 'user@example.com')
    app.config['SMTP_PASSWORD'] = os.environ.get('SMTP_PASSWORD', 'password')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)

    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(watch_bp)

    with app.app_context():
        db.create_all()

    start_scheduler()
    return app
