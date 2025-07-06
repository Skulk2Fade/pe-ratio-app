from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash
import pyotp

from stockapp.models import User, WatchlistItem, Alert, PortfolioItem


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
        "/watchlist",
        data={
            "symbol": "TEST",
            "threshold": 15,
            "de_threshold": 1,
            "rsi_threshold": 70,
            "ma_threshold": 10,
        },
        follow_redirects=True,
    )
    assert b"TEST" in resp.data
    with app.app_context():
        item = WatchlistItem.query.filter_by(symbol="TEST").first()
        item_id = item.id
    auth_client.post(
        "/watchlist",
        data={
            "item_id": item_id,
            "threshold": 20,
            "de_threshold": 0.5,
            "rsi_threshold": 60,
            "ma_threshold": 5,
        },
        follow_redirects=True,
    )
    with app.app_context():
        item = WatchlistItem.query.get(item_id)
        assert item.pe_threshold == 20
        assert item.de_threshold == 0.5
        assert item.rsi_threshold == 60
        assert item.ma_threshold == 5
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
    assert b"Monte Carlo VaR" in resp.data


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
        "stockapp.tasks.get_historical_prices",
        lambda s, days=60: (["d"] * 60, [100] * 60),
    )
    monkeypatch.setattr("stockapp.tasks.moving_average", lambda prices, p: [80])
    monkeypatch.setattr("stockapp.tasks.calculate_rsi", lambda prices, p=14: [80])
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
        db.session.add(
            WatchlistItem(
                symbol="AAA",
                user_id=u.id,
                pe_threshold=10,
                de_threshold=0.2,
                rsi_threshold=70,
                ma_threshold=10,
            )
        )
        db.session.commit()
    from stockapp import tasks

    tasks._check_watchlists()
    assert len(emails) >= 4
    assert len(sms) >= 4
    with app.app_context():
        alert = Alert.query.filter_by(user_id=u.id).first()
        assert alert is not None


def test_trend_summary_notifications(app, monkeypatch):
    monkeypatch.setattr(
        "stockapp.tasks.get_historical_prices",
        lambda s, days=7: (["d1", "d2"], [100, 110]),
    )
    emails = []
    monkeypatch.setattr(
        "stockapp.tasks.send_email",
        lambda to, subject, body: emails.append((to, subject, body)),
    )
    from stockapp.extensions import db

    with app.app_context():
        u = User(
            username="summary",
            email="s@example.com",
            password_hash=generate_password_hash("x"),
            is_verified=True,
            trend_opt_in=True,
        )
        db.session.add(u)
        db.session.commit()
        db.session.add(
            PortfolioItem(symbol="AAA", quantity=1, price_paid=10, user_id=u.id)
        )
        db.session.add(WatchlistItem(symbol="BBB", user_id=u.id))
        db.session.commit()
    from stockapp import tasks

    tasks._send_trend_summaries()
    assert emails
    assert "AAA" in emails[0][2] and "BBB" in emails[0][2]


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


def test_public_watchlist_and_follow_portfolio(app, client, auth_client):
    from stockapp.extensions import db
    from stockapp.models import User, WatchlistItem, PortfolioItem, PortfolioFollow
    from werkzeug.security import generate_password_hash

    with app.app_context():
        u = User(
            username="other",
            email="o@example.com",
            password_hash=generate_password_hash("pass"),
            is_verified=True,
        )
        db.session.add(u)
        db.session.commit()
        db.session.add(WatchlistItem(symbol="SOC", user_id=u.id, is_public=True))
        db.session.add(
            PortfolioItem(symbol="SOC", quantity=1, price_paid=1, user_id=u.id)
        )
        db.session.commit()

    resp = client.get("/watchlist/public/other")
    assert b"SOC" in resp.data

    auth_client.get("/portfolio/follow/other", follow_redirects=True)
    resp = auth_client.get("/portfolio/other", follow_redirects=True)
    assert b"SOC" in resp.data


def test_leaderboard(app, client):
    from stockapp.extensions import db
    from stockapp.models import User, PortfolioFollow
    from werkzeug.security import generate_password_hash

    with app.app_context():
        u1 = User(
            username="l1",
            email="l1@e.com",
            password_hash=generate_password_hash("x"),
            is_verified=True,
        )
        u2 = User(
            username="l2",
            email="l2@e.com",
            password_hash=generate_password_hash("x"),
            is_verified=True,
        )
        u3 = User(
            username="l3",
            email="l3@e.com",
            password_hash=generate_password_hash("x"),
            is_verified=True,
        )
        db.session.add_all([u1, u2, u3])
        db.session.commit()
        db.session.add_all(
            [
                PortfolioFollow(follower_id=u2.id, followed_id=u1.id),
                PortfolioFollow(follower_id=u3.id, followed_id=u1.id),
                PortfolioFollow(follower_id=u3.id, followed_id=u2.id),
            ]
        )
        db.session.commit()

    resp = client.get("/leaderboard")
    assert resp.status_code == 200
    data = resp.data.decode()
    assert "l1" in data and "l2" in data


def test_currency_conversion_in_index(auth_client, app, monkeypatch):
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
            *([None] * 15),
        )

    monkeypatch.setattr("stockapp.main.routes.get_stock_data", fake_get_stock)
    monkeypatch.setattr("stockapp.utils.get_exchange_rate", lambda f, t: 0.5)

    from stockapp.extensions import db
    from stockapp.models import User

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        user.default_currency = "EUR"
        db.session.commit()

    resp = auth_client.get("/?ticker=AAA")
    assert b"\xe2\x82\xac50.00" in resp.data
