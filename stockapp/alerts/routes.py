from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Alert, PushSubscription
from ..utils import notify_user_push

alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts")
@login_required
def alerts():
    entries = (
        Alert.query.filter_by(user_id=current_user.id)
        .order_by(Alert.timestamp.desc())
        .all()
    )
    return render_template("alerts.html", alerts=entries)


@alerts_bp.route("/clear_alerts")
@login_required
def clear_alerts():
    Alert.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("alerts.alerts"))


@alerts_bp.route("/subscribe_push", methods=["POST"])
@login_required
def subscribe_push():
    data = request.get_json() or {}
    if not data.get("endpoint"):
        return "", 400
    sub = PushSubscription.query.filter_by(
        user_id=current_user.id, endpoint=data.get("endpoint")
    ).first()
    if not sub:
        db.session.add(
            PushSubscription(
                endpoint=data["endpoint"],
                p256dh=data.get("keys", {}).get("p256dh"),
                auth=data.get("keys", {}).get("auth"),
                user_id=current_user.id,
            )
        )
        db.session.commit()
    return "", 204


@alerts_bp.route("/unsubscribe_push", methods=["POST"])
@login_required
def unsubscribe_push():
    data = request.get_json() or {}
    PushSubscription.query.filter_by(
        user_id=current_user.id, endpoint=data.get("endpoint")
    ).delete()
    db.session.commit()
    return "", 204
