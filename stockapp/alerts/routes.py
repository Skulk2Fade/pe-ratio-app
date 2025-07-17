from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Alert, PushSubscription, CustomAlertRule
from ..utils import notify_user_push
from ..forms import CustomRuleForm, CustomRuleUpdateForm

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


@alerts_bp.route("/custom_rules", methods=["GET", "POST"])
@login_required
def custom_rules():
    add_form = CustomRuleForm()
    update_form = CustomRuleUpdateForm()
    error = None
    if request.method == "POST":
        if request.form.get("rule_id"):
            if update_form.validate_on_submit():
                rule = CustomAlertRule.query.get_or_404(update_form.rule_id.data)
                if rule.user_id == current_user.id:
                    rule.description = update_form.description.data
                    rule.rule = update_form.rule.data
                    db.session.commit()
            else:
                error = "; ".join(
                    f"{getattr(update_form, f).label.text}: {', '.join(m)}"
                    for f, m in update_form.errors.items()
                )
        else:
            if add_form.validate_on_submit():
                db.session.add(
                    CustomAlertRule(
                        description=add_form.description.data,
                        rule=add_form.rule.data,
                        user_id=current_user.id,
                    )
                )
                db.session.commit()
            else:
                error = "; ".join(
                    f"{getattr(add_form, f).label.text}: {', '.join(m)}"
                    for f, m in add_form.errors.items()
                )
    rules = CustomAlertRule.query.filter_by(user_id=current_user.id).all()
    return render_template(
        "custom_rules.html",
        rules=rules,
        add_form=add_form,
        update_form=update_form,
        error=error,
    )


@alerts_bp.route("/custom_rules/delete/<int:rule_id>")
@login_required
def delete_rule(rule_id: int):
    rule = CustomAlertRule.query.get_or_404(rule_id)
    if rule.user_id == current_user.id:
        db.session.delete(rule)
        db.session.commit()
    return redirect(url_for("alerts.custom_rules"))
