import importlib
import os
import requests


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


def test_fetch_json_network_error(monkeypatch):
    import stockapp.utils as utils

    utils._cache.clear()

    # simulate network failure
    class FakeExc(requests.exceptions.RequestException):
        pass

    def raise_exc(*args, **kwargs):
        raise FakeExc("boom")

    monkeypatch.setattr(utils.session, "get", raise_exc)

    # no cached value -> empty dict
    data = utils._fetch_json("http://test", "desc")
    assert data == {}

    # cached value should be returned on failure
    utils._set_cached("http://test", {"cached": True})
    data = utils._fetch_json("http://test", "desc")
    assert data == {"cached": True}


def test_screen_stocks_rating_filter(monkeypatch):
    monkeypatch.setenv("API_KEY", "x")
    import stockapp.utils as utils

    importlib.reload(utils)

    monkeypatch.setattr(
        utils,
        "_fetch_json",
        lambda url, desc: [
            {
                "symbol": "AAA",
                "companyName": "Test Co",
                "sector": "Tech",
                "pe": 10,
                "marketCap": 1000,
                "volume": 1000,
            }
        ],
    )

    monkeypatch.setattr(
        "stockapp.utils.get_stock_data",
        lambda symbol: (
            "Test Co",
            None,
            "Tech",
            "",
            "",
            "USD",
            100,
            10,
            "10B",
            None,
            None,
            None,
            None,
            None,
            "Buy",
            0.02,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    )

    results = utils.screen_stocks(rating="Buy")
    assert len(results) == 1 and results[0]["symbol"] == "AAA"

    results = utils.screen_stocks(rating="Sell")
    assert results == []
