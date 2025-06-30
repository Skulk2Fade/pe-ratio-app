import os
import pytest
from stockapp import create_app

@pytest.fixture
def app(monkeypatch):
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ.setdefault('API_KEY', 'demo')
    os.environ['DEFAULT_USERNAME'] = 'tester'
    os.environ['DEFAULT_PASSWORD'] = 'password'
    os.environ['ENABLE_SCHEDULER'] = '0'
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
