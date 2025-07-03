import pytest

from stockapp.forms import SignupForm, LoginForm
from stockapp.tasks import check_watchlists_task


def test_download_errors(client, monkeypatch):
    monkeypatch.setattr(
        'stockapp.main.routes.get_stock_data',
        lambda s: (
            'Test', '', '', '', 'NASDAQ', 'USD',
            100, 5, '1B', None, None, None, None, None, None,
            None, None, None, None, None, None, None, None
        )
    )
    resp = client.get('/download')
    assert resp.status_code == 400
    resp = client.get('/download?symbol=AAA&format=bogus')
    assert resp.status_code == 400


def test_form_validation(app):
    with app.test_request_context():
        form = SignupForm(meta={'csrf': False}, data={'username': '', 'email': 'bad', 'password': ''})
        assert not form.validate()
        form2 = LoginForm(meta={'csrf': False}, data={'username': '', 'password': ''})
        assert not form2.validate()


def test_celery_task_invocation(monkeypatch):
    called = []
    monkeypatch.setattr('stockapp.tasks._check_watchlists', lambda: called.append(True))
    check_watchlists_task()
    assert called


def test_api_requires_login(client):
    for endpoint in ['/api/watchlist', '/api/portfolio', '/api/alerts']:
        resp = client.get(endpoint)
        assert resp.status_code in (302, 401)
        if resp.status_code == 302:
            assert '/login' in resp.headers['Location']
