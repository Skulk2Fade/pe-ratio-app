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
    from stockapp.utils import moving_average, calculate_rsi

    prices = [1, 2, 3, 4, 5]
    ma = moving_average(prices, 3)
    assert ma[-1] == 4
    rsi = calculate_rsi(prices, 3)
    assert rsi[-1] == 100


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
    assert any(item["symbol"] == "API" for item in resp.get_json())

    resp = auth_client.get("/api/portfolio")
    assert resp.status_code == 200
    assert any(item["symbol"] == "API" for item in resp.get_json())

    resp = auth_client.get("/api/alerts")
    assert resp.status_code == 200
    assert any(alert["message"] == "msg" for alert in resp.get_json())


def test_stream_price(client, monkeypatch):
    monkeypatch.setattr(
        "stockapp.main.routes.get_stock_data",
        lambda s: (
            "Name",
            "",
            "",
            "",
            "",
            "",
            100,
            5,
            *([None] * 15),
        ),
    )
    resp = client.get("/stream_price?symbol=AAA")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/event-stream")
    chunk = next(resp.response).decode()
    assert "price" in chunk
