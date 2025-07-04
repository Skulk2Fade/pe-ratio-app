from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash
import pyotp

from stockapp.models import User, WatchlistItem, Alert


def test_signup_login_logout(client, app, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "stockapp.utils.send_email", lambda *args, **kw: sent.append(args)
    )
    resp = client.post(
        "/signup",
        data={
            "username": "new",
            "email": "n@e.com",
            "password": "pass",
            "phone": "123",
            "sms_opt_in": "y",
        },
        follow_redirects=True,
    )
    assert b"Check your email" in resp.data
    with app.app_context():
        user = User.query.filter_by(username="new").first()
        token = user.verification_token
    resp = client.get(f"/verify/{token}", follow_redirects=True)
    assert b"Email verified" in resp.data
    resp = client.post(
        "/login", data={"username": "new", "password": "pass"}, follow_redirects=True
    )
    assert b"MarketMinder" in resp.data
    resp = client.get("/logout", follow_redirects=True)
    assert b"Login" in resp.data


def test_watchlist_modifications(auth_client, app, monkeypatch):
    monkeypatch.setattr("stockapp.watchlists.routes.get_stock_news", lambda *a, **k: [])
    resp = auth_client.post(
        "/watchlist", data={"symbol": "TEST", "threshold": 15}, follow_redirects=True
    )
    assert b"TEST" in resp.data
    with app.app_context():
        item = WatchlistItem.query.filter_by(symbol="TEST").first()
        item_id = item.id
    auth_client.post(
        "/watchlist", data={"item_id": item_id, "threshold": 20}, follow_redirects=True
    )
    with app.app_context():
        assert WatchlistItem.query.get(item_id).pe_threshold == 20
    auth_client.get(f"/watchlist/delete/{item_id}", follow_redirects=True)
    with app.app_context():
        assert WatchlistItem.query.get(item_id) is None


def test_portfolio_calculations(auth_client, app, monkeypatch):
    monkeypatch.setattr("stockapp.portfolio.routes.get_stock_news", lambda *a, **k: [])

    def fake_get_stock_data(symbol):
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

    monkeypatch.setattr("stockapp.portfolio.routes.get_stock_data", fake_get_stock_data)
    auth_client.post(
        "/portfolio",
        data={"symbol": "AAA", "quantity": 2, "price_paid": 90},
        follow_redirects=True,
    )
    auth_client.post(
        "/portfolio",
        data={"symbol": "BBB", "quantity": 1, "price_paid": 110},
        follow_redirects=True,
    )
    resp = auth_client.get("/portfolio", follow_redirects=True)
    assert b"High concentration in Tech" in resp.data


def test_portfolio_volatility_correlations(auth_client, app, monkeypatch):
    monkeypatch.setattr("stockapp.portfolio.routes.get_stock_news", lambda *a, **k: [])

    def fake_get_stock_data(symbol):
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

    historical = {
        "AAA": (["d1", "d2", "d3"], [100, 102, 101]),
        "BBB": (["d1", "d2", "d3"], [50, 49, 51]),
        "SPY": (["d1", "d2", "d3"], [300, 303, 306]),
    }

    monkeypatch.setattr("stockapp.portfolio.routes.get_stock_data", fake_get_stock_data)
    monkeypatch.setattr(
        "stockapp.portfolio.routes.get_historical_prices",
        lambda s, days=30: historical.get(s, historical["SPY"]),
    )
    auth_client.post(
        "/portfolio",
        data={"symbol": "AAA", "quantity": 1, "price_paid": 90},
        follow_redirects=True,
    )
    auth_client.post(
        "/portfolio",
        data={"symbol": "BBB", "quantity": 1, "price_paid": 110},
        follow_redirects=True,
    )
    resp = auth_client.get("/portfolio", follow_redirects=True)
    assert b"Asset Correlations" in resp.data
    assert b"Portfolio Volatility" in resp.data
    assert b"Portfolio Beta" in resp.data
    assert b"Sharpe Ratio" in resp.data
    assert b"Value at Risk" in resp.data


def test_check_watchlists(app, monkeypatch):
    def fake_get_stock(symbol):
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

    emails = []
    sms = []
    monkeypatch.setattr("stockapp.tasks.get_stock_data", fake_get_stock)
    monkeypatch.setattr(
        "stockapp.tasks.send_email",
        lambda to, subject, body: emails.append((to, subject, body)),
    )
    monkeypatch.setattr(
        "stockapp.tasks.send_sms", lambda to, body: sms.append((to, body))
    )
    from stockapp.extensions import db

    with app.app_context():
        u = User(
            username="alert",
            email="a@b.com",
            password_hash=generate_password_hash("x"),
            is_verified=True,
            alert_frequency=1,
            last_alert_time=datetime.utcnow() - timedelta(hours=2),
            mfa_enabled=False,
            phone_number="123",
            sms_opt_in=True,
        )
        db.session.add(u)
        db.session.commit()
        db.session.add(WatchlistItem(symbol="AAA", user_id=u.id, pe_threshold=10))
        db.session.commit()
    from stockapp import tasks

    tasks._check_watchlists()
    assert emails
    assert sms
    with app.app_context():
        alert = Alert.query.filter_by(user_id=u.id).first()
        assert alert is not None


def test_mfa_login_flow(client, app):
    from stockapp.extensions import db

    secret = pyotp.random_base32()
    with app.app_context():
        user = User(
            username="mfa",
            email="mfa@example.com",
            password_hash=generate_password_hash("pass"),
            is_verified=True,
            mfa_enabled=True,
            mfa_secret=secret,
        )
        db.session.add(user)
        db.session.commit()
    resp = client.post(
        "/login", data={"username": "mfa", "password": "pass"}, follow_redirects=True
    )
    assert b"Enter the 6-digit code" in resp.data
    totp = pyotp.TOTP(secret)
    code = totp.now()
    resp = client.post("/mfa_verify", data={"code": code}, follow_redirects=True)
    assert b"MarketMinder" in resp.data


def test_user_preferences_update(auth_client):
    resp = auth_client.post(
        "/settings",
        data={
            "frequency": 12,
            "phone": "111",
            "currency": "EUR",
            "language": "fr",
            "theme": "dark",
        },
        follow_redirects=True,
    )
    assert b"EUR" in resp.data
