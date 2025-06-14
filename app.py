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
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            quote = data[0]
            price = quote.get("price")
            eps = quote.get("eps")
            market_cap = format_market_cap(quote.get("marketCap"))
            return price, eps, market_cap
    except Exception as e:
        print(f"API error: {e}")
    return None, None, None

@app.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    price = ""
    eps = ""
    market_cap = ""
    pe_ratio = None
    valuation = None
    error_message = ""

    if request.method == "POST":
        symbol = request.form.get("ticker").strip().upper()
        price, eps, market_cap = get_stock_data(symbol)

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

    return render_template("index.html", symbol=symbol, price=price, eps=eps,
                           pe_ratio=pe_ratio, valuation=valuation,
                           market_cap=market_cap, error_message=error_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)