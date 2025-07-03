from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Alert

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
