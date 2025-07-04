from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_sock import Sock

# Initialize extensions without app, will be configured in create_app

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
sock = Sock()
