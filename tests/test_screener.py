def test_screener_route(client, monkeypatch):
    monkeypatch.setattr(
        "stockapp.utils.screen_stocks",
        lambda **k: [
            {
                "symbol": "AAA",
                "company": "Test Co",
                "sector": "Tech",
                "pe": 10,
                "peg": 1.2,
                "dividend_yield": 2.0,
            }
        ],
    )
    resp = client.get("/screener?pe_min=5")
    assert resp.status_code == 200
    assert b"AAA" in resp.data
