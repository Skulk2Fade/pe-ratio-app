import os
import requests
import smtplib
from email.mime.text import MIMEText
from flask import current_app, has_request_context, request
from babel import Locale
from babel.numbers import format_currency, format_decimal
from babel.dates import format_datetime
from datetime import datetime

API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise RuntimeError('API_KEY environment variable not set')

ALERT_PE_THRESHOLD = 30

def get_locale():
    if has_request_context():
        loc = request.accept_languages.best or 'en_US'
        try:
            return str(Locale.parse(loc))
        except Exception:
            return 'en_US'
    return 'en_US'

def send_email(to, subject, body):
    smtp_server = current_app.config.get('SMTP_SERVER')
    smtp_port = current_app.config.get('SMTP_PORT', 587)
    smtp_user = current_app.config.get('SMTP_USERNAME')
    smtp_pass = current_app.config.get('SMTP_PASSWORD')
    if not all([smtp_server, smtp_user, smtp_pass]):
        print('Email configuration incomplete')
        return
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = to
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    except Exception as e:
        print(f'Email error: {e}')

def _get_asx_historical_prices(symbol, days=30):
    """Fetch historical prices from Yahoo Finance for ASX tickers."""
    range_str = f"{days}d"
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?"
        f"range={range_str}&interval=1d"
    )
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return [], []
        chart = result[0]
        timestamps = chart.get("timestamp", [])
        indicators = chart.get("indicators", {}).get("quote", [{}])[0]
        closes = indicators.get("close", [])
        dates = [datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") for ts in timestamps]
        return dates, closes
    except Exception as e:
        print(f"ASX historical error: {e}")
        return [], []


def get_historical_prices(symbol, days=30):
    """Retrieve historical prices for a ticker."""
    if symbol.lower().endswith(".ax"):
        return _get_asx_historical_prices(symbol, days)

    url = (
        f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
        f"?serietype=line&timeseries={days}&apikey={API_KEY}"
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
        return 'N/A'
    suffix = ''
    if value >= 1_000_000_000_000:
        value /= 1_000_000_000_000
        suffix = 'T'
    elif value >= 1_000_000_000:
        value /= 1_000_000_000
        suffix = 'B'
    elif value >= 1_000_000:
        value /= 1_000_000
        suffix = 'M'
    formatted = format_currency(value, currency, locale=get_locale())
    return f'{formatted}{suffix}'

def _get_asx_stock_data(symbol):
    """Retrieve stock information for ASX tickers using Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        resp = requests.get(url, timeout=10)
        data = resp.json().get("quoteResponse", {}).get("result", [])
        if not data:
            return (None,) * 21
        info = data[0]
        name = info.get("longName") or info.get("shortName", "")
        price = info.get("regularMarketPrice")
        eps = info.get("epsTrailingTwelveMonths")
        currency = info.get("currency", "AUD")
        market_cap = format_market_cap(info.get("marketCap"), currency)
        exchange = info.get("fullExchangeName", "ASX")
        return (
            name,
            '',
            info.get('sector', ''),
            info.get('industry', ''),
            exchange,
            currency,
            price,
            eps,
            market_cap,
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
    except Exception as e:
        print(f"ASX API error: {e}")
        return (None,) * 21


def get_stock_data(symbol):
    if symbol.lower().endswith('.ax'):
        return _get_asx_stock_data(symbol)

    quote_url = f'https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}'
    profile_url = f'https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}'
    ratios_url = f'https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={API_KEY}'
    rating_url = f'https://financialmodelingprep.com/api/v3/rating/{symbol}?apikey={API_KEY}'
    growth_url = f'https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit=1&apikey={API_KEY}'
    try:
        quote_response = requests.get(quote_url, timeout=10)
        quote_data = quote_response.json()
        if not isinstance(quote_data, list) or len(quote_data) == 0:
            return (None,) * 21
        quote = quote_data[0]

        profile_response = requests.get(profile_url, timeout=10)
        profile_data = profile_response.json()
        profile = profile_data[0] if isinstance(profile_data, list) and len(profile_data) > 0 else {}

        ratio_response = requests.get(ratios_url, timeout=10)
        ratio_data = ratio_response.json()
        debt_to_equity = pb_ratio = roe = roa = profit_margin = dividend_yield = None
        price_to_sales = ev_to_ebitda = price_to_fcf = None
        if isinstance(ratio_data, list) and len(ratio_data) > 0:
            r = ratio_data[0]
            debt_to_equity = r.get('debtEquityRatioTTM')
            pb_ratio = r.get('priceToBookRatioTTM')
            roe = r.get('returnOnEquityTTM')
            roa = r.get('returnOnAssetsTTM')
            profit_margin = r.get('netProfitMarginTTM')
            dividend_yield = r.get('dividendYielTTM') or r.get('dividendYieldTTM')
            price_to_sales = r.get('priceToSalesRatioTTM')
            price_to_fcf = (
                r.get('priceToFreeCashFlowRatioTTM')
                or r.get('priceToFreeCashFlowsRatioTTM')
                or r.get('priceFreeCashFlowRatioTTM')
                or r.get('priceCashFlowRatioTTM')
            )

        metrics_url = f'https://financialmodelingprep.com/api/v3/key-metrics-ttm/{symbol}?apikey={API_KEY}'
        metrics_response = requests.get(metrics_url, timeout=10)
        metrics_data = metrics_response.json()
        fcf_per_share = None
        if isinstance(metrics_data, list) and len(metrics_data) > 0:
            m = metrics_data[0]
            ev_to_ebitda = (
                m.get('evToEbitdaTTM')
                or m.get('evToEbitda')
                or m.get('enterpriseValueOverEBITDA')
            )
            fcf_per_share = m.get('freeCashFlowPerShareTTM') or m.get('freeCashFlowPerShare')

        rating_response = requests.get(rating_url, timeout=10)
        rating_data = rating_response.json()
        analyst_rating = None
        if isinstance(rating_data, list) and len(rating_data) > 0:
            analyst_rating = rating_data[0].get('ratingRecommendation') or rating_data[0].get('rating')

        growth_response = requests.get(growth_url, timeout=10)
        growth_data = growth_response.json()
        earnings_growth = None
        if isinstance(growth_data, list) and len(growth_data) > 0:
            earnings_growth = growth_data[0].get('growthEPS') or growth_data[0].get('epsgrowth')

        name = profile.get('companyName', '')
        logo_url = profile.get('image', '')
        sector = profile.get('sector', '')
        industry = profile.get('industry', '')
        exchange = profile.get('exchangeShortName', '')
        currency = profile.get('currency', 'USD')

        price = quote.get('price')
        eps = quote.get('eps')
        market_cap = format_market_cap(quote.get('marketCap'), currency)

        forward_pe = None
        if price is not None and eps is not None:
            try:
                growth = float(earnings_growth) if earnings_growth is not None else None
            except (TypeError, ValueError):
                growth = None
            if growth is not None:
                try:
                    forward_eps = eps * (1 + growth)
                    forward_pe = round(price / forward_eps, 2) if forward_eps else None
                except Exception:
                    forward_pe = None

        if price_to_fcf is None and price is not None and fcf_per_share:
            try:
                price_to_fcf = round(price / fcf_per_share, 2)
            except Exception:
                price_to_fcf = None

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
            forward_pe,
            price_to_sales,
            ev_to_ebitda,
            price_to_fcf,
        )
    except Exception as e:
        print(f'API error: {e}')
        return (None,) * 21
