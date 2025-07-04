from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from ..models import WatchlistItem, PortfolioItem, Alert

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/watchlist")
@login_required
def get_watchlist():
    items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    data = [
        {
            "id": i.id,
            "symbol": i.symbol,
            "pe_threshold": i.pe_threshold,
            "de_threshold": i.de_threshold,
            "rsi_threshold": i.rsi_threshold,
            "ma_threshold": i.ma_threshold,
            "notes": i.notes,
            "tags": i.tags,
        }
        for i in items
    ]
    return jsonify(data)


@api_bp.route("/portfolio")
@login_required
def get_portfolio():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    data = [
        {
            "id": i.id,
            "symbol": i.symbol,
            "quantity": i.quantity,
            "price_paid": i.price_paid,
            "notes": i.notes,
            "tags": i.tags,
        }
        for i in items
    ]
    return jsonify(data)


@api_bp.route("/alerts")
@login_required
def get_alerts():
    alerts = (
        Alert.query.filter_by(user_id=current_user.id)
        .order_by(Alert.timestamp.desc())
        .all()
    )
    data = [
        {
            "id": a.id,
            "symbol": a.symbol,
            "message": a.message,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        }
        for a in alerts
    ]
    return jsonify(data)
