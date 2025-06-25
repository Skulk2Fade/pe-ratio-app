from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_login import login_required, current_user
import csv
import io
from babel.dates import format_datetime

from ..extensions import db
from ..models import WatchlistItem, FavoriteTicker, Alert, History
from ..utils import get_locale, ALERT_PE_THRESHOLD

watch_bp = Blueprint('watch', __name__)


@watch_bp.route('/watchlist', methods=['GET', 'POST'])
@login_required
def watchlist():
    if request.method == 'POST':
        if request.form.get('item_id'):
            item_id = int(request.form['item_id'])
            threshold = request.form.get('threshold', type=float)
            item = WatchlistItem.query.get_or_404(item_id)
            if item.user_id == current_user.id:
                item.pe_threshold = threshold or ALERT_PE_THRESHOLD
                db.session.commit()
        else:
            symbol = request.form['symbol'].upper()
            threshold = request.form.get('threshold', type=float) or ALERT_PE_THRESHOLD
            if not WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first():
                db.session.add(WatchlistItem(symbol=symbol, user_id=current_user.id, pe_threshold=threshold))
                db.session.commit()
    items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template('watchlist.html', items=items, default_threshold=ALERT_PE_THRESHOLD)


@watch_bp.route('/watchlist/delete/<int:item_id>')
@login_required
def delete_watchlist_item(item_id):
    item = WatchlistItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('watch.watchlist'))


@watch_bp.route('/add_watchlist/<symbol>')
@login_required
def add_watchlist(symbol):
    symbol = symbol.upper()
    if not WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first():
        db.session.add(WatchlistItem(symbol=symbol, user_id=current_user.id, pe_threshold=ALERT_PE_THRESHOLD))
        db.session.commit()
    return redirect(url_for('main.index', ticker=symbol))


@watch_bp.route('/favorites', methods=['GET', 'POST'])
@login_required
def favorites():
    if request.method == 'POST':
        symbol = request.form['symbol'].upper()
        if not FavoriteTicker.query.filter_by(user_id=current_user.id, symbol=symbol).first():
            db.session.add(FavoriteTicker(symbol=symbol, user_id=current_user.id))
            db.session.commit()
    items = FavoriteTicker.query.filter_by(user_id=current_user.id).all()
    return render_template('favorites.html', items=items)


@watch_bp.route('/favorites/delete/<int:item_id>')
@login_required
def delete_favorite(item_id):
    item = FavoriteTicker.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('watch.favorites'))


@watch_bp.route('/add_favorite/<symbol>')
@login_required
def add_favorite(symbol):
    symbol = symbol.upper()
    if not FavoriteTicker.query.filter_by(user_id=current_user.id, symbol=symbol).first():
        db.session.add(FavoriteTicker(symbol=symbol, user_id=current_user.id))
        db.session.commit()
    return redirect(url_for('main.index', ticker=symbol))


@watch_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        freq = request.form.get('frequency', type=int)
        if freq and freq > 0:
            current_user.alert_frequency = freq
            db.session.commit()
    return render_template('settings.html', frequency=current_user.alert_frequency)


@watch_bp.route('/alerts')
@login_required
def alerts():
    entries = (
        Alert.query.filter_by(user_id=current_user.id)
        .order_by(Alert.timestamp.desc())
        .all()
    )
    return render_template('alerts.html', alerts=entries)


@watch_bp.route('/clear_alerts')
@login_required
def clear_alerts():
    Alert.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for('watch.alerts'))


@watch_bp.route('/export_history')
@login_required
def export_history():
    entries = (
        History.query.filter_by(user_id=current_user.id)
        .order_by(History.timestamp.desc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Symbol', 'Timestamp'])
    for e in entries:
        timestamp = format_datetime(e.timestamp, locale=get_locale())
        writer.writerow([e.symbol, timestamp])
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=history.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response
