from flask import Flask, render_template, request, make_response, session, redirect, url_for
import requests
from babel.numbers import format_currency
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

app = Flask(__name__)
app.config["SECRET_KEY"] = "change_this_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

API_KEY = "fM7Qz7WUnr08q65xIA720mnBnnLbUhav"

# Threshold for triggering a P/E ratio alert
ALERT_PE_THRESHOLD = 30


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(150), nullable=False)


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
    formatted = format_currency(value, currency, locale="en_US")
    return f"{formatted}{suffix}"

def get_stock_data(symbol):
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
    ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={API_KEY}"

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
        debt_to_equity = None
        if isinstance(ratio_data, list) and len(ratio_data) > 0:
            debt_to_equity = ratio_data[0].get("debtEquityRatioTTM")

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
        )
    except Exception as e:
        print(f"API error: {e}")
        return None, None, None, None, None, None, None, None, None, None

@app.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    price = eps = pe_ratio = valuation = company_name = logo_url = market_cap = sector = industry = exchange = currency = debt_to_equity = error_message = alert_message = None
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
            ) = get_stock_data(symbol)

            history_dates, history_prices = get_historical_prices(symbol)

            if price is not None and eps:
                pe_ratio = round(price / eps, 2)
                if pe_ratio < 15:
                    valuation = "Undervalued?"
                elif pe_ratio > 25:
                    valuation = "Overvalued?"
                else:
                    valuation = "Fairly Valued"
                if pe_ratio > ALERT_PE_THRESHOLD:
                    alert_message = (
                        f"P/E ratio {pe_ratio} exceeds threshold of {ALERT_PE_THRESHOLD}"
                    )
                    if current_user.is_authenticated:
                        db.session.add(
                            Alert(symbol=symbol, message=alert_message, user_id=current_user.id)
                        )
                        db.session.commit()
            elif price is None or eps is None:
                error_message = "Price or EPS data is missing."
            if debt_to_equity is not None:
                debt_to_equity = round(debt_to_equity, 2)
            if price is not None:
                price = format_currency(price, currency, locale="en_US")
            if eps is not None:
                eps = format_currency(eps, currency, locale="en_US")
        
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
    ) = get_stock_data(symbol)

    if price is not None and eps:
        pe_ratio = round(price / eps, 2)
        if pe_ratio < 15:
            valuation = "Undervalued?"
        elif pe_ratio > 25:
            valuation = "Overvalued?"
        else:
            valuation = "Fairly Valued"
    else:
        pe_ratio = valuation = "N/A"

    if debt_to_equity is not None:
        debt_to_equity = round(debt_to_equity, 2)

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
        password = request.form["password"]
        if User.query.filter_by(username=username).first():
            error = "Username already exists"
        else:
            user = User(username=username, password_hash=generate_password_hash(password))
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
        writer.writerow([e.symbol, e.timestamp.isoformat()])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=history.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
