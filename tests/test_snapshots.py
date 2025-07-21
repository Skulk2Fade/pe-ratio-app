from stockapp.tasks import _create_snapshots
from stockapp.models import DataSnapshot, User, PortfolioItem, WatchlistItem
from stockapp.extensions import db


def test_create_snapshots(app):
    with app.app_context():
        user = User.query.filter_by(username="tester").first()
        db.session.add(PortfolioItem(symbol="AAA", quantity=1, price_paid=10, user_id=user.id))
        db.session.add(WatchlistItem(symbol="AAA", user_id=user.id))
        db.session.commit()
        _create_snapshots()
        snap = DataSnapshot.query.filter_by(user_id=user.id).first()
        assert snap is not None
        assert "AAA" in snap.portfolio
        assert "AAA" in snap.watchlist
