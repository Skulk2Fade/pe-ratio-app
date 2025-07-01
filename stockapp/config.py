import os
import secrets


class Config:
    """Base configuration with defaults suitable for production."""

    SECRET_KEY = secrets.token_hex(16)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SMTP_SERVER = 'smtp.example.com'
    SMTP_PORT = 587
    SMTP_USERNAME = 'user@example.com'
    SMTP_PASSWORD = 'password'

    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

    DEBUG = False

    def __init__(self):
        self.SECRET_KEY = os.environ.get('SECRET_KEY', self.SECRET_KEY)
        db_url = os.environ.get('DATABASE_URL', self.SQLALCHEMY_DATABASE_URI)
        if db_url.startswith('postgres://'):
            db_url = db_url.replace('postgres://', 'postgresql://', 1)
        self.SQLALCHEMY_DATABASE_URI = db_url
        self.SMTP_SERVER = os.environ.get('SMTP_SERVER', self.SMTP_SERVER)
        self.SMTP_PORT = int(os.environ.get('SMTP_PORT', self.SMTP_PORT))
        self.SMTP_USERNAME = os.environ.get('SMTP_USERNAME', self.SMTP_USERNAME)
        self.SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', self.SMTP_PASSWORD)
        self.CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', self.CELERY_BROKER_URL)
        self.CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', self.CELERY_RESULT_BACKEND)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
