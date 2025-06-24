import requests
import smtplib
from email.mime.text import MIMEText
from flask import current_app, request, has_request_context
from babel import Locale
from babel.numbers import format_currency, format_decimal
from babel.dates import format_datetime

ALERT_PE_THRESHOLD = 30


def get_locale():
    if has_request_context():
        loc = request.accept_languages.best or "en_US"
        try:
            return str(Locale.parse(loc))
        except Exception:
            return "en_US"
    return "en_US"


def send_email(to, subject, body):
    smtp_server = current_app.config.get("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT", 587)
    smtp_user = current_app.config.get("SMTP_USERNAME")
    smtp_pass = current_app.config.get("SMTP_PASSWORD")
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
    url = (
        f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?"
        f"serietype=line&timeseries={days}&apikey={current_app.config['API_KEY']}"
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
    key = current_app.config["API_KEY"]
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={key}"
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={key}"
    ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={key}"
    rating_url = f"https://financialmodelingprep.com/api/v3/rating/{symbol}?apikey={key}"
    growth_url = (
        f"https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit=1&apikey={key}"
    )

    try:
        quote_response = requests.get(quote_url, timeout=10)
        quote_data = quote_response.json()
        if not isinstance(quote_data, list) or not quote_data:
            return (None,) * 15
        quote = quote_data[0]

        profile_response = requests.get(profile_url, timeout=10)
        profile_data = profile_response.json()
        profile = profile_data[0] if isinstance(profile_data, list) and profile_data else {}

        ratio_response = requests.get(ratios_url, timeout=10)
        ratio_data = ratio_response.json()
        debt_to_equity = pb_ratio = roe = roa = profit_margin = dividend_yield = None
        if isinstance(ratio_data, list) and ratio_data:
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
        if isinstance(rating_data, list) and rating_data:
            analyst_rating = rating_data[0].get("ratingRecommendation") or rating_data[0].get("rating")

        growth_response = requests.get(growth_url, timeout=10)
        growth_data = growth_response.json()
        earnings_growth = None
        if isinstance(growth_data, list) and growth_data:
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
        return (None,) * 15
