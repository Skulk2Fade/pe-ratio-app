from flask import url_for


def test_index_route(client):
    res = client.get("/")
    assert res.status_code == 200
    assert b"MarketMinder" in res.data


def test_health_route(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.data == b"OK"


def test_format_market_cap():
    from stockapp.utils import format_market_cap

    result = format_market_cap(1_500_000_000, "USD")
    assert "B" in result


def test_indicators():
    from stockapp.utils import (
        moving_average,
        calculate_rsi,
        calculate_macd,
        bollinger_bands,
        calculate_cci,
    )

    prices = [1, 2, 3, 4, 5]
    ma = moving_average(prices, 3)
    assert ma[-1] == 4
    rsi = calculate_rsi(prices, 3)
    assert rsi[-1] == 100
    macd, signal = calculate_macd(prices)
    assert len(macd) == len(prices)
    upper, lower = bollinger_bands(prices, period=3, num_std=1)
    assert upper[-1] is not None and lower[-1] is not None
    highs = [2, 3, 4, 5, 6]
    lows = [0, 1, 2, 3, 4]
    cci = calculate_cci(highs, lows, prices, period=3)
    assert cci[-1] is not None


def test_news_sentiment(monkeypatch):
    from stockapp import utils

    utils._cache.clear()

    sample = [
        {
            "title": "Stock surges on strong growth",
            "url": "u1",
            "publishedDate": "2023-01-01",
        },
        {
            "title": "Shares drop after bad results",
            "url": "u2",
            "publishedDate": "2023-01-02",
        },
    ]

    monkeypatch.setattr(utils, "_fetch_json", lambda url, desc, symbol=None: sample)

    news = utils.get_stock_news("AAA", limit=2)
    assert len(news) == 2
    sentiments = [a["sentiment"] for a in news]
    assert sentiments[0] > 0
    assert sentiments[1] < 0


def test_api_endpoints(auth_client, app):
    from stockapp.models import WatchlistItem, PortfolioItem, Alert, User
    from stockapp.extensions import db

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(WatchlistItem(symbol="API", user_id=user.id))
        db.session.add(
            PortfolioItem(symbol="API", quantity=1, price_paid=10, user_id=user.id)
        )
        db.session.add(Alert(symbol="API", message="msg", user_id=user.id))
        db.session.commit()

    resp = auth_client.get("/api/watchlist")
    assert resp.status_code == 200
    data = resp.get_json()
    assert any(item["symbol"] == "API" for item in data)
    assert all("de_threshold" in item for item in data)

    resp = auth_client.get("/api/portfolio")
    assert resp.status_code == 200
    assert any(item["symbol"] == "API" for item in resp.get_json())

    resp = auth_client.get("/api/alerts")
    assert resp.status_code == 200
    assert any(alert["message"] == "msg" for alert in resp.get_json())


def test_stream_price(client, monkeypatch):
    monkeypatch.setattr(
        "stockapp.main.routes.get_realtime_data",
        lambda symbol, provider=None: (100, 5),
    )
    resp = client.get("/stream_price?symbol=AAA")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/event-stream")
    chunk = next(resp.response).decode()
    assert "price" in chunk


def test_ws_price_route(app):
    with app.test_request_context():
        url = url_for("main.ws_price")
    assert url == "/ws/price"


def test_push_subscribe(auth_client):
    resp = auth_client.post(
        "/subscribe_push",
        json={"endpoint": "e", "keys": {"p256dh": "a", "auth": "b"}},
    )
    assert resp.status_code == 204


def test_localization_es(auth_client, app):
    from stockapp.extensions import db
    from stockapp.models import User

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        user.language = "es"
        db.session.commit()

    resp = auth_client.get("/settings")
    assert b"Configuraci\xc3\xb3n de alertas" in resp.data
