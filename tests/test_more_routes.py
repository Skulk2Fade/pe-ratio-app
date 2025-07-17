import pytest


def _fake_get_stock_data(_symbol):
    return (
        "Test Corp",
        "",
        "Tech",
        "Software",
        "NASDAQ",
        "USD",
        100,
        5,
        "1B",
        0.5,
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


def test_toggle_public_watchlist(auth_client, app, monkeypatch):
    monkeypatch.setattr("stockapp.watchlists.routes.get_stock_news", lambda *a, **k: [])
    auth_client.post(
        "/watchlist",
        data={"symbol": "TGL", "threshold": 10},
        follow_redirects=True,
    )
    from stockapp.extensions import db
    from stockapp.models import WatchlistItem

    with app.app_context():
        item = WatchlistItem.query.filter_by(symbol="TGL").first()
        assert item is not None
        item_id = item.id
        assert item.is_public is False

    auth_client.get(f"/watchlist/toggle_public/{item_id}", follow_redirects=True)
    with app.app_context():
        item = WatchlistItem.query.get(item_id)
        assert item.is_public is True

    auth_client.get(f"/watchlist/toggle_public/{item_id}", follow_redirects=True)
    with app.app_context():
        item = WatchlistItem.query.get(item_id)
        assert item.is_public is False


def test_portfolio_update_and_delete(auth_client, app, monkeypatch):
    monkeypatch.setattr("stockapp.portfolio.routes.get_stock_news", lambda *a, **k: [])
    monkeypatch.setattr(
        "stockapp.portfolio.routes.get_stock_data", _fake_get_stock_data
    )

    auth_client.post(
        "/portfolio",
        data={"symbol": "UPD", "quantity": 1, "price_paid": 100},
        follow_redirects=True,
    )

    from stockapp.extensions import db
    from stockapp.models import PortfolioItem

    with app.app_context():
        item = PortfolioItem.query.filter_by(symbol="UPD").first()
        item_id = item.id

    auth_client.post(
        "/portfolio",
        data={"item_id": item_id, "quantity": 2, "price_paid": 105},
        follow_redirects=True,
    )
    with app.app_context():
        item = PortfolioItem.query.get(item_id)
        assert item.quantity == 2
        assert item.price_paid == 105

    auth_client.get(f"/portfolio/delete/{item_id}", follow_redirects=True)
    with app.app_context():
        assert PortfolioItem.query.get(item_id) is None


def test_custom_rules_page(auth_client, app):
    resp = auth_client.get("/custom_rules")
    assert resp.status_code == 200
    resp = auth_client.post(
        "/custom_rules",
        data={"description": "rule", "rule": "price('AAA') > 1"},
        follow_redirects=True,
    )
    assert b"rule" in resp.data
