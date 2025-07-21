def test_download_csv(client, monkeypatch):
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
            1.1,
            0.1,
            0.05,
            0.2,
            "Buy",
            0.03,
            0.2,
            0.15,
            20,
            5,
            10,
            15,
            1.5,
        )

    monkeypatch.setattr("stockapp.main.routes.get_stock_data", fake_get_stock)
    resp = client.get("/download?symbol=AAA&format=csv")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/csv"
    assert b"Company Name" in resp.data


def test_download_pdf(client, monkeypatch):
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
            1.1,
            0.1,
            0.05,
            0.2,
            "Buy",
            0.03,
            0.2,
            0.15,
            20,
            5,
            10,
            15,
            1.5,
        )

    monkeypatch.setattr("stockapp.main.routes.get_stock_data", fake_get_stock)
    resp = client.get("/download?symbol=AAA&format=pdf")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"


def test_download_xlsx(client, monkeypatch):
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
            1.1,
            0.1,
            0.05,
            0.2,
            "Buy",
            0.03,
            0.2,
            0.15,
            20,
            5,
            10,
            15,
            1.5,
        )

    monkeypatch.setattr("stockapp.main.routes.get_stock_data", fake_get_stock)
    resp = client.get("/download?symbol=AAA&format=xlsx")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )


def test_download_json(client, monkeypatch):
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
            1.1,
            0.1,
            0.05,
            0.2,
            "Buy",
            0.03,
            0.2,
            0.15,
            20,
            5,
            10,
            15,
            1.5,
        )

    monkeypatch.setattr("stockapp.main.routes.get_stock_data", fake_get_stock)
    resp = client.get("/download?symbol=AAA&format=json")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/json"


def test_loan_calculator(client):
    data = {"loan_amount": 1000, "loan_rate": 5, "loan_years": 1}
    resp = client.post("/calc/loan", data=data)
    assert b"Monthly Payment" in resp.data
    assert b"Total Interest" in resp.data


def test_export_portfolio_csv(auth_client, app):
    from stockapp.models import User, PortfolioItem
    from stockapp.extensions import db

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(
            PortfolioItem(symbol="AAA", quantity=1, price_paid=10, user_id=user.id)
        )
        db.session.commit()
    resp = auth_client.get("/export_portfolio")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/csv"
    assert b"Symbol,Quantity,Price Paid" in resp.data


def test_export_portfolio_xlsx(auth_client, app):
    from stockapp.models import User, PortfolioItem
    from stockapp.extensions import db

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(
            PortfolioItem(symbol="BBB", quantity=2, price_paid=20, user_id=user.id)
        )
        db.session.commit()
    resp = auth_client.get("/export_portfolio?format=xlsx")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )


def test_export_portfolio_json(auth_client, app):
    from stockapp.models import User, PortfolioItem
    from stockapp.extensions import db

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(
            PortfolioItem(symbol="CCC", quantity=3, price_paid=30, user_id=user.id)
        )
        db.session.commit()
    resp = auth_client.get("/export_portfolio?format=json")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/json"


def test_export_portfolio_pdf(auth_client, app):
    from stockapp.models import User, PortfolioItem
    from stockapp.extensions import db

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(
            PortfolioItem(symbol="DDD", quantity=4, price_paid=40, user_id=user.id)
        )
        db.session.commit()
    resp = auth_client.get("/export_portfolio?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"


def test_export_history_pdf(auth_client, app):
    from stockapp.models import User, History
    from stockapp.extensions import db
    from datetime import datetime

    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(
            History(symbol="EEE", user_id=user.id, timestamp=datetime.utcnow())
        )
        db.session.commit()
    resp = auth_client.get("/export_history?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "application/pdf"


def test_roi_calculator(client):
    data = {"initial": 100, "final": 120}
    resp = client.post("/calc/roi", data=data)
    assert resp.status_code == 200
    assert b"ROI:" in resp.data


def test_dcf_calculator(client):
    data = {
        "cash_flow": 100,
        "discount_rate": 10,
        "years": 2,
        "terminal_value": 50,
    }
    resp = client.post("/calc/dcf", data=data)
    assert resp.status_code == 200
    assert b"Present Value" in resp.data


def test_tax_calculator(client):
    data = {
        "purchase_price": 10,
        "sale_price": 15,
        "quantity": 2,
        "tax_rate": 20,
    }
    resp = client.post("/calc/tax", data=data)
    assert resp.status_code == 200
    assert b"Tax Due" in resp.data


def test_wacc_calculator(client):
    data = {
        "equity": 1000,
        "debt": 500,
        "cost_equity": 10,
        "cost_debt": 5,
        "tax_rate": 20,
    }
    resp = client.post("/calc/wacc", data=data)
    assert resp.status_code == 200
    assert b"WACC:" in resp.data
