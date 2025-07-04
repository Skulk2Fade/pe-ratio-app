import os
import time
import pickle
import logging
import requests
import smtplib
from email.mime.text import MIMEText
from flask import current_app, has_request_context, request
from flask_login import current_user
from babel import Locale
from babel.numbers import format_currency, format_decimal
from babel.dates import format_datetime
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

try:
    import redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover - optional dependency
    redis = None

    class RedisError(Exception):
        """Fallback Redis error when redis package is unavailable."""

        pass


API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable not set")

ALERT_PE_THRESHOLD = 30

logger = logging.getLogger(__name__)

# Use a requests Session with retries for better resilience
session = requests.Session()
retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
adapter = HTTPAdapter(max_retries=retries)
session.mount("http://", adapter)
session.mount("https://", adapter)

# Cache configuration. Uses Redis when available with in-memory fallback
CACHE_TTL = int(os.environ.get("API_CACHE_TTL", 3600))
REDIS_URL = os.environ.get("REDIS_URL")
_cache = {}
_redis = None
if redis and REDIS_URL:
    try:
        _redis = redis.Redis.from_url(REDIS_URL)
        _redis.ping()
    except Exception as e:  # pragma: no cover - handle missing Redis
        logger.error("Redis error: %s; falling back to local cache", e)
        _redis = None


def _get_cached(key):
    if _redis:
        try:
            val = _redis.get(key)
            if val is not None:
                return pickle.loads(val)
        except RedisError as e:  # pragma: no cover - redis failure
            logger.error("Redis get error for %s: %s", key, e)
        except Exception:
            logger.exception("Unexpected Redis get error for %s", key)
    data = _cache.get(key)
    if not data:
        return None
    value, ts = data
    if time.time() - ts < CACHE_TTL:
        return value
    _cache.pop(key, None)
    return None


def _set_cached(key, value):
    if _redis:
        try:
            _redis.setex(key, CACHE_TTL, pickle.dumps(value))
            return
        except RedisError as e:  # pragma: no cover - redis failure
            logger.error("Redis set error for %s: %s", key, e)
        except Exception:
            logger.exception("Unexpected Redis set error for %s", key)
    _cache[key] = (value, time.time())


def _fetch_json(url, desc, symbol=None):
    """Fetch JSON data from a URL and log any errors."""
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except (
        requests.exceptions.RequestException
    ) as e:  # pragma: no cover - network failure
        status = getattr(e.response, "status_code", "unknown")
        if symbol:
            logger.error(
                "Error fetching %s for %s: %s (status %s)", desc, symbol, e, status
            )
        else:
            logger.error("Error fetching %s: %s (status %s)", desc, e, status)
        raise
    except Exception as e:  # pragma: no cover - other failure
        if symbol:
            logger.error("Error fetching %s for %s: %s", desc, symbol, e)
        else:
            logger.error("Error fetching %s: %s", desc, e)
        raise


def _cached_or_placeholder(key, size=23):
    cached = _get_cached(key)
    return cached if cached else (None,) * size


def get_locale():
    if has_request_context():
        if current_user.is_authenticated and current_user.language:
            return current_user.language
        loc = request.accept_languages.best or "en"
        try:
            return Locale.parse(loc).language
        except Exception:  # pragma: no cover - fallback
            return "en"
    return "en"


def send_email(to, subject, body):
    smtp_server = current_app.config.get("SMTP_SERVER")
    smtp_port = current_app.config.get("SMTP_PORT", 587)
    smtp_user = current_app.config.get("SMTP_USERNAME")
    smtp_pass = current_app.config.get("SMTP_PASSWORD")
    if not all([smtp_server, smtp_user, smtp_pass]):
        logger.error("Email configuration incomplete")
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
        logger.error("Email error: %s", e)


