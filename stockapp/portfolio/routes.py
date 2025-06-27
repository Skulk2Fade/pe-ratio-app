from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_login import login_required, current_user
import csv
import io
from babel.numbers import format_currency

from ..extensions import db
from ..models import PortfolioItem
from ..utils import get_locale, get_stock_data

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/export_portfolio')
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

@portfolio_bp.route('/portfolio', methods=['GET', 'POST'])
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
    total_value = 0.0
    total_pl = 0.0
    totals_currency = None
    sector_totals = {}
    for item in items:
        (
            _name,
            _logo_url,
            sector,
            _industry,
            _exchange,
            currency,
            price,
            *_rest,
        ) = get_stock_data(item.symbol)
        if price is not None:
            current_price = format_currency(price, currency, locale=get_locale())
            value_num = price * item.quantity
            pl_num = (price - item.price_paid) * item.quantity
            value = format_currency(value_num, currency, locale=get_locale())
            pl = format_currency(pl_num, currency, locale=get_locale())
            total_value += value_num
            total_pl += pl_num
            if totals_currency is None:
                totals_currency = currency
            if sector:
                sector_totals[sector] = sector_totals.get(sector, 0) + value_num
        else:
            current_price = value = pl = None
            value_num = 0
        data.append(
            {
                'item': item,
                'current_price': current_price,
                'value': value,
                'profit_loss': pl,
            }
        )
    totals = None
    if items and totals_currency:
        totals = {
            'value': format_currency(total_value, totals_currency, locale=get_locale()),
            'profit_loss': format_currency(total_pl, totals_currency, locale=get_locale()),
        }
    diversification = []
    risk_assessment = None
    if total_value > 0:
        for sec, val in sector_totals.items():
            pct = round(val / total_value * 100, 2)
            diversification.append({'sector': sec, 'percentage': pct})
        diversification.sort(key=lambda x: x['percentage'], reverse=True)
        if diversification:
            top = diversification[0]
            if top['percentage'] > 50:
                risk_assessment = f"High concentration in {top['sector']}"
            elif top['percentage'] > 30:
                risk_assessment = f"Moderate concentration in {top['sector']}"
            else:
                risk_assessment = 'Well diversified across sectors.'
    return render_template('portfolio.html', items=data, symbol=symbol_prefill, totals=totals, diversification=diversification, risk_assessment=risk_assessment)

@portfolio_bp.route('/portfolio/delete/<int:item_id>')
@login_required
def delete_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('portfolio.portfolio'))
