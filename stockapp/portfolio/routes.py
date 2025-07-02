from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_login import login_required, current_user
import csv
import io
from babel.numbers import format_currency

from ..extensions import db
from ..models import PortfolioItem
from statistics import correlation, stdev

from ..utils import get_locale, get_stock_data, get_historical_prices
from ..forms import PortfolioAddForm, PortfolioUpdateForm, PortfolioImportForm

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
    add_form = PortfolioAddForm(symbol=symbol_prefill)
    import_form = PortfolioImportForm()
    update_form = PortfolioUpdateForm()

    if request.method == 'POST':
        if request.files.get('file'):
            if import_form.validate_on_submit():
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
            if update_form.validate_on_submit():
                item_id = update_form.item_id.data
                quantity = update_form.quantity.data
                price_paid = update_form.price_paid.data
                item = PortfolioItem.query.get_or_404(item_id)
                if item.user_id == current_user.id:
                    if quantity is not None:
                        item.quantity = quantity
                    if price_paid is not None:
                        item.price_paid = price_paid
                    db.session.commit()
        else:
            if add_form.validate_on_submit():
                symbol = add_form.symbol.data.upper()
                quantity = add_form.quantity.data
                price_paid = add_form.price_paid.data
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
                'price_num': price,
                'value_num': value_num,
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
        # Calculate correlations and portfolio volatility
        returns = {}
        weights = {}
        for row in data:
            sym = row['item'].symbol
            price_num = row['price_num']
            if price_num is None:
                continue
            weights[sym] = row['value_num'] / total_value if total_value else 0
            _dates, prices = get_historical_prices(sym, days=30)
            if len(prices) > 1:
                r = []
                for i in range(1, len(prices)):
                    try:
                        if prices[i-1]:
                            r.append((prices[i] - prices[i-1]) / prices[i-1])
                    except Exception:
                        pass
                if r:
                    returns[sym] = r
        correlations = []
        if returns:
            syms = list(returns.keys())
            for i in range(len(syms)):
                r1 = returns[syms[i]]
                for j in range(i + 1, len(syms)):
                    r2 = returns[syms[j]]
                    n = min(len(r1), len(r2))
                    if n > 1:
                        try:
                            c = correlation(r1[-n:], r2[-n:])
                            correlations.append({'pair': f'{syms[i]}-{syms[j]}', 'value': round(c, 2)})
                        except Exception:
                            pass
        portfolio_volatility = None
        if returns and len(returns) > 0:
            n = min(len(r) for r in returns.values())
            if n > 1:
                portfolio_returns = []
                for idx in range(-n, 0):
                    day_ret = 0.0
                    for sym, r in returns.items():
                        if len(r) >= n:
                            day_ret += weights.get(sym, 0) * r[idx]
                    portfolio_returns.append(day_ret)
                if len(portfolio_returns) > 1:
                    try:
                        vol = stdev(portfolio_returns) * (252 ** 0.5)
                        portfolio_volatility = round(vol * 100, 2)
                    except Exception:
                        portfolio_volatility = None
    else:
        correlations = []
        portfolio_volatility = None
    return render_template(
        'portfolio.html',
        symbols=[row['item'].symbol for row in data],
        items=data,
        symbol=symbol_prefill,
        totals=totals,
        diversification=diversification,
        risk_assessment=risk_assessment,
        correlations=correlations,
        portfolio_volatility=portfolio_volatility,
        add_form=add_form,
        import_form=import_form,
        update_form=update_form,
    )

@portfolio_bp.route('/portfolio/delete/<int:item_id>')
@login_required
def delete_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('portfolio.portfolio'))
