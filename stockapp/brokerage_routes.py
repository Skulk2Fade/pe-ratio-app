from flask import Blueprint, redirect, request, url_for, session
from flask_login import login_required, current_user

from . import brokerage
from .extensions import db

broker_bp = Blueprint("broker", __name__)


@broker_bp.route("/brokerage/connect")
@login_required
def connect():
    state = brokerage.generate_state()
    session["broker_oauth_state"] = state
    return redirect(brokerage.get_authorization_url(state))


@broker_bp.route("/brokerage/callback")
@login_required
def callback():
    stored = session.pop("broker_oauth_state", None)
    state = request.args.get("state")
    code = request.args.get("code")
    if not code or stored != state:
        return redirect(url_for("portfolio.portfolio"))
    token_data = brokerage.exchange_code_for_token(code)
    if not token_data:
        return redirect(url_for("portfolio.portfolio"))
    current_user.brokerage_access_token = token_data.get("access_token")
    current_user.brokerage_refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    if expires_in:
        current_user.brokerage_token_expiry = brokerage.token_expiry_time(expires_in)
    db.session.commit()
    return redirect(url_for("portfolio.portfolio"))


@broker_bp.route("/brokerage/disconnect")
@login_required
def disconnect():
    current_user.brokerage_access_token = None
    current_user.brokerage_refresh_token = None
    current_user.brokerage_token_expiry = None
    db.session.commit()
    return redirect(url_for("portfolio.portfolio"))
