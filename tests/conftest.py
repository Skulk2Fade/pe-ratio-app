import os
import pytest
from stockapp import create_app

@pytest.fixture
def app(monkeypatch):
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ.setdefault('API_KEY', 'demo')
    os.environ['DEFAULT_USERNAME'] = 'tester'
    os.environ['DEFAULT_PASSWORD'] = 'password'
    # prevent scheduler from running
    monkeypatch.setattr('stockapp.__init__.start_scheduler', lambda: None)
    app = create_app()
    app.config['TESTING'] = True
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    client.post('/login', data={'username':'tester', 'password':'password'}, follow_redirects=True)
    return client
