import pytest

from stockapp.portfolio.helpers import sync_transactions_from_brokerage
from stockapp import brokerage
from stockapp.models import User, PortfolioItem, Transaction
from stockapp.extensions import db


def test_sync_transactions(app):
    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        sync_transactions_from_brokerage(user.id, "demo-token")
        txns = Transaction.query.filter_by(user_id=user.id).all()
        assert len(txns) == 2
        items = {
            i.symbol: i for i in PortfolioItem.query.filter_by(user_id=user.id).all()
        }
        assert "AAA" in items
        assert items["AAA"].quantity >= 1


def test_account_balance():
    bal = brokerage.get_account_balance("demo-token")
    assert bal == 10000.0
