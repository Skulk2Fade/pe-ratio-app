from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_login import login_required, current_user
import csv
import io
from babel.dates import format_datetime

from ..extensions import db

from ..models import (
    WatchlistItem,
    FavoriteTicker,
    History,
    StockRecord,
)
from ..utils import (
    get_locale,
    ALERT_PE_THRESHOLD,
    get_stock_data,
    get_stock_news,
)
from ..forms import WatchlistAddForm, WatchlistUpdateForm

watch_bp = Blueprint("watch", __name__)


@watch_bp.route("/watchlist", methods=["GET", "POST"])
@login_required
def watchlist():
    add_form = WatchlistAddForm()
    update_form = WatchlistUpdateForm()
    if request.method == "POST":
        if request.form.get("item_id"):
            if update_form.validate_on_submit():
                item_id = update_form.item_id.data
                threshold = update_form.threshold.data
                notes = update_form.notes.data
                tags = update_form.tags.data
                item = WatchlistItem.query.get_or_404(item_id)
                if item.user_id == current_user.id:
                    item.pe_threshold = threshold or ALERT_PE_THRESHOLD
                    item.notes = notes
                    item.tags = tags
                    db.session.commit()
        else:
            if add_form.validate_on_submit():
                symbol = add_form.symbol.data.upper()
                threshold = add_form.threshold.data or ALERT_PE_THRESHOLD
                notes = add_form.notes.data
                tags = add_form.tags.data
                if not WatchlistItem.query.filter_by(
                    user_id=current_user.id, symbol=symbol
                ).first():
                    db.session.add(
                        WatchlistItem(
                            symbol=symbol,
                            user_id=current_user.id,
                            pe_threshold=threshold,
                            notes=notes,
                            tags=tags,
                        )
                    )
                    db.session.commit()
    items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    news = {i.symbol: get_stock_news(i.symbol, limit=3) for i in items}
    return render_template(
        "watchlist.html",
        items=items,
        add_form=add_form,
        update_form=update_form,
        default_threshold=ALERT_PE_THRESHOLD,
        news=news,
    )


@watch_bp.route("/watchlist/delete/<int:item_id>")
@login_required
def delete_watchlist_item(item_id):
    item = WatchlistItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("watch.watchlist"))


@watch_bp.route("/add_watchlist/<symbol>")
@login_required
def add_watchlist(symbol):
    symbol = symbol.upper()
    if not WatchlistItem.query.filter_by(
        user_id=current_user.id, symbol=symbol
    ).first():
        db.session.add(
            WatchlistItem(
                symbol=symbol, user_id=current_user.id, pe_threshold=ALERT_PE_THRESHOLD
            )
        )
        db.session.commit()
    return redirect(url_for("main.index", ticker=symbol))


@watch_bp.route("/favorites", methods=["GET", "POST"])
@login_required
def favorites():
    if request.method == "POST":
        symbol = request.form["symbol"].upper()
        if not FavoriteTicker.query.filter_by(
            user_id=current_user.id, symbol=symbol
        ).first():
            db.session.add(FavoriteTicker(symbol=symbol, user_id=current_user.id))
            db.session.commit()
    items = FavoriteTicker.query.filter_by(user_id=current_user.id).all()
    return render_template("favorites.html", items=items)


@watch_bp.route("/favorites/delete/<int:item_id>")
@login_required
def delete_favorite(item_id):
    item = FavoriteTicker.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("watch.favorites"))


@watch_bp.route("/add_favorite/<symbol>")
@login_required
def add_favorite(symbol):
    symbol = symbol.upper()
    if not FavoriteTicker.query.filter_by(
        user_id=current_user.id, symbol=symbol
    ).first():
        db.session.add(FavoriteTicker(symbol=symbol, user_id=current_user.id))
        db.session.commit()
    return redirect(url_for("main.index", ticker=symbol))


@watch_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        freq = request.form.get("frequency", type=int)
        if freq and freq > 0:
            current_user.alert_frequency = freq
        phone = request.form.get("phone")
        current_user.phone_number = phone
        current_user.sms_opt_in = bool(request.form.get("sms_opt_in"))
        current_user.trend_opt_in = bool(request.form.get("trend_opt_in"))
        currency = request.form.get("currency")
        language = request.form.get("language")
        theme = request.form.get("theme")
        if currency:
            current_user.default_currency = currency
        if language:
            current_user.language = language
        if theme in ("light", "dark"):
            current_user.theme = theme
        db.session.commit()
    return render_template(
        "settings.html",
        frequency=current_user.alert_frequency,
        phone=current_user.phone_number or "",
        sms_opt_in=current_user.sms_opt_in,
        trend_opt_in=current_user.trend_opt_in,
        currency=current_user.default_currency,
        language=current_user.language,
        theme=current_user.theme,
    )


@watch_bp.route("/export_history")
@login_required
def export_history():
    entries = (
        History.query.filter_by(user_id=current_user.id)
        .order_by(History.timestamp.desc())
        .all()
    )
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Symbol", "Timestamp"])
    for e in entries:
        timestamp = format_datetime(e.timestamp, locale=get_locale())
        writer.writerow([e.symbol, timestamp])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=history.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@watch_bp.route("/records")
@login_required
def records():
    entries = (
        StockRecord.query.filter_by(user_id=current_user.id)
        .order_by(StockRecord.timestamp.desc())
        .all()
    )
    return render_template("records.html", records=entries)


@watch_bp.route("/clear_records")
@login_required
def clear_records():
    StockRecord.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("watch.records"))
