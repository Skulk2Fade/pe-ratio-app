from datetime import datetime, timedelta

from celery import Celery
from celery.schedules import crontab

from .extensions import db
from .models import User, WatchlistItem, Alert, PortfolioItem
from .utils import (
    get_stock_data,
    get_historical_prices,
    moving_average,
    calculate_rsi,
    send_email,
    send_sms,
    notify_user_push,
    ALERT_PE_THRESHOLD,
    get_upcoming_dividends,
)
from .portfolio.helpers import (
    sync_portfolio_from_brokerage,
    sync_transactions_from_brokerage,
)

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
        "check-dividends-daily": {
            "task": "stockapp.tasks.check_dividends_task",
            "schedule": crontab(minute=0, hour=9),
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
                debt_to_equity,
                *_rest,
            ) = get_stock_data(item.symbol)
            alerts = []
            if price is not None and eps:
                pe_ratio = round(price / eps, 2)
                threshold = item.pe_threshold or ALERT_PE_THRESHOLD
                if pe_ratio > threshold:
                    alerts.append(
                        f"{item.symbol} P/E ratio {pe_ratio} exceeds threshold {threshold}"
                    )
            if (
                debt_to_equity is not None
                and item.de_threshold is not None
                and debt_to_equity > item.de_threshold
            ):
                alerts.append(
                    f"{item.symbol} Debt/Equity {round(debt_to_equity,2)} exceeds threshold {item.de_threshold}"
                )
            if item.rsi_threshold is not None or item.ma_threshold is not None:
                _d, prices = get_historical_prices(item.symbol, days=60)
                if prices:
                    if item.rsi_threshold is not None:
                        rsi = calculate_rsi(prices, 14)
                        if rsi and rsi[-1] is not None and rsi[-1] > item.rsi_threshold:
                            alerts.append(
                                f"{item.symbol} RSI {rsi[-1]} exceeds threshold {item.rsi_threshold}"
                            )
                    if item.ma_threshold is not None and price is not None:
                        ma = moving_average(prices, 50)
                        if ma and ma[-1] is not None:
                            diff = abs(price - ma[-1]) / ma[-1] * 100
                            if diff > item.ma_threshold:
                                alerts.append(
                                    f"{item.symbol} price deviation {round(diff,2)}% exceeds {item.ma_threshold}% from 50d MA"
                                )
            for msg in alerts:
                send_email(user.email, "Watchlist Alert", msg)
                if user.sms_opt_in and user.phone_number:
                    send_sms(user.phone_number, msg)
                db.session.add(Alert(symbol=item.symbol, message=msg, user_id=user.id))
                notify_user_push(user.id, msg)
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
    users = User.query.filter(
        (User.brokerage_token.isnot(None)) | (User.brokerage_access_token.isnot(None))
    ).all()
    for user in users:
        token = user.brokerage_access_token or user.brokerage_token
        sync_portfolio_from_brokerage(
            user.id,
            token,
            refresh=user.brokerage_refresh_token,
            expiry=user.brokerage_token_expiry,
        )
        sync_transactions_from_brokerage(
            user.id,
            token,
            refresh=user.brokerage_refresh_token,
            expiry=user.brokerage_token_expiry,
        )


@celery.task(name="stockapp.tasks.sync_brokerage_task")
def sync_brokerage_task():
    """Celery task wrapper for ``_sync_brokerage``."""
    _sync_brokerage()


def _check_dividends():
    """Notify users of upcoming dividend ex-dates."""
    today = datetime.utcnow().date()
    end = today + timedelta(days=7)
    users = User.query.all()
    for user in users:
        if not user.email:
            continue
        items = PortfolioItem.query.filter_by(user_id=user.id).all()
        for item in items:
            events = get_upcoming_dividends(item.symbol, days=7)
            for ev in events:
                date_str = ev.get("date")
                if not date_str:
                    continue
                try:
                    ex_date = datetime.fromisoformat(date_str).date()
                except Exception:
                    continue
                if today <= ex_date <= end:
                    msg = f"{item.symbol} dividend ex-date on {date_str}"
                    send_email(user.email, "Dividend Reminder", msg)
                    if user.sms_opt_in and user.phone_number:
                        send_sms(user.phone_number, msg)
                    db.session.add(
                        Alert(symbol=item.symbol, message=msg, user_id=user.id)
                    )
                    notify_user_push(user.id, msg)
    db.session.commit()


@celery.task(name="stockapp.tasks.check_dividends_task")
def check_dividends_task():
    """Celery task wrapper for ``_check_dividends``."""
    _check_dividends()
