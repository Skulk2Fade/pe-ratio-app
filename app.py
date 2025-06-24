from flask import (
    Flask,
    render_template,
    request,
    make_response,
    session,
    redirect,
    url_for,
    has_request_context,
    send_from_directory,
)
import os
import requests
from babel import Locale
from babel.numbers import format_currency, format_decimal
from babel.dates import format_datetime
import csv
import io
from fpdf import FPDF
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.config["SECRET_KEY"] = "change_this_secret"

# Use DATABASE_URL if provided (e.g. when deployed on Render), otherwise
# default to a local SQLite database.
db_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SMTP_SERVER"] = "smtp.example.com"
app.config["SMTP_PORT"] = 587
app.config["SMTP_USERNAME"] = "user@example.com"
app.config["SMTP_PASSWORD"] = "password"

db = SQLAlchemy(app)


@app.route("/service-worker.js")
def service_worker():
    """Serve the service worker file with correct scope."""
    return app.send_static_file("service-worker.js")

login_manager = LoginManager(app)
login_manager.login_view = "login"

API_KEY = "fM7Qz7WUnr08q65xIA720mnBnnLbUhav"

# Threshold for triggering a P/E ratio alert
ALERT_PE_THRESHOLD = 30


def get_locale():
    """Determine best match locale from the request."""
    if has_request_context():
        loc = request.accept_languages.best or "en_US"
        try:
            return str(Locale.parse(loc))
        except Exception:
            return "en_US"
    return "en_US"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=True)


class WatchlistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10))
    message = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def send_email(to, subject, body):
    smtp_server = app.config.get("SMTP_SERVER")
    smtp_port = app.config.get("SMTP_PORT", 587)
    smtp_user = app.config.get("SMTP_USERNAME")
    smtp_pass = app.config.get("SMTP_PASSWORD")
    if not all([smtp_server, smtp_user, smtp_pass]):
        print("Email configuration incomplete")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        print(f"Email error: {e}")


def get_historical_prices(symbol, days=30):
    """Fetch historical closing prices for the given symbol."""
    url = (
        f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?"
        f"serietype=line&timeseries={days}&apikey={API_KEY}"
    )
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        historical = data.get("historical", [])
        dates = [item.get("date") for item in historical][::-1]
        prices = [item.get("close") for item in historical][::-1]
        return dates, prices
    except Exception as e:
        print(f"Historical API error: {e}")
        return [], []

def format_market_cap(value, currency):
    if value is None:
        return "N/A"
    suffix = ""
    if value >= 1_000_000_000_000:
        value /= 1_000_000_000_000
        suffix = "T"
    elif value >= 1_000_000_000:
        value /= 1_000_000_000
        suffix = "B"
    elif value >= 1_000_000:
        value /= 1_000_000
        suffix = "M"
    formatted = format_currency(value, currency, locale=get_locale())
    return f"{formatted}{suffix}"

def get_stock_data(symbol):
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
    ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={API_KEY}"
    rating_url = f"https://financialmodelingprep.com/api/v3/rating/{symbol}?apikey={API_KEY}"
    growth_url = f"https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit=1&apikey={API_KEY}"

    try:
        # Get quote data
        quote_response = requests.get(quote_url, timeout=10)
        quote_data = quote_response.json()
        if not isinstance(quote_data, list) or len(quote_data) == 0:
            return None, None, None, None, None, None, None, None, None, None
        quote = quote_data[0]

        # Get profile data
        profile_response = requests.get(profile_url, timeout=10)
        profile_data = profile_response.json()
        profile = profile_data[0] if isinstance(profile_data, list) and len(profile_data) > 0 else {}

        ratio_response = requests.get(ratios_url, timeout=10)
        ratio_data = ratio_response.json()
        debt_to_equity = pb_ratio = roe = roa = profit_margin = dividend_yield = None
        if isinstance(ratio_data, list) and len(ratio_data) > 0:
            r = ratio_data[0]
            debt_to_equity = r.get("debtEquityRatioTTM")
            pb_ratio = r.get("priceToBookRatioTTM")
            roe = r.get("returnOnEquityTTM")
            roa = r.get("returnOnAssetsTTM")
            profit_margin = r.get("netProfitMarginTTM")
            dividend_yield = r.get("dividendYielTTM") or r.get("dividendYieldTTM")

        rating_response = requests.get(rating_url, timeout=10)
        rating_data = rating_response.json()
        analyst_rating = None
        if isinstance(rating_data, list) and len(rating_data) > 0:
            analyst_rating = rating_data[0].get("ratingRecommendation") or rating_data[0].get("rating")

        growth_response = requests.get(growth_url, timeout=10)
        growth_data = growth_response.json()
        earnings_growth = None
        if isinstance(growth_data, list) and len(growth_data) > 0:
            earnings_growth = growth_data[0].get("growthEPS") or growth_data[0].get("epsgrowth")

        name = profile.get("companyName", "")
        logo_url = profile.get("image", "")
        sector = profile.get("sector", "")
        industry = profile.get("industry", "")
        exchange = profile.get("exchangeShortName", "")
        currency = profile.get("currency", "USD")

        price = quote.get("price")
        eps = quote.get("eps")
        market_cap = format_market_cap(quote.get("marketCap"), currency)

        return (
            name,
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
        )
    except Exception as e:
        print(f"API error: {e}")
        return (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )


