import pytest


def test_oauth_login_route(client):
    resp = client.get("/login/google")
    assert resp.status_code in (302, 301)
    resp = client.get("/login/github")
    assert resp.status_code in (302, 301)
