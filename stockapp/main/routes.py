from flask import (
    Blueprint,
    render_template,
    request,
    session,
    redirect,
    url_for,
    make_response,
    current_app,
    Response,
)
from flask_login import current_user
import csv
import io
from fpdf import FPDF
from babel.numbers import format_currency, format_decimal
import json
from ..utils import (
    get_stock_data,
    get_historical_prices,
    get_locale,
    ALERT_PE_THRESHOLD,
    moving_average,
    calculate_rsi,
    calculate_macd,
    bollinger_bands,
    generate_xlsx,
    notify_user_push,
)
import time
from ..extensions import db, sock
from ..models import History, Alert, WatchlistItem, StockRecord

main_bp = Blueprint("main", __name__)


@main_bp.route("/service-worker.js")
def service_worker():
    return current_app.send_static_file("service-worker.js")


@main_bp.route("/health")
def health():
    """Simple health check endpoint."""
    return "OK", 200


@main_bp.route("/stream_price")
def stream_price():
    """Server-Sent Events endpoint streaming price and EPS."""
    symbol = request.args.get("symbol", "").upper()
    if not symbol:
        return "Symbol required", 400

    def generate():
        loops = 0
        while True:
            try:
                (
                    _name,
                    _logo_url,
                    _sector,
                    _industry,
                    _exchange,
                    _currency,
                    price,
                    eps,
                    *_rest,
                ) = get_stock_data(symbol)
                data = json.dumps({"price": price, "eps": eps})
            except Exception:
                data = json.dumps({"error": "fetch"})
            yield f"data: {data}\n\n"
            loops += 1
            if current_app.config.get("TESTING") and loops >= 2:
                break
            time.sleep(5)

    return Response(generate(), mimetype="text/event-stream")


@sock.route("/ws/price")
def ws_price(ws):
    """WebSocket endpoint streaming price and EPS."""
    symbol = (ws.receive() or "").upper()
    if not symbol:
        ws.send(json.dumps({"error": "symbol required"}))
        return

    loops = 0
    while True:
        try:
            (
                _name,
                _logo_url,
                _sector,
                _industry,
                _exchange,
                _currency,
                price,
                eps,
                *_rest,
            ) = get_stock_data(symbol)
            data = json.dumps({"price": price, "eps": eps})
        except Exception:
            data = json.dumps({"error": "fetch"})
        ws.send(data)
        loops += 1
        if current_app.config.get("TESTING") and loops >= 2:
            break
        time.sleep(5)


