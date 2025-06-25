from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

from flask import current_app
from .extensions import db
from .models import User, WatchlistItem, Alert
from .utils import get_stock_data, send_email, ALERT_PE_THRESHOLD

scheduler = BackgroundScheduler()


def check_watchlists():
    with current_app.app_context():
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
                        msg = f'{item.symbol} P/E ratio {pe_ratio} exceeds threshold {threshold}'
                        send_email(user.email, 'P/E Ratio Alert', msg)
                        db.session.add(Alert(symbol=item.symbol, message=msg, user_id=user.id))
            user.last_alert_time = now
        db.session.commit()


def start_scheduler():
    scheduler.add_job(check_watchlists, 'interval', hours=1)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
