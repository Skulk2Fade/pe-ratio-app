from flask import Blueprint, render_template, request, session, redirect, url_for, make_response, current_app
from flask_login import current_user
import csv
import io
from fpdf import FPDF
from babel.numbers import format_currency, format_decimal
from ..extensions import db
from ..models import History, Alert, WatchlistItem
from ..utils import (
    get_stock_data,
    get_historical_prices,
    get_locale,
    ALERT_PE_THRESHOLD,
)

main_bp = Blueprint('main', __name__)


@main_bp.route('/service-worker.js')
def service_worker():
    return current_app.send_static_file('service-worker.js')


@main_bp.route('/', methods=['GET', 'POST'])
def index():
    symbol = ''
    price = eps = pe_ratio = valuation = company_name = logo_url = market_cap = None
    sector = industry = exchange = currency = debt_to_equity = None
    pb_ratio = roe = roa = profit_margin = analyst_rating = dividend_yield = None
    earnings_growth = forward_pe = price_to_sales = None
    error_message = alert_message = None
    history_dates = history_prices = []
    interest_amount = interest_rate = interest_result = None
    active_tab = 'pe'

    if request.method == 'GET':
        symbol = request.args.get('ticker', '').upper() or symbol

    if current_user.is_authenticated:
        history_entries = (
            History.query.filter_by(user_id=current_user.id)
            .order_by(History.timestamp.desc())
            .limit(10)
            .all()
        )
        history = [h.symbol for h in history_entries]
    else:
        history = session.get('history', [])

    if request.method == 'POST':
        if request.form.get('calc_type') == 'interest':
            active_tab = 'interest'
            try:
                interest_amount = float(request.form.get('amount', 0))
                interest_rate = float(request.form.get('rate', 0))
                interest_result = round(interest_amount * interest_rate / 100, 2)
            except ValueError:
                error_message = 'Invalid amount or interest rate.'
        else:
            symbol = request.form['ticker'].upper()

    if (request.method == 'POST' and request.form.get('calc_type') != 'interest') or symbol:
        try:
            (
                company_name,
                logo_url,
                sector,
                industry,
                exchange,
                currency,
                price,
                eps,
                market_cap,
                debt_to_equity,
                pb_ratio,
                roe,
                roa,
                profit_margin,
                analyst_rating,
                dividend_yield,
                earnings_growth,
                forward_pe,
                price_to_sales,
            ) = get_stock_data(symbol)

            history_dates, history_prices = get_historical_prices(symbol, days=90)

            if price is not None and eps:
                pe_ratio_val = round(price / eps, 2)
                pe_ratio = format_decimal(pe_ratio_val, locale=get_locale())
                if pe_ratio_val < 15:
                    valuation = 'Undervalued?'
                elif pe_ratio_val > 25:
                    valuation = 'Overvalued?'
                else:
                    valuation = 'Fairly Valued'
                threshold = ALERT_PE_THRESHOLD
                if current_user.is_authenticated:
                    item = WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first()
                    if item and item.pe_threshold is not None:
                        threshold = item.pe_threshold
                if pe_ratio_val > threshold:
                    alert_message = f'P/E ratio {pe_ratio_val} exceeds threshold of {threshold}'
                    if current_user.is_authenticated:
                        db.session.add(Alert(symbol=symbol, message=alert_message, user_id=current_user.id))
                        db.session.commit()
            elif price is None or eps is None:
                error_message = 'Price or EPS data is missing.'
            if debt_to_equity is not None:
                debt_to_equity = format_decimal(round(debt_to_equity, 2), locale=get_locale())
            if pb_ratio is not None:
                pb_ratio = format_decimal(round(pb_ratio, 2), locale=get_locale())
            if roe is not None:
                roe = format_decimal(round(roe * 100, 2), locale=get_locale())
            if roa is not None:
                roa = format_decimal(round(roa * 100, 2), locale=get_locale())
            if profit_margin is not None:
                profit_margin = format_decimal(round(profit_margin * 100, 2), locale=get_locale())
            if dividend_yield is not None:
                dividend_yield = format_decimal(round(dividend_yield * 100, 2), locale=get_locale())
            if earnings_growth is not None:
                earnings_growth = format_decimal(round(earnings_growth * 100, 2), locale=get_locale())
            if forward_pe is not None:
                forward_pe = format_decimal(round(forward_pe, 2), locale=get_locale())
            if price_to_sales is not None:
                price_to_sales = format_decimal(round(price_to_sales, 2), locale=get_locale())
            if price is not None:
                price = format_currency(price, currency, locale=get_locale())
            if eps is not None:
                eps = format_currency(eps, currency, locale=get_locale())

            if symbol:
                if current_user.is_authenticated:
                    db.session.add(History(symbol=symbol, user_id=current_user.id))
                    db.session.commit()
                    history.insert(0, symbol)
                    history = history[:10]
                else:
                    if symbol in history:
                        history.remove(symbol)
                    history.insert(0, symbol)
                    history = history[:10]
                    session['history'] = history
        except Exception as e:
            error_message = str(e)

    return render_template(
        'index.html',
        symbol=symbol,
        price=price,
        eps=eps,
        pe_ratio=pe_ratio,
        valuation=valuation,
        company_name=company_name,
        logo_url=logo_url,
        market_cap=market_cap,
        sector=sector,
        industry=industry,
        exchange=exchange,
        currency=currency,
        debt_to_equity=debt_to_equity,
        pb_ratio=pb_ratio,
        roe=roe,
        roa=roa,
        profit_margin=profit_margin,
        analyst_rating=analyst_rating,
        dividend_yield=dividend_yield,
        earnings_growth=earnings_growth,
        forward_pe=forward_pe,
        price_to_sales=price_to_sales,
        error_message=error_message,
        alert_message=alert_message,
        history_dates=history_dates,
        history_prices=history_prices,
        history=history,
        interest_amount=interest_amount,
        interest_rate=interest_rate,
        interest_result=interest_result,
        active_tab=active_tab,
    )