@main_bp.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    price = eps = pe_ratio = valuation = company_name = logo_url = market_cap = None
    sector = industry = exchange = currency = debt_to_equity = None
    pb_ratio = roe = roa = profit_margin = analyst_rating = dividend_yield = (
        payout_ratio
    ) = None
    earnings_growth = forward_pe = price_to_sales = ev_to_ebitda = price_to_fcf = (
        current_ratio
    ) = None
    peg_ratio = None
    error_message = alert_message = None
    history_dates = history_prices = []
    ma20 = ma50 = rsi_values = []
    macd_vals = macd_signal = []
    bb_upper = bb_lower = []
    # calculators moved to separate blueprint

    if request.method == "GET":
        symbol = request.args.get("ticker", "").upper() or symbol

    if current_user.is_authenticated:
        history_entries = (
            History.query.filter_by(user_id=current_user.id)
            .order_by(History.timestamp.desc())
            .limit(10)
            .all()
        )
        history = [h.symbol for h in history_entries]
    else:
        history = session.get("history", [])

    if request.method == "POST":
        symbol = request.form.get("ticker", "").upper()

    if symbol:
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
                payout_ratio,
                earnings_growth,
                forward_pe,
                price_to_sales,
                ev_to_ebitda,
                price_to_fcf,
                current_ratio,
            ) = get_stock_data(symbol)

            if current_user.is_authenticated and current_user.default_currency:
                currency = current_user.default_currency

            history_dates, history_prices = get_historical_prices(symbol, days=90)
            ma20 = moving_average(history_prices, 20)
            ma50 = moving_average(history_prices, 50)
            rsi_values = calculate_rsi(history_prices, 14)
            macd_vals, macd_signal = calculate_macd(history_prices)
            bb_upper, bb_lower = bollinger_bands(history_prices, 20, 2)

            raw_price = price
            raw_eps = eps
            raw_pe_ratio_val = None

            if price is not None and eps:
                pe_ratio_val = round(price / eps, 2)
                pe_ratio = format_decimal(pe_ratio_val, locale=get_locale())
                raw_pe_ratio_val = pe_ratio_val
                peg_ratio_val = None
                if earnings_growth not in (None, 0):
                    try:
                        growth_pct = float(earnings_growth)
                        if growth_pct != 0:
                            peg_ratio_val = pe_ratio_val / (growth_pct * 100)
                    except (TypeError, ValueError):
                        peg_ratio_val = None
                if peg_ratio_val is not None:
                    peg_ratio = format_decimal(
                        round(peg_ratio_val, 2), locale=get_locale()
                    )
                if pe_ratio_val < 15:
                    valuation = "Undervalued?"
                elif pe_ratio_val > 25:
                    valuation = "Overvalued?"
                else:
                    valuation = "Fairly Valued"
                threshold = ALERT_PE_THRESHOLD
                de_thr = rsi_thr = ma_thr = None
                if current_user.is_authenticated:
                    item = WatchlistItem.query.filter_by(
                        user_id=current_user.id, symbol=symbol
                    ).first()
                    if item:
                        if item.pe_threshold is not None:
                            threshold = item.pe_threshold
                        de_thr = item.de_threshold
                        rsi_thr = item.rsi_threshold
                        ma_thr = item.ma_threshold
                if pe_ratio_val > threshold:
                    alert_message = (
                        f"P/E ratio {pe_ratio_val} exceeds threshold of {threshold}"
                    )
                    if current_user.is_authenticated:
                        db.session.add(
                            Alert(
                                symbol=symbol,
                                message=alert_message,
                                user_id=current_user.id,
                            )
                        )
                        db.session.commit()
                        notify_user_push(current_user.id, alert_message)
                elif (
                    de_thr is not None
                    and debt_to_equity is not None
                    and debt_to_equity > de_thr
                ):
                    alert_message = f"Debt/Equity {round(debt_to_equity,2)} exceeds threshold of {de_thr}"
                    if current_user.is_authenticated:
                        db.session.add(
                            Alert(
                                symbol=symbol,
                                message=alert_message,
                                user_id=current_user.id,
                            )
                        )
                        db.session.commit()
                        notify_user_push(current_user.id, alert_message)
                elif rsi_thr is not None or ma_thr is not None:
                    if history_prices:
                        if rsi_thr is not None:
                            rsi_val = calculate_rsi(history_prices, 14)
                            if (
                                rsi_val
                                and rsi_val[-1] is not None
                                and rsi_val[-1] > rsi_thr
                            ):
                                alert_message = (
                                    f"RSI {rsi_val[-1]} exceeds threshold of {rsi_thr}"
                                )
                        if (
                            alert_message is None
                            and ma_thr is not None
                            and price is not None
                        ):
                            ma_val = moving_average(history_prices, 50)
                            if ma_val and ma_val[-1] is not None:
                                diff = abs(price - ma_val[-1]) / ma_val[-1] * 100
                                if diff > ma_thr:
                                    alert_message = f"Price deviation {round(diff,2)}% exceeds {ma_thr}% from 50d MA"
                        if alert_message and current_user.is_authenticated:
                            db.session.add(
                                Alert(
                                    symbol=symbol,
                                    message=alert_message,
                                    user_id=current_user.id,
                                )
                            )
                            db.session.commit()
                            notify_user_push(current_user.id, alert_message)
            elif price is None or eps is None:
                error_message = "Price or EPS data is missing."
            if debt_to_equity is not None:
                debt_to_equity = format_decimal(
                    round(debt_to_equity, 2), locale=get_locale()
                )
            if pb_ratio is not None:
                pb_ratio = format_decimal(round(pb_ratio, 2), locale=get_locale())
            if roe is not None:
                roe = format_decimal(round(roe * 100, 2), locale=get_locale())
            if roa is not None:
                roa = format_decimal(round(roa * 100, 2), locale=get_locale())
            if profit_margin is not None:
                profit_margin = format_decimal(
                    round(profit_margin * 100, 2), locale=get_locale()
                )
            if dividend_yield is not None:
                dividend_yield = format_decimal(
                    round(dividend_yield * 100, 2), locale=get_locale()
                )
            if payout_ratio is not None:
                payout_ratio = format_decimal(
                    round(payout_ratio * 100, 2), locale=get_locale()
                )
            if earnings_growth is not None:
                earnings_growth = format_decimal(
                    round(earnings_growth * 100, 2), locale=get_locale()
                )
            if forward_pe is not None:
                forward_pe = format_decimal(round(forward_pe, 2), locale=get_locale())
            if price_to_sales is not None:
                price_to_sales = format_decimal(
                    round(price_to_sales, 2), locale=get_locale()
                )
            if ev_to_ebitda is not None:
                ev_to_ebitda = format_decimal(
                    round(ev_to_ebitda, 2), locale=get_locale()
                )
            if price_to_fcf is not None:
                price_to_fcf = format_decimal(
                    round(price_to_fcf, 2), locale=get_locale()
                )
            if current_ratio is not None:
                current_ratio = format_decimal(
                    round(current_ratio, 2), locale=get_locale()
                )
            if price is not None:
                price = format_currency(price, currency, locale=get_locale())
            if eps is not None:
                eps = format_currency(eps, currency, locale=get_locale())

            if symbol:
                if current_user.is_authenticated:
                    db.session.add(History(symbol=symbol, user_id=current_user.id))
                    db.session.add(
                        StockRecord(
                            symbol=symbol,
                            price=raw_price,
                            eps=raw_eps,
                            pe_ratio=raw_pe_ratio_val,
                            user_id=current_user.id,
                        )
                    )
                    db.session.commit()
                    history.insert(0, symbol)
                    history = history[:10]
                else:
                    if symbol in history:
                        history.remove(symbol)
                    history.insert(0, symbol)
                    history = history[:10]
                    session["history"] = history
        except Exception as e:
            error_message = str(e)

    return render_template(
        "index.html",
        symbol=symbol,
        price=price,
        eps=eps,
        pe_ratio=pe_ratio,
        peg_ratio=peg_ratio,
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
        payout_ratio=payout_ratio,
        earnings_growth=earnings_growth,
        forward_pe=forward_pe,
        price_to_sales=price_to_sales,
        ev_to_ebitda=ev_to_ebitda,
        price_to_fcf=price_to_fcf,
        current_ratio=current_ratio,
        error_message=error_message,
        alert_message=alert_message,
        history_dates=history_dates,
        history_prices=history_prices,
        ma20=ma20,
        ma50=ma50,
        rsi_values=rsi_values,
        macd_values=macd_vals,
        macd_signal=macd_signal,
        bb_upper=bb_upper,
        bb_lower=bb_lower,
        history=history,
    )


