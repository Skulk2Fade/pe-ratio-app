from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_sock import Sock

try:
    from flask_babel import Babel
except Exception:  # pragma: no cover - optional dependency

    class Babel:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            app.jinja_env.globals.setdefault("_", lambda s: s)

        def localeselector(self, func):
            return func


babel = Babel()

# Initialize extensions without app, will be configured in create_app

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
sock = Sock()
