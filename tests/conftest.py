import os
import pytest
from stockapp import create_app

@pytest.fixture
def app(monkeypatch):
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ.setdefault('API_KEY', 'demo')
    os.environ['DEFAULT_USERNAME'] = 'tester'
    os.environ['DEFAULT_PASSWORD'] = 'password'
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    from stockapp import tasks
    tasks.celery.conf.update(task_always_eager=True)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_client(client):
    client.post('/login', data={'username':'tester', 'password':'password'}, follow_redirects=True)
    return client