def send_sms(to, body):
    sid = current_app.config.get("TWILIO_SID")
    token = current_app.config.get("TWILIO_TOKEN")
    from_number = current_app.config.get("TWILIO_FROM")
    if not all([sid, token, from_number]):
        logger.error("SMS configuration incomplete")
        return
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        resp = session.post(
            url,
            data={"From": from_number, "To": to, "Body": body},
            auth=(sid, token),
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error("SMS error: %s", e)


def _get_asx_historical_prices(symbol, days=30):
    """Fetch historical prices from Yahoo Finance for ASX tickers."""
    range_str = f"{days}d"
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?"
        f"range={range_str}&interval=1d"
    )
    try:
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("chart", {}).get("result", [])
        if not result:
            return [], []
        chart = result[0]
        timestamps = chart.get("timestamp", [])
        indicators = chart.get("indicators", {}).get("quote", [{}])[0]
        closes = indicators.get("close", [])
        dates = [
            datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") for ts in timestamps
        ]
        return dates, closes
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, "status_code", "unknown")
        logger.error("ASX historical error for %s: %s (status %s)", symbol, e, status)
        return [], []
    except Exception as e:
        logger.error("ASX historical error for %s: %s", symbol, e)
        return [], []


def get_historical_prices(symbol, days=30):
    """Retrieve historical prices for a ticker."""
    cache_key = ("hist", symbol, days)
    cached = _get_cached(cache_key)
    if cached:
        return cached
    if symbol.lower().endswith(".ax"):
        result = _get_asx_historical_prices(symbol, days)
        if result[0]:
            _set_cached(cache_key, result)
        return result

    url = (
        f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
        f"?serietype=line&timeseries={days}&apikey={API_KEY}"
    )
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        historical = data.get("historical", [])
        dates = [item.get("date") for item in historical][::-1]
        prices = [item.get("close") for item in historical][::-1]
        result = (dates, prices)
        if dates:
            _set_cached(cache_key, result)
        return result
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, "status_code", "unknown")
        logger.error("Historical API error for %s: %s (status %s)", symbol, e, status)
        cached = _get_cached(cache_key)
        return cached if cached else ([], [])
    except Exception as e:
        logger.error("Historical API error for %s: %s", symbol, e)
        cached = _get_cached(cache_key)
        return cached if cached else ([], [])


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


def _get_asx_stock_data(symbol):
    """Retrieve stock information for ASX tickers using Yahoo Finance."""
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        resp = session.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("quoteResponse", {}).get("result", [])
        if not data:
            return (None,) * 22
        info = data[0]
        name = info.get("longName") or info.get("shortName", "")
        price = info.get("regularMarketPrice")
        eps = info.get("epsTrailingTwelveMonths")
        currency = info.get("currency", "AUD")
        market_cap = format_market_cap(info.get("marketCap"), currency)
        exchange = info.get("fullExchangeName", "ASX")
        return (
            name,
            "",
            info.get("sector", ""),
            info.get("industry", ""),
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
            None,
            None,
            None,
        )
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, "status_code", "unknown")
        logger.error("ASX API error for %s: %s (status %s)", symbol, e, status)
        return (None,) * 23
    except Exception as e:
        logger.error("ASX API error for %s: %s", symbol, e)
        return (None,) * 23


