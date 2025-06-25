from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_login import login_required, current_user
import csv
import io
from babel.dates import format_datetime

from ..extensions import db
from babel.numbers import format_currency

from ..models import (
    WatchlistItem,
    FavoriteTicker,
    Alert,
    History,
    PortfolioItem,
)
from ..utils import get_locale, ALERT_PE_THRESHOLD, get_stock_data

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


@watch_bp.route('/export_portfolio')
@login_required
def export_portfolio():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Symbol', 'Quantity', 'Price Paid'])
    for item in items:
        writer.writerow([item.symbol, item.quantity, item.price_paid])
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=portfolio.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


@watch_bp.route('/portfolio', methods=['GET', 'POST'])
@login_required
def portfolio():
    symbol_prefill = request.args.get('symbol', '').upper()
    if request.method == 'POST':
        if request.files.get('file'):
            file = request.files['file']
            content = file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                symbol = row.get('Symbol', '').upper()
                try:
                    quantity = float(row.get('Quantity', 0))
                    price_paid = float(row.get('Price Paid', 0))
                except (TypeError, ValueError):
                    continue
                if symbol and quantity and price_paid:
                    if not PortfolioItem.query.filter_by(user_id=current_user.id, symbol=symbol).first():
                        db.session.add(
                            PortfolioItem(
                                symbol=symbol,
                                quantity=quantity,
                                price_paid=price_paid,
                                user_id=current_user.id,
                            )
                        )
            db.session.commit()
        elif request.form.get('item_id'):
            item_id = int(request.form['item_id'])
            quantity = request.form.get('quantity', type=float)
            price_paid = request.form.get('price_paid', type=float)
            item = PortfolioItem.query.get_or_404(item_id)
            if item.user_id == current_user.id:
                if quantity is not None:
                    item.quantity = quantity
                if price_paid is not None:
                    item.price_paid = price_paid
                db.session.commit()
        else:
            symbol = request.form['symbol'].upper()
            quantity = request.form.get('quantity', type=float)
            price_paid = request.form.get('price_paid', type=float)
            if quantity is not None and price_paid is not None:
                if not PortfolioItem.query.filter_by(user_id=current_user.id, symbol=symbol).first():
                    db.session.add(
                        PortfolioItem(
                            symbol=symbol,
                            quantity=quantity,
                            price_paid=price_paid,
                            user_id=current_user.id,
                        )
                    )
                    db.session.commit()
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    data = []
    for item in items:
        (
            _name,
            _logo_url,
            _sector,
            _industry,
            _exchange,
            currency,
            price,
            *_rest,
        ) = get_stock_data(item.symbol)
        if price is not None:
            current_price = format_currency(price, currency, locale=get_locale())
            value = format_currency(price * item.quantity, currency, locale=get_locale())
            pl = format_currency((price - item.price_paid) * item.quantity, currency, locale=get_locale())
        else:
            current_price = value = pl = None
        data.append(
            {
                'item': item,
                'current_price': current_price,
                'value': value,
                'profit_loss': pl,
            }
        )
    return render_template('portfolio.html', items=data, symbol=symbol_prefill)


@watch_bp.route('/portfolio/delete/<int:item_id>')
@login_required
def delete_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('watch.portfolio'))
