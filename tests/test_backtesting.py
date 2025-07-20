import pytest


def test_backtest_rule_api(auth_client, monkeypatch):
    # Provide deterministic historical prices
    def fake_hist(symbol, days=10):
        dates = [f"d{i}" for i in range(days)]
        prices = [100 + i * 10 for i in range(days)]
        return dates, prices

    monkeypatch.setattr("stockapp.backtesting.get_historical_prices", fake_hist)

    resp = auth_client.get("/api/backtest_rule?rule=change('AAA',3)%20>%205&days=5")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["results"]) == 5
    assert all(r["result"] for r in data["results"])