def get_stock_data(symbol):
    cache_key = ("stock", symbol)
    cached = _get_cached(cache_key)
    if cached:
        return cached

    if symbol.lower().endswith(".ax"):
        data = _get_asx_stock_data(symbol)
        if any(item is not None for item in data):
            _set_cached(cache_key, data)
        return data

    quote_url = (
        f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
    )
    profile_url = (
        f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
    )
    ratios_url = (
        f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={API_KEY}"
    )
    rating_url = (
        f"https://financialmodelingprep.com/api/v3/rating/{symbol}?apikey={API_KEY}"
    )
    growth_url = f"https://financialmodelingprep.com/api/v3/financial-growth/{symbol}?limit=1&apikey={API_KEY}"
    try:
        quote_data = _fetch_json(quote_url, "quote", symbol)
        if not isinstance(quote_data, list) or len(quote_data) == 0:
            raise ValueError("No quote data")
        quote = quote_data[0]

        profile_data = _fetch_json(profile_url, "profile", symbol)
        profile = (
            profile_data[0]
            if isinstance(profile_data, list) and len(profile_data) > 0
            else {}
        )

        ratio_data = _fetch_json(ratios_url, "ratios", symbol)
        debt_to_equity = pb_ratio = roe = roa = profit_margin = dividend_yield = (
            payout_ratio
        ) = None
        price_to_sales = ev_to_ebitda = price_to_fcf = current_ratio = None
        if isinstance(ratio_data, list) and len(ratio_data) > 0:
            r = ratio_data[0]
            debt_to_equity = r.get("debtEquityRatioTTM")
            pb_ratio = r.get("priceToBookRatioTTM")
            roe = r.get("returnOnEquityTTM")
            roa = r.get("returnOnAssetsTTM")
            profit_margin = r.get("netProfitMarginTTM")
            dividend_yield = r.get("dividendYielTTM") or r.get("dividendYieldTTM")
            payout_ratio = r.get("payoutRatioTTM") or r.get("payoutRatio")
            price_to_sales = r.get("priceToSalesRatioTTM")
            price_to_fcf = (
                r.get("priceToFreeCashFlowRatioTTM")
                or r.get("priceToFreeCashFlowsRatioTTM")
                or r.get("priceFreeCashFlowRatioTTM")
                or r.get("priceCashFlowRatioTTM")
            )
            current_ratio = r.get("currentRatioTTM")

        metrics_url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{symbol}?apikey={API_KEY}"
        metrics_data = _fetch_json(metrics_url, "key metrics", symbol)
        fcf_per_share = None
        if isinstance(metrics_data, list) and len(metrics_data) > 0:
            m = metrics_data[0]
            ev_to_ebitda = (
                m.get("evToEbitdaTTM")
                or m.get("evToEbitda")
                or m.get("enterpriseValueOverEBITDA")
            )
            fcf_per_share = m.get("freeCashFlowPerShareTTM") or m.get(
                "freeCashFlowPerShare"
            )

        rating_data = _fetch_json(rating_url, "rating", symbol)
        analyst_rating = None
        if isinstance(rating_data, list) and len(rating_data) > 0:
            analyst_rating = rating_data[0].get("ratingRecommendation") or rating_data[
                0
            ].get("rating")

        growth_data = _fetch_json(growth_url, "growth", symbol)
        earnings_growth = None
        if isinstance(growth_data, list) and len(growth_data) > 0:
            earnings_growth = growth_data[0].get("growthEPS") or growth_data[0].get(
                "epsgrowth"
            )

        name = profile.get("companyName", "")
        logo_url = profile.get("image", "")
        sector = profile.get("sector", "")
        industry = profile.get("industry", "")
        exchange = profile.get("exchangeShortName", "")
        currency = profile.get("currency", "USD")

        price = quote.get("price")
        eps = quote.get("eps")
        market_cap = format_market_cap(quote.get("marketCap"), currency)

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

        result = (
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
            payout_ratio,
            earnings_growth,
            forward_pe,
            price_to_sales,
            ev_to_ebitda,
            price_to_fcf,
            current_ratio,
        )
        if any(item is not None for item in result):
            _set_cached(cache_key, result)
        return result
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, "status_code", "unknown")
        logger.error(
            "Network error fetching stock data for %s: %s (status %s)",
            symbol,
            e,
            status,
        )
        return _cached_or_placeholder(cache_key)
    except ValueError as e:
        logger.error("Data error for %s: %s", symbol, e)
        return _cached_or_placeholder(cache_key)
    except Exception:
        logger.exception("Unexpected error fetching stock data for %s", symbol)
        return _cached_or_placeholder(cache_key)


