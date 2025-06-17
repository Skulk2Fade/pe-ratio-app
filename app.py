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

    try:
        # Get quote data
        quote_response = requests.get(quote_url, timeout=10)
        quote_data = quote_response.json()
        if not isinstance(quote_data, list) or len(quote_data) == 0:
            return None, None, None, None, None, None
        quote = quote_data[0]

        # Get profile data (logo + company name)
        profile_response = requests.get(profile_url, timeout=10)
        profile_data = profile_response.json()
        profile = profile_data[0] if isinstance(profile_data, list) and len(profile_data) > 0 else {}

        name = profile.get("companyName", "")
        logo_url = profile.get("image", "")

        price = quote.get("price")
        eps = quote.get("eps")
        market_cap = format_market_cap(quote.get("marketCap"))

        return name, logo_url, price, eps, market_cap
    except Exception as e:
        print(f"API error: {e}")
        return None, None, None, None, None, None

@app.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    company_name = ""
    logo_url = ""
    price = ""
    eps = ""
    market_cap = ""
    pe_ratio = None
    valuation = None
    error_message = ""

    if request.method == "POST":
        symbol = request.form.get("ticker").strip().upper()
        company_name, logo_url, price, eps, market_cap = get_stock_data(symbol)

        if price is None or eps is None:
            error_message = "Ticker not found or unsupported by data provider."
        else:
            try:
                pe_ratio = round(price / eps, 2)
                if pe_ratio < 10:
                    valuation = "Undervalued?"
                elif pe_ratio <= 25:
                    valuation = "Fairly Valued"
                else:
                    valuation = "Overvalued?"
            except ZeroDivisionError:
                pe_ratio = "EPS is zero"

    return render_template("index.html", symbol=symbol, company_name=company_name,
                           logo_url=logo_url, price=price, eps=eps, pe_ratio=pe_ratio,
                           valuation=valuation, market_cap=market_cap,
                           error_message=error_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)