import importlib
import os


def test_no_api_key_returns_placeholders(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    import stockapp.utils as utils

    importlib.reload(utils)
    assert utils.API_KEY_MISSING

    dates, prices = utils.get_historical_prices("AAPL", 1)
    assert dates == [] and prices == []

    data = utils.get_stock_data("AAPL")
    assert len(data) == 23 and all(item is None for item in data)

    assert utils.get_stock_news("AAPL") == []
    assert utils.screen_stocks() == []
