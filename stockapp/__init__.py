import os
from flask import Flask
from werkzeug.security import generate_password_hash

# Load environment variables before importing modules that depend on them
from .config import Config, DevelopmentConfig, ProductionConfig

from .extensions import db, login_manager, csrf, sock, babel, migrate
from flask_migrate import upgrade
from .models import User
from .auth import auth_bp
from .main import main_bp
from .watchlists import watch_bp
from .portfolio import portfolio_bp
from .alerts import alerts_bp
from .calculators import calc_bp
from .api import api_bp
from .brokerage_routes import broker_bp
from .screener import screener_bp
from .tasks import init_celery


def create_app(config_class=None):
    """Application factory accepting an optional configuration class."""
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # Determine which configuration to use
    if config_class is None:
        env = os.environ.get("FLASK_ENV")
        if env == "development":
            config_class = DevelopmentConfig
        elif env == "production":
            config_class = ProductionConfig
        else:
            config_class = Config

    app.config.from_object(config_class())

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    csrf.init_app(app)
    sock.init_app(app)
    babel.init_app(app)

    from .utils import get_locale

    @babel.localeselector
    def locale_selector():
        return get_locale()

    @app.context_processor
    def inject_globals():
        from flask_wtf.csrf import generate_csrf

        return {"csrf_token": generate_csrf, "app_name": "MarketMinder"}

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(watch_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(calc_bp)
    app.register_blueprint(screener_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(broker_bp)

    with app.app_context():
        try:
            upgrade()
        except Exception:
            db.create_all()

        # Only create the default user in development mode
        if app.config.get("ENV") == "development":
            default_user = os.environ.get("DEFAULT_USERNAME", "testuser")
            default_pass = os.environ.get("DEFAULT_PASSWORD", "testpass")
            if default_user and default_pass:
                if not User.query.filter_by(username=default_user).first():
                    user = User(
                        username=default_user,
                        password_hash=generate_password_hash(default_pass),
                        is_verified=True,
                        default_currency="USD",
                        language="en",
                        theme="light",
                    )
                    db.session.add(user)
                    db.session.commit()

    init_celery(app)
    return app