@main_bp.route("/clear_history")
def clear_history():
    if current_user.is_authenticated:
        History.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    else:
        session.pop("history", None)
    return redirect(url_for("main.index"))


@main_bp.route("/download")
def download():
    symbol = request.args.get("symbol", "").upper()
    fmt = request.args.get("format", "csv").lower()
    if not symbol:
        return "Symbol missing", 400

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
        payout_ratio,
        earnings_growth,
        forward_pe,
        price_to_sales,
        ev_to_ebitda,
        price_to_fcf,
        current_ratio,
    ) = get_stock_data(symbol)

    if current_user.is_authenticated and current_user.default_currency:
        currency = current_user.default_currency

    if price is not None and eps:
        pe_ratio_val = round(price / eps, 2)
        peg_ratio_val = None
        if earnings_growth not in (None, 0):
            try:
                growth_pct = float(earnings_growth)
                if growth_pct != 0:
                    peg_ratio_val = pe_ratio_val / (growth_pct * 100)
            except (TypeError, ValueError):
                peg_ratio_val = None
        if pe_ratio_val < 15:
            valuation = "Undervalued?"
        elif pe_ratio_val > 25:
            valuation = "Overvalued?"
        else:
            valuation = "Fairly Valued"
        pe_ratio = format_decimal(pe_ratio_val, locale=get_locale())
        peg_ratio = (
            format_decimal(round(peg_ratio_val, 2), locale=get_locale())
            if peg_ratio_val is not None
            else "N/A"
        )
    else:
        pe_ratio = valuation = peg_ratio = "N/A"

    if debt_to_equity is not None:
        debt_to_equity = format_decimal(round(debt_to_equity, 2), locale=get_locale())
    if pb_ratio is not None:
        pb_ratio = format_decimal(round(pb_ratio, 2), locale=get_locale())
    if roe is not None:
        roe = format_decimal(round(roe * 100, 2), locale=get_locale())
    if roa is not None:
        roa = format_decimal(round(roa * 100, 2), locale=get_locale())
    if profit_margin is not None:
        profit_margin = format_decimal(
            round(profit_margin * 100, 2), locale=get_locale()
        )
    if dividend_yield is not None:
        dividend_yield = format_decimal(
            round(dividend_yield * 100, 2), locale=get_locale()
        )
    if payout_ratio is not None:
        payout_ratio = format_decimal(round(payout_ratio * 100, 2), locale=get_locale())
    if earnings_growth is not None:
        earnings_growth = format_decimal(
            round(earnings_growth * 100, 2), locale=get_locale()
        )
    if forward_pe is not None:
        forward_pe = format_decimal(round(forward_pe, 2), locale=get_locale())
    if price_to_sales is not None:
        price_to_sales = format_decimal(round(price_to_sales, 2), locale=get_locale())
    if ev_to_ebitda is not None:
        ev_to_ebitda = format_decimal(round(ev_to_ebitda, 2), locale=get_locale())
    if price_to_fcf is not None:
        price_to_fcf = format_decimal(round(price_to_fcf, 2), locale=get_locale())
    if current_ratio is not None:
        current_ratio = format_decimal(round(current_ratio, 2), locale=get_locale())

    if price is not None:
        price = format_currency(price, currency, locale=get_locale())
    if eps is not None:
        eps = format_currency(eps, currency, locale=get_locale())

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Company Name",
                "Symbol",
                "Price",
                "EPS",
                "P/E Ratio",
                "PEG Ratio",
                "Valuation",
                "Market Cap",
                "Debt/Equity",
                "P/B",
                "ROE %",
                "ROA %",
                "Profit Margin %",
                "Analyst Rating",
                "Dividend Yield %",
                "Dividend Payout Ratio %",
                "Earnings Growth %",
                "Forward P/E",
                "P/S Ratio",
                "EV/EBITDA",
                "P/FCF Ratio",
                "Current Ratio",
                "Sector",
                "Industry",
                "Exchange",
                "Currency",
            ]
        )
        writer.writerow(
            [
                company_name,
                symbol,
                price,
                eps,
                pe_ratio,
                peg_ratio,
                valuation,
                market_cap,
                debt_to_equity,
                pb_ratio,
                roe,
                roa,
                profit_margin,
                analyst_rating,
                dividend_yield,
                payout_ratio,
                earnings_growth,
                forward_pe,
                price_to_sales,
                ev_to_ebitda,
                price_to_fcf,
                current_ratio,
                sector,
                industry,
                exchange,
                currency,
            ]
        )
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = (
            f"attachment; filename={symbol}_data.csv"
        )
        response.headers["Content-Type"] = "text/csv"
        return response
    elif fmt == "xlsx":
        output = generate_xlsx(
            [
                "Company Name",
                "Symbol",
                "Price",
                "EPS",
                "P/E Ratio",
                "PEG Ratio",
                "Valuation",
                "Market Cap",
                "Debt/Equity",
                "P/B",
                "ROE %",
                "ROA %",
                "Profit Margin %",
                "Analyst Rating",
                "Dividend Yield %",
                "Dividend Payout Ratio %",
                "Earnings Growth %",
                "Forward P/E",
                "P/S Ratio",
                "EV/EBITDA",
                "P/FCF Ratio",
                "Current Ratio",
                "Sector",
                "Industry",
                "Exchange",
                "Currency",
            ],
            [
                company_name,
                symbol,
                price,
                eps,
                pe_ratio,
                peg_ratio,
                valuation,
                market_cap,
                debt_to_equity,
                pb_ratio,
                roe,
                roa,
                profit_margin,
                analyst_rating,
                dividend_yield,
                payout_ratio,
                earnings_growth,
                forward_pe,
                price_to_sales,
                ev_to_ebitda,
                price_to_fcf,
                current_ratio,
                sector,
                industry,
                exchange,
                currency,
            ],
        )
        response = make_response(output)
        response.headers["Content-Disposition"] = (
            f"attachment; filename={symbol}_data.xlsx"
        )
        response.headers["Content-Type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return response
    elif fmt == "json":
        data = {
            "company_name": company_name,
            "symbol": symbol,
            "price": price,
            "eps": eps,
            "pe_ratio": pe_ratio,
            "peg_ratio": peg_ratio,
            "valuation": valuation,
            "market_cap": market_cap,
            "debt_to_equity": debt_to_equity,
            "pb_ratio": pb_ratio,
            "roe": roe,
            "roa": roa,
            "profit_margin": profit_margin,
            "analyst_rating": analyst_rating,
            "dividend_yield": dividend_yield,
            "payout_ratio": payout_ratio,
            "earnings_growth": earnings_growth,
            "forward_pe": forward_pe,
            "price_to_sales": price_to_sales,
            "ev_to_ebitda": ev_to_ebitda,
            "price_to_fcf": price_to_fcf,
            "current_ratio": current_ratio,
            "sector": sector,
            "industry": industry,
            "exchange": exchange,
            "currency": currency,
        }
        response = make_response(json.dumps(data))
        response.headers["Content-Disposition"] = (
            f"attachment; filename={symbol}_data.json"
        )
        response.headers["Content-Type"] = "application/json"
        return response
    elif fmt == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, txt=f"Stock Data for {symbol}", ln=1)
        fields = [
            ("Company Name", company_name),
            ("Price", price),
            ("EPS", eps),
            ("P/E Ratio", pe_ratio),
            ("PEG Ratio", peg_ratio),
            ("Valuation", valuation),
            ("Market Cap", market_cap),
            ("Debt/Equity", debt_to_equity),
            ("P/B", pb_ratio),
            ("ROE %", roe),
            ("ROA %", roa),
            ("Profit Margin %", profit_margin),
            ("Analyst Rating", analyst_rating),
            ("Dividend Yield %", dividend_yield),
            ("Dividend Payout Ratio %", payout_ratio),
            ("Earnings Growth %", earnings_growth),
            ("Forward P/E", forward_pe),
            ("P/S Ratio", price_to_sales),
            ("EV/EBITDA", ev_to_ebitda),
            ("P/FCF Ratio", price_to_fcf),
            ("Current Ratio", current_ratio),
            ("Sector", sector),
            ("Industry", industry),
            ("Exchange", exchange),
            ("Currency", currency),
        ]
        for label, value in fields:
            pdf.cell(0, 10, txt=f"{label}: {value}", ln=1)
        pdf_output = pdf.output(dest="S").encode("latin-1")
        response = make_response(pdf_output)
        response.headers["Content-Disposition"] = (
            f"attachment; filename={symbol}_data.pdf"
        )
        response.headers["Content-Type"] = "application/pdf"
        return response
    else:
        return "Invalid format", 400
