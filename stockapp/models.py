from datetime import datetime
from flask_login import UserMixin
from .extensions import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)
    phone_number = db.Column(db.String(20))
    sms_opt_in = db.Column(db.Boolean, default=False)
    trend_opt_in = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    verification_token_sent = db.Column(db.DateTime)
    reset_token = db.Column(db.String(100), unique=True)
    reset_token_sent = db.Column(db.DateTime)
    alert_frequency = db.Column(db.Integer, default=24)
    last_alert_time = db.Column(db.DateTime, default=datetime.utcnow)
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_code = db.Column(db.String(20))
    mfa_expiry = db.Column(db.DateTime)
    mfa_secret = db.Column(db.String(32))
    default_currency = db.Column(db.String(3), default="USD")
    language = db.Column(db.String(5), default="en")
    theme = db.Column(db.String(10), default="light")
    brokerage_token = db.Column(db.String(100))


class WatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    pe_threshold = db.Column(db.Float, default=30)
    de_threshold = db.Column(db.Float)
    rsi_threshold = db.Column(db.Float)
    ma_threshold = db.Column(db.Float)
    notes = db.Column(db.Text)
    tags = db.Column(db.String(100))
    is_public = db.Column(db.Boolean, default=False)


class FavoriteTicker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10))
    message = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class StockRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    price = db.Column(db.Float)
    eps = db.Column(db.Float)
    pe_ratio = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class PortfolioItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    price_paid = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    notes = db.Column(db.Text)
    tags = db.Column(db.String(100))


class PortfolioFollow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