def get_stock_news(symbol, limit=3):
    """Fetch recent news articles for a stock ticker."""
    cache_key = ("news", symbol, limit)
    cached = _get_cached(cache_key)
    if cached:
        return cached
    url = (
        f"https://financialmodelingprep.com/api/v3/stock_news?"
        f"tickers={symbol}&limit={limit}&apikey={API_KEY}"
    )
    try:
        data = _fetch_json(url, "news", symbol)
        articles = []
        if isinstance(data, list):
            for item in data:
                articles.append(
                    {
                        "headline": item.get("title"),
                        "url": item.get("url"),
                        "published": item.get("publishedDate"),
                    }
                )
        if articles:
            _set_cached(cache_key, articles)
        return articles
    except requests.exceptions.RequestException as e:
        status = getattr(e.response, "status_code", "unknown")
        logger.error(
            "Network error fetching news for %s: %s (status %s)", symbol, e, status
        )
        cached = _get_cached(cache_key)
        return cached if cached else []
    except Exception:
        logger.exception("Unexpected error fetching news for %s", symbol)
        cached = _get_cached(cache_key)
        return cached if cached else []


def moving_average(prices, period):
    """Simple moving average for a list of prices."""
    ma = []
    for i in range(len(prices)):
        if i + 1 < period:
            ma.append(None)
        else:
            window = prices[i + 1 - period : i + 1]
            ma.append(round(sum(window) / period, 2))
    return ma


def calculate_rsi(prices, period=14):
    """Calculate the Relative Strength Index (RSI)."""
    rsi = []
    for i in range(len(prices)):
        if i < period:
            rsi.append(None)
            continue
        gains = []
        losses = []
        for j in range(i - period + 1, i + 1):
            change = prices[j] - prices[j - 1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(round(100 - (100 / (1 + rs)), 2))
    return rsi


def calculate_macd(prices, slow=26, fast=12, signal=9):
    """Compute MACD and signal line using exponential moving averages."""
    ema_fast = []
    ema_slow = []
    macd = []
    signal_line = []
    for i, price in enumerate(prices):
        if i == 0:
            ema_fast.append(price)
            ema_slow.append(price)
            macd.append(0)
            signal_line.append(0)
            continue
        ema_fast.append(ema_fast[-1] + (2 / (fast + 1)) * (price - ema_fast[-1]))
        ema_slow.append(ema_slow[-1] + (2 / (slow + 1)) * (price - ema_slow[-1]))
        macd_val = ema_fast[-1] - ema_slow[-1]
        macd.append(macd_val)
        signal_line.append(
            signal_line[-1] + (2 / (signal + 1)) * (macd_val - signal_line[-1])
        )
    macd = [round(x, 2) for x in macd]
    signal_line = [round(x, 2) for x in signal_line]
    return macd, signal_line


def bollinger_bands(prices, period=20, num_std=2):
    """Return upper and lower Bollinger Bands."""
    ma = moving_average(prices, period)
    stds = []
    for i in range(len(prices)):
        if i + 1 < period:
            stds.append(None)
        else:
            window = prices[i + 1 - period : i + 1]
            mean = sum(window) / period
            variance = sum((p - mean) ** 2 for p in window) / period
            stds.append(variance**0.5)
    upper = []
    lower = []
    for m, s in zip(ma, stds):
        if m is None or s is None:
            upper.append(None)
            lower.append(None)
        else:
            upper.append(round(m + num_std * s, 2))
            lower.append(round(m - num_std * s, 2))
    return upper, lower


def generate_xlsx(headers, rows):
    """Return XLSX binary for the provided table data."""
    import zipfile
    from io import BytesIO

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/_rels/workbook.xml.rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Override PartName="/_rels/.rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        "</Types>"
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )
    rows_xml = [
        '<row r="1">'
        + "".join(f'<c t="inlineStr"><is><t>{h}</t></is></c>' for h in headers)
        + "</row>"
    ]
    r = 1
    for row in rows:
        r += 1
        cells = "".join(f'<c t="inlineStr"><is><t>{v}</t></is></c>' for v in row)
        rows_xml.append(f'<row r="{r}">{cells}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(rows_xml) + "</sheetData></worksheet>"
    )

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("xl/workbook.xml", workbook)
        zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()
