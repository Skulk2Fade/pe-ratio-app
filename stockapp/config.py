import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load variables from a .env file if present
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class Config:
    """Base configuration with defaults suitable for production."""

    SECRET_KEY = secrets.token_hex(16)
    SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SMTP_SERVER = "smtp.example.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "user@example.com"
    SMTP_PASSWORD = "password"

    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/0"

    CHECK_WATCHLISTS_CRON = "0 * * * *"
    SEND_TREND_SUMMARIES_CRON = "0 8 * * *"
    SYNC_BROKERAGE_CRON = "0 6 * * *"
    CHECK_DIVIDENDS_CRON = "0 9 * * *"
    CLEANUP_OLD_DATA_CRON = "0 3 * * *"
    DATA_SNAPSHOT_CRON = "0 7 * * *"

    TWILIO_SID = ""
    TWILIO_TOKEN = ""
    TWILIO_FROM = ""

    VAPID_PUBLIC_KEY = ""
    VAPID_PRIVATE_KEY = ""

    BABEL_DEFAULT_LOCALE = "en"
    BABEL_TRANSLATION_DIRECTORIES = "translations"

    REALTIME_PROVIDER = "fmp"
    PRICE_STREAM_INTERVAL = 5
    ASYNC_REALTIME = False

    GOOGLE_CLIENT_ID = ""
    GOOGLE_CLIENT_SECRET = ""
    GITHUB_CLIENT_ID = ""
    GITHUB_CLIENT_SECRET = ""

    DEBUG = False

    def __init__(self):
        self.SECRET_KEY = os.environ.get("SECRET_KEY", self.SECRET_KEY)
        db_url = os.environ.get("DATABASE_URL", self.SQLALCHEMY_DATABASE_URI)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        self.SQLALCHEMY_DATABASE_URI = db_url
        self.SMTP_SERVER = os.environ.get("SMTP_SERVER", self.SMTP_SERVER)
        self.SMTP_PORT = int(os.environ.get("SMTP_PORT", self.SMTP_PORT))
        self.SMTP_USERNAME = os.environ.get("SMTP_USERNAME", self.SMTP_USERNAME)
        self.SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", self.SMTP_PASSWORD)
        self.CELERY_BROKER_URL = os.environ.get(
            "CELERY_BROKER_URL", self.CELERY_BROKER_URL
        )
        self.CELERY_RESULT_BACKEND = os.environ.get(
            "CELERY_RESULT_BACKEND", self.CELERY_RESULT_BACKEND
        )
        self.TWILIO_SID = os.environ.get("TWILIO_SID", self.TWILIO_SID)
        self.TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", self.TWILIO_TOKEN)
        self.TWILIO_FROM = os.environ.get("TWILIO_FROM", self.TWILIO_FROM)
        self.VAPID_PUBLIC_KEY = os.environ.get(
            "VAPID_PUBLIC_KEY", self.VAPID_PUBLIC_KEY
        )
        self.VAPID_PRIVATE_KEY = os.environ.get(
            "VAPID_PRIVATE_KEY", self.VAPID_PRIVATE_KEY
        )
        self.REALTIME_PROVIDER = os.environ.get(
            "REALTIME_PROVIDER", self.REALTIME_PROVIDER
        )
        self.ASYNC_REALTIME = os.environ.get("ASYNC_REALTIME", "0").lower() in [
            "1",
            "true",
            "yes",
        ]
        self.PRICE_STREAM_INTERVAL = float(
            os.environ.get("PRICE_STREAM_INTERVAL", self.PRICE_STREAM_INTERVAL)
        )
        self.CHECK_WATCHLISTS_CRON = os.environ.get(
            "CHECK_WATCHLISTS_CRON", self.CHECK_WATCHLISTS_CRON
        )
        self.SEND_TREND_SUMMARIES_CRON = os.environ.get(
            "SEND_TREND_SUMMARIES_CRON", self.SEND_TREND_SUMMARIES_CRON
        )
        self.SYNC_BROKERAGE_CRON = os.environ.get(
            "SYNC_BROKERAGE_CRON", self.SYNC_BROKERAGE_CRON
        )
        self.CHECK_DIVIDENDS_CRON = os.environ.get(
            "CHECK_DIVIDENDS_CRON", self.CHECK_DIVIDENDS_CRON
        )
        self.CLEANUP_OLD_DATA_CRON = os.environ.get(
            "CLEANUP_OLD_DATA_CRON", self.CLEANUP_OLD_DATA_CRON
        )
        self.DATA_SNAPSHOT_CRON = os.environ.get(
            "DATA_SNAPSHOT_CRON", self.DATA_SNAPSHOT_CRON
        )
        self.GOOGLE_CLIENT_ID = os.environ.get(
            "GOOGLE_CLIENT_ID", self.GOOGLE_CLIENT_ID
        )
        self.GOOGLE_CLIENT_SECRET = os.environ.get(
            "GOOGLE_CLIENT_SECRET", self.GOOGLE_CLIENT_SECRET
        )
        self.GITHUB_CLIENT_ID = os.environ.get(
            "GITHUB_CLIENT_ID", self.GITHUB_CLIENT_ID
        )
        self.GITHUB_CLIENT_SECRET = os.environ.get(
            "GITHUB_CLIENT_SECRET", self.GITHUB_CLIENT_SECRET
        )


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False

    def __init__(self):
        super().__init__()
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError("SECRET_KEY must be set in production")
        if not os.environ.get("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in production")
        if (
            self.SMTP_SERVER == "smtp.example.com"
            or self.SMTP_USERNAME == "user@example.com"
            or self.SMTP_PASSWORD == "password"
        ):
            raise RuntimeError("Valid SMTP settings must be provided in production")
        if (
            self.CELERY_BROKER_URL == "redis://localhost:6379/0"
            or self.CELERY_RESULT_BACKEND == "redis://localhost:6379/0"
        ):
            raise RuntimeError("Valid Redis settings must be provided in production")
        missing_twilio = [
            var
            for var in ("TWILIO_SID", "TWILIO_TOKEN", "TWILIO_FROM")
            if not os.environ.get(var)
        ]
        if missing_twilio:
            raise RuntimeError(
                "Missing Twilio configuration: " + ", ".join(missing_twilio)
            )
