import os
import pytest

os.environ.setdefault('API_KEY', 'demo')

from flask import url_for
from stockapp import create_app

@pytest.fixture
def app(monkeypatch):
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    # prevent scheduler from running
    monkeypatch.setattr('stockapp.__init__.start_scheduler', lambda: None)
    app = create_app()
    app.config['TESTING'] = True
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_index_route(client):
    res = client.get('/')
    assert res.status_code == 200
    assert b'MarketMinder' in res.data

def test_format_market_cap():
    from stockapp.utils import format_market_cap
    result = format_market_cap(1_500_000_000, 'USD')
    assert 'B' in result
