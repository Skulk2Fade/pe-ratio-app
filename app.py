from flask import Flask, render_template, request
import yfinance as yf
import requests

app = Flask(__name__)

# Workaround: custom request session with headers
def get_stock_info(symbol):
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.headers.update(headers)
    ticker = yf.Ticker(symbol, session=session)
    return ticker.info

@app.route("/", methods=["GET", "POST"])
def index():
    pe_ratio = None
    valuation = None
    price = ""
    eps = ""
    symbol = ""

    if request.method == "POST":
        symbol = request.form.get("ticker").strip().upper()
        try:
            info = get_stock_info(symbol)
            price = info.get("currentPrice")
            eps = info.get("trailingEps")
            if price and eps:
                pe_ratio = round(price / eps, 2)
                if pe_ratio < 10:
                    valuation = "Undervalued?"
                elif pe_ratio <= 25:
                    valuation = "Fairly Valued"
                else:
                    valuation = "Overvalued?"
        except Exception:
            pe_ratio = "Error"

    return render_template("index.html", symbol=symbol, price=price, eps=eps, pe_ratio=pe_ratio, valuation=valuation)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)