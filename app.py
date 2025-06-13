from flask import Flask, render_template, request
import requests

app = Flask(__name__)

API_KEY = "fM7Qz7WUnr08q65xIA720mnBnnLbUhav"

def get_stock_data(symbol):
    url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey={API_KEY}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            quote = data[0]
            price = quote.get("price")
            eps = quote.get("eps")
            return price, eps
    except Exception as e:
        print(f"API error: {e}")
    return None, None

@app.route("/", methods=["GET", "POST"])
def index():
    symbol = ""
    price = ""
    eps = ""
    pe_ratio = None
    valuation = None
    error_message = ""

    if request.method == "POST":
        symbol = request.form.get("ticker").strip().upper()
        price, eps = get_stock_data(symbol)

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
                           pe_ratio=pe_ratio, valuation=valuation, error_message=error_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)