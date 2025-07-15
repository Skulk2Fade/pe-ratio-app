import os
import pytest
from stockapp.config import ProductionConfig


def test_production_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("TWILIO_SID", "sid")
    monkeypatch.setenv("TWILIO_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM", "+1000")
    with pytest.raises(RuntimeError):
        ProductionConfig()


def test_production_requires_database(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TWILIO_SID", "sid")
    monkeypatch.setenv("TWILIO_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM", "+1000")
    with pytest.raises(RuntimeError):
        ProductionConfig()


def test_production_requires_twilio(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.delenv("TWILIO_SID", raising=False)
    monkeypatch.delenv("TWILIO_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_FROM", raising=False)
    with pytest.raises(RuntimeError):
        ProductionConfig()


def test_production_requires_smtp(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("TWILIO_SID", "sid")
    monkeypatch.setenv("TWILIO_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM", "+1000")
    monkeypatch.delenv("SMTP_SERVER", raising=False)
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://example:6379/1")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "redis://example:6379/1")
    with pytest.raises(RuntimeError):
        ProductionConfig()


def test_production_requires_redis(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/db")
    monkeypatch.setenv("TWILIO_SID", "sid")
    monkeypatch.setenv("TWILIO_TOKEN", "token")
    monkeypatch.setenv("TWILIO_FROM", "+1000")
    monkeypatch.setenv("SMTP_SERVER", "smtp.mail.com")
    monkeypatch.setenv("SMTP_USERNAME", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.delenv("CELERY_BROKER_URL", raising=False)
    monkeypatch.delenv("CELERY_RESULT_BACKEND", raising=False)
    with pytest.raises(RuntimeError):
        ProductionConfig()
