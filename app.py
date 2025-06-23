from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_KEY = "fM7Qz7WUnr08q65xIA720mnBnnLbUhav"

def format_market_cap(value):
    if value is None:
        return "N/A"
    if value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.2f}T"
    elif value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    return str(value)

def get_stock_data(symbol):
    quote_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
    profile_url = f"https://financialmodelingprep.com/api/v3/profile/{symbol}?apikey={API_KEY}"
    ratios_url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{symbol}?apikey={API_KEY}"

    try:
        # Get quote data
        quote_response = requests.get(quote_url, timeout=10)
        quote_data = quote_response.json()
        if not isinstance(quote_data, list) or len(quote_data) == 0:
            return None, None, None, None, None, None, None, None, None
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

        price = quote.get("price")
        eps = quote.get("eps")
        market_cap = format_market_cap(quote.get("marketCap"))

        return (
            name,
            logo_url,
            sector,
            industry,
            exchange,
            price,
            eps,
            market_cap,
            debt_to_equity,
        )
    except Exception as e:
        print(f"API error: {e}")
        return None, None, None, None, None, None, None, None, None

@app.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    price = eps = pe_ratio = valuation = company_name = logo_url = market_cap = sector = industry = exchange = debt_to_equity = error_message = None

    if request.method == "POST":
        symbol = request.form["ticker"].upper()
        try:
            (
                company_name,
                logo_url,
                sector,
                industry,
                exchange,
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
            elif price is None or eps is None:
                error_message = "Price or EPS data is missing."
            if debt_to_equity is not None:
                debt_to_equity = round(debt_to_equity, 2)
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
        debt_to_equity=debt_to_equity,
        error_message=error_message,
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)