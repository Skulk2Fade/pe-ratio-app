from datetime import datetime, timedelta

from celery import Celery
from celery.schedules import crontab

from .extensions import db
from .models import User, WatchlistItem, Alert, PortfolioItem
from .utils import (
    get_stock_data,
    get_historical_prices,
    send_email,
    send_sms,
    ALERT_PE_THRESHOLD,
)
from .portfolio.helpers import sync_portfolio_from_brokerage

# Celery application instance configured in ``init_celery``.
celery = Celery(__name__)


def init_celery(app):
    """Configure Celery with the Flask app context."""
    celery.conf.update(
        broker_url=app.config.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
        result_backend=app.config.get(
            "CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
        ),
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

    celery.Task = ContextTask

    celery.conf.beat_schedule = {
        "check-watchlists-hourly": {
            "task": "stockapp.tasks.check_watchlists_task",
            "schedule": crontab(minute=0, hour="*"),
        },
        "send-trend-summaries-daily": {
            "task": "stockapp.tasks.send_trend_summaries_task",
            "schedule": crontab(minute=0, hour=8),
        },
        "sync-brokerage-daily": {
            "task": "stockapp.tasks.sync_brokerage_task",
            "schedule": crontab(minute=0, hour=6),
        },
    }


def _check_watchlists():
    """Check all user watchlists and send alerts when thresholds are exceeded."""
    now = datetime.utcnow()
    users = User.query.all()
    for user in users:
        if not user.email:
            continue
        freq = user.alert_frequency or 24
        last = user.last_alert_time or datetime.min
        if now - last < timedelta(hours=freq):
            continue
        items = WatchlistItem.query.filter_by(user_id=user.id).all()
        for item in items:
            (
                _name,
                _logo_url,
                _sector,
                _industry,
                _exchange,
                currency,
                price,
                eps,
                _market_cap,
                _debt_to_equity,
                *_rest,
            ) = get_stock_data(item.symbol)
            if price is not None and eps:
                pe_ratio = round(price / eps, 2)
                threshold = item.pe_threshold or ALERT_PE_THRESHOLD
                if pe_ratio > threshold:
                    msg = f"{item.symbol} P/E ratio {pe_ratio} exceeds threshold {threshold}"
                    send_email(user.email, "P/E Ratio Alert", msg)
                    if user.sms_opt_in and user.phone_number:
                        send_sms(user.phone_number, msg)
                    db.session.add(
                        Alert(symbol=item.symbol, message=msg, user_id=user.id)
                    )
        user.last_alert_time = now
    db.session.commit()


@celery.task(name="stockapp.tasks.check_watchlists_task")
def check_watchlists_task():
    """Celery task wrapper for ``_check_watchlists``."""
    _check_watchlists()


def _send_trend_summaries():
    """Compile and email weekly summaries to opted-in users."""
    users = User.query.filter_by(trend_opt_in=True).all()
    for user in users:
        if not user.email:
            continue
        lines = []
        p_items = PortfolioItem.query.filter_by(user_id=user.id).all()
        if p_items:
            lines.append("Portfolio changes (7d):")
            for item in p_items:
                _d, prices = get_historical_prices(item.symbol, days=7)
                if len(prices) >= 2 and prices[0]:
                    change = prices[-1] - prices[0]
                    pct = (change / prices[0]) * 100
                    lines.append(f"{item.symbol}: {pct:+.2f}%")
        w_items = WatchlistItem.query.filter_by(user_id=user.id).all()
        if w_items:
            lines.append("\nWatchlist performance (7d):")
            for item in w_items:
                _d, prices = get_historical_prices(item.symbol, days=7)
                if len(prices) >= 2 and prices[0]:
                    change = prices[-1] - prices[0]
                    pct = (change / prices[0]) * 100
                    lines.append(f"{item.symbol}: {pct:+.2f}%")
        if lines:
            body = "\n".join(lines)
            send_email(user.email, "MarketMinder Summary", body)


@celery.task(name="stockapp.tasks.send_trend_summaries_task")
def send_trend_summaries_task():
    """Celery task wrapper for ``_send_trend_summaries``."""
    _send_trend_summaries()


def _sync_brokerage():
    """Synchronize portfolios with brokerage holdings."""
    users = User.query.filter(User.brokerage_token.isnot(None)).all()
    for user in users:
        sync_portfolio_from_brokerage(user.id, user.brokerage_token)


@celery.task(name="stockapp.tasks.sync_brokerage_task")
def sync_brokerage_task():
    """Celery task wrapper for ``_sync_brokerage``."""
    _sync_brokerage()