@main_bp.route('/clear_history')
def clear_history():
    if current_user.is_authenticated:
        History.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    else:
        session.pop('history', None)
    return redirect(url_for('main.index'))


@main_bp.route('/download')
def download():
    symbol = request.args.get('symbol', '').upper()
    fmt = request.args.get('format', 'csv').lower()
    if not symbol:
        return 'Symbol missing', 400

    (
        company_name,
        _logo_url,
        sector,
        industry,
        exchange,
        currency,
        price,
        eps,
        market_cap,
        debt_to_equity,
        pb_ratio,
        roe,
        roa,
        profit_margin,
        analyst_rating,
        dividend_yield,
        earnings_growth,
        forward_pe,
        price_to_sales,
    ) = get_stock_data(symbol)

    if price is not None and eps:
        pe_ratio_val = round(price / eps, 2)
        if pe_ratio_val < 15:
            valuation = 'Undervalued?'
        elif pe_ratio_val > 25:
            valuation = 'Overvalued?'
        else:
            valuation = 'Fairly Valued'
        pe_ratio = format_decimal(pe_ratio_val, locale=get_locale())
    else:
        pe_ratio = valuation = 'N/A'

    if debt_to_equity is not None:
        debt_to_equity = format_decimal(round(debt_to_equity, 2), locale=get_locale())
    if pb_ratio is not None:
        pb_ratio = format_decimal(round(pb_ratio, 2), locale=get_locale())
    if roe is not None:
        roe = format_decimal(round(roe * 100, 2), locale=get_locale())
    if roa is not None:
        roa = format_decimal(round(roa * 100, 2), locale=get_locale())
    if profit_margin is not None:
        profit_margin = format_decimal(round(profit_margin * 100, 2), locale=get_locale())
    if dividend_yield is not None:
        dividend_yield = format_decimal(round(dividend_yield * 100, 2), locale=get_locale())
    if earnings_growth is not None:
        earnings_growth = format_decimal(round(earnings_growth * 100, 2), locale=get_locale())
    if forward_pe is not None:
        forward_pe = format_decimal(round(forward_pe, 2), locale=get_locale())
    if price_to_sales is not None:
        price_to_sales = format_decimal(round(price_to_sales, 2), locale=get_locale())

    if price is not None:
        price = format_currency(price, currency, locale=get_locale())
    if eps is not None:
        eps = format_currency(eps, currency, locale=get_locale())

    if fmt == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Company Name',
            'Symbol',
            'Price',
            'EPS',
            'P/E Ratio',
            'Valuation',
            'Market Cap',
            'Debt/Equity',
            'P/B',
            'ROE %',
            'ROA %',
            'Profit Margin %',
            'Analyst Rating',
            'Dividend Yield %',
            'Earnings Growth %',
            'Forward P/E',
            'P/S Ratio',
            'Sector',
            'Industry',
            'Exchange',
            'Currency',
        ])
        writer.writerow([
            company_name,
            symbol,
            price,
            eps,
            pe_ratio,
            valuation,
            market_cap,
            debt_to_equity,
            pb_ratio,
            roe,
            roa,
            profit_margin,
            analyst_rating,
            dividend_yield,
            earnings_growth,
            forward_pe,
            price_to_sales,
            sector,
            industry,
            exchange,
            currency,
        ])
        response = make_response(output.getvalue())
        response.headers['Content-Disposition'] = f'attachment; filename={symbol}_data.csv'
        response.headers['Content-Type'] = 'text/csv'
        return response
    elif fmt == 'pdf':
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font('Arial', size=12)
        pdf.cell(0, 10, txt=f'Stock Data for {symbol}', ln=1)
        fields = [
            ('Company Name', company_name),
            ('Price', price),
            ('EPS', eps),
            ('P/E Ratio', pe_ratio),
            ('Valuation', valuation),
            ('Market Cap', market_cap),
            ('Debt/Equity', debt_to_equity),
            ('P/B', pb_ratio),
            ('ROE %', roe),
            ('ROA %', roa),
            ('Profit Margin %', profit_margin),
            ('Analyst Rating', analyst_rating),
            ('Dividend Yield %', dividend_yield),
            ('Earnings Growth %', earnings_growth),
            ('Forward P/E', forward_pe),
            ('P/S Ratio', price_to_sales),
            ('Sector', sector),
            ('Industry', industry),
            ('Exchange', exchange),
            ('Currency', currency),
        ]
        for label, value in fields:
            pdf.cell(0, 10, txt=f'{label}: {value}', ln=1)
        pdf_output = pdf.output(dest='S').encode('latin-1')
        response = make_response(pdf_output)
        response.headers['Content-Disposition'] = f'attachment; filename={symbol}_data.pdf'
        response.headers['Content-Type'] = 'application/pdf'
        return response
    else:
        return 'Invalid format', 400
