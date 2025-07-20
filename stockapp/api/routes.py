from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from ..models import WatchlistItem, PortfolioItem, Alert
from ..utils import get_news_summary
from ..backtesting import backtest_custom_rule

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


@api_bp.route("/news_summary/<symbol>")
def news_summary(symbol: str):
    period = request.args.get("period", "daily")
    summary = get_news_summary(symbol.upper(), period)
    return jsonify({"symbol": symbol.upper(), "summary": summary})


@api_bp.route("/backtest_rule")
@login_required
def api_backtest_rule():
    """Return historical evaluation of a custom rule."""
    rule = request.args.get("rule", "")
    days_param = request.args.get("days", "30")
    try:
        days = int(days_param)
    except ValueError:
        days = 30
    if not rule:
        return jsonify({"error": "rule required"}), 400
    results = backtest_custom_rule(rule, days)
    return jsonify({"rule": rule, "results": results})
