import pytest
from stockapp.tasks import (
    check_watchlists_task,
    send_trend_summaries_task,
    check_dividends_task,
    send_mobile_push_task,
)


def test_check_watchlists_task_invokes_helper(monkeypatch):
    called = []
    monkeypatch.setattr("stockapp.tasks._check_watchlists", lambda: called.append(True))
    check_watchlists_task()
    assert called


def test_send_trend_summaries_task_invokes_helper(monkeypatch):
    called = []
    monkeypatch.setattr(
        "stockapp.tasks._send_trend_summaries", lambda: called.append(True)
    )
    send_trend_summaries_task()
    assert called


def test_check_dividends_task_invokes_helper(monkeypatch):
    called = []
    monkeypatch.setattr("stockapp.tasks._check_dividends", lambda: called.append(True))
    check_dividends_task()
    assert called


def test_send_mobile_push_task_invokes_helper(monkeypatch):
    called = []
    monkeypatch.setattr(
        "stockapp.tasks.send_mobile_push", lambda *a, **k: called.append(True)
    )
    send_mobile_push_task("t", "title", "body")
    assert called
