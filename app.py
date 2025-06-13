from flask import Flask, render_template, request
import yfinance as yf
import requests

app = Flask(__name__)

# Workaround: custom session with headers
def get_stock_info(symbol):
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    session.headers.update(headers)
    ticker = yf.Ticker(symbol, session=session)

    # Get latest close price
    hist = ticker.history(period="1d")
    price = hist["Close"].iloc[-1] if not hist.empty else None

    # Get earnings and shares to calculate EPS
    eps = None
    try:
        earnings = ticker.earnings
        shares = ticker.get_shares_full(start="2020-01-01").iloc[-1]  # fallback for shares
        if not earnings.empty and shares:
            latest_year = earnings.index[-1]
            net_income = earnings.loc[latest_year]["Earnings"]
            eps = net_income / shares
    except Exception:
        eps = None

    return {"price": price, "eps": eps}

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
            data = get_stock_info(symbol)
            price = data.get("price")
            eps = data.get("eps")
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