def check_watchlists():
    with app.app_context():
        items = WatchlistItem.query.all()
        for item in items:
            user = User.query.get(item.user_id)
            if not user or not getattr(user, "email", None):
                continue
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
                if pe_ratio > ALERT_PE_THRESHOLD:
                    msg = (
                        f"{item.symbol} P/E ratio {pe_ratio} exceeds threshold {ALERT_PE_THRESHOLD}"
                    )
                    send_email(user.email, "P/E Ratio Alert", msg)
                    db.session.add(
                        Alert(symbol=item.symbol, message=msg, user_id=user.id)
                    )
                    db.session.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    price = eps = pe_ratio = valuation = company_name = logo_url = market_cap = sector = industry = exchange = currency = debt_to_equity = None
    pb_ratio = roe = roa = profit_margin = analyst_rating = dividend_yield = earnings_growth = None
    error_message = alert_message = None
    history_dates = history_prices = []

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
        symbol = request.form["ticker"].upper()
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
            ) = get_stock_data(symbol)

            history_dates, history_prices = get_historical_prices(symbol, days=90)

            if price is not None and eps:
                pe_ratio_val = round(price / eps, 2)
                pe_ratio = format_decimal(pe_ratio_val, locale=get_locale())
                if pe_ratio_val < 15:
                    valuation = "Undervalued?"
                elif pe_ratio_val > 25:
                    valuation = "Overvalued?"
                else:
                    valuation = "Fairly Valued"
                if pe_ratio_val > ALERT_PE_THRESHOLD:
                    alert_message = (
                        f"P/E ratio {pe_ratio_val} exceeds threshold of {ALERT_PE_THRESHOLD}"
                    )
                    if current_user.is_authenticated:
                        db.session.add(
                            Alert(symbol=symbol, message=alert_message, user_id=current_user.id)
                        )
                        db.session.commit()
            elif price is None or eps is None:
                error_message = "Price or EPS data is missing."
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
            if price is not None:
                price = format_currency(price, currency, locale=get_locale())
            if eps is not None:
                eps = format_currency(eps, currency, locale=get_locale())
        
            # update history
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
                    session["history"] = history

        except Exception as e:
            error_message = str(e)

    return render_template(
        "index.html",
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
        error_message=error_message,
        alert_message=alert_message,
        history_dates=history_dates,
        history_prices=history_prices,
        history=history,
    )


@app.route("/clear_history")
def clear_history():
    if current_user.is_authenticated:
        History.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
    else:
        session.pop("history", None)
    return redirect(url_for("index"))


@app.route("/download")
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
        earnings_growth,
    ) = get_stock_data(symbol)

    if price is not None and eps:
        pe_ratio_val = round(price / eps, 2)
        if pe_ratio_val < 15:
            valuation = "Undervalued?"
        elif pe_ratio_val > 25:
            valuation = "Overvalued?"
        else:
            valuation = "Fairly Valued"
        pe_ratio = format_decimal(pe_ratio_val, locale=get_locale())
    else:
        pe_ratio = valuation = "N/A"

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
                "Valuation",
                "Market Cap",
                "Debt/Equity",
                "P/B",
                "ROE %",
                "ROA %",
                "Profit Margin %",
                "Analyst Rating",
                "Dividend Yield %",
                "Earnings Growth %",
                "Sector",
                "Industry",
                "Exchange",
                "Currency",
            ]
        )
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
            sector,
            industry,
            exchange,
            currency,
        ])
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = f"attachment; filename={symbol}_data.csv"
        response.headers["Content-Type"] = "text/csv"
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
            ("Valuation", valuation),
            ("Market Cap", market_cap),
            ("Debt/Equity", debt_to_equity),
            ("P/B", pb_ratio),
            ("ROE %", roe),
            ("ROA %", roa),
            ("Profit Margin %", profit_margin),
            ("Analyst Rating", analyst_rating),
            ("Dividend Yield %", dividend_yield),
            ("Earnings Growth %", earnings_growth),
            ("Sector", sector),
            ("Industry", industry),
            ("Exchange", exchange),
            ("Currency", currency),
        ]
        for label, value in fields:
            pdf.cell(0, 10, txt=f"{label}: {value}", ln=1)
        pdf_output = pdf.output(dest="S").encode("latin-1")
        response = make_response(pdf_output)
        response.headers["Content-Disposition"] = f"attachment; filename={symbol}_data.pdf"
        response.headers["Content-Type"] = "application/pdf"
        return response
    else:
        return "Invalid format", 400


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        email = request.form.get("email")
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            error = "Username already exists"
        else:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
                email=email,
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))
    return render_template("signup.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials"
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


@app.route("/watchlist", methods=["GET", "POST"])
@login_required
def watchlist():
    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        if not WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first():
            db.session.add(WatchlistItem(symbol=symbol, user_id=current_user.id))
            db.session.commit()
    items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    return render_template("watchlist.html", items=items)


@app.route("/watchlist/delete/<int:item_id>")
@login_required
def delete_watchlist_item(item_id):
    item = WatchlistItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("watchlist"))


@app.route("/add_watchlist/<symbol>")
@login_required
def add_watchlist(symbol):
    symbol = symbol.upper()
    if not WatchlistItem.query.filter_by(user_id=current_user.id, symbol=symbol).first():
        db.session.add(WatchlistItem(symbol=symbol, user_id=current_user.id))
        db.session.commit()
    return redirect(url_for("index", ticker=symbol))


@app.route("/export_history")
@login_required
def export_history():
    entries = (
        History.query.filter_by(user_id=current_user.id)
        .order_by(History.timestamp.desc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Symbol", "Timestamp"])
    for e in entries:
        timestamp = format_datetime(e.timestamp, locale=get_locale())
        writer.writerow([e.symbol, timestamp])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=history.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_watchlists, "interval", hours=1)
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    app.run(host="0.0.0.0", port=5000, debug=True)
