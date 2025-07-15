from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    make_response,
    Response,
)
from flask_login import login_required, current_user
import csv
import io
import json
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
    generate_xlsx,
)
from ..forms import WatchlistAddForm, WatchlistUpdateForm

watch_bp = Blueprint("watch", __name__)


@watch_bp.route("/watchlist", methods=["GET", "POST"])
@login_required
def watchlist() -> str:
    add_form = WatchlistAddForm()
    update_form = WatchlistUpdateForm()
    error = None
    if request.method == "POST":
        if request.form.get("item_id"):
            if update_form.validate_on_submit():
                item_id = update_form.item_id.data
                threshold = update_form.threshold.data
                de_threshold = update_form.de_threshold.data
                rsi_threshold = update_form.rsi_threshold.data
                ma_threshold = update_form.ma_threshold.data
                notes = update_form.notes.data
                tags = update_form.tags.data
                public = update_form.public.data
                item = WatchlistItem.query.get_or_404(item_id)
                if item.user_id == current_user.id:
                    item.pe_threshold = threshold or ALERT_PE_THRESHOLD
                    item.de_threshold = de_threshold
                    item.rsi_threshold = rsi_threshold
                    item.ma_threshold = ma_threshold
                    item.notes = notes
                    item.tags = tags
                    item.is_public = public
                    db.session.commit()
            else:
                error = "; ".join(
                    f"{getattr(update_form, field).label.text}: {', '.join(msgs)}"
                    for field, msgs in update_form.errors.items()
                )
        else:
            if add_form.validate_on_submit():
                symbol = add_form.symbol.data.upper()
                threshold = add_form.threshold.data or ALERT_PE_THRESHOLD
                de_threshold = add_form.de_threshold.data
                rsi_threshold = add_form.rsi_threshold.data
                ma_threshold = add_form.ma_threshold.data
                notes = add_form.notes.data
                tags = add_form.tags.data
                public = add_form.public.data
                if not WatchlistItem.query.filter_by(
                    user_id=current_user.id, symbol=symbol
                ).first():
                    db.session.add(
                        WatchlistItem(
                            symbol=symbol,
                            user_id=current_user.id,
                            pe_threshold=threshold,
                            de_threshold=de_threshold,
                            rsi_threshold=rsi_threshold,
                            ma_threshold=ma_threshold,
                            notes=notes,
                            tags=tags,
                            is_public=public,
                        )
                    )
                    db.session.commit()
            else:
                error = "; ".join(
                    f"{getattr(add_form, field).label.text}: {', '.join(msgs)}"
                    for field, msgs in add_form.errors.items()
                )
    items = (
        WatchlistItem.query.filter_by(user_id=current_user.id)
        .order_by(WatchlistItem.symbol)
        .all()
    )
    news = {i.symbol: get_stock_news(i.symbol, limit=3) for i in items}
    sentiments = {}
    for sym, articles in news.items():
        if articles:
            avg = sum(a.get("sentiment", 0) for a in articles) / len(articles)
            sentiments[sym] = round(avg, 2)
        else:
            sentiments[sym] = None
    return render_template(
        "watchlist.html",
        items=items,
        add_form=add_form,
        update_form=update_form,
        error=error,
        default_threshold=ALERT_PE_THRESHOLD,
        news=news,
        sentiments=sentiments,
    )


@watch_bp.route("/watchlist/delete/<int:item_id>")
@login_required
def delete_watchlist_item(item_id: int) -> Response:
    item = WatchlistItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("watch.watchlist"))


@watch_bp.route("/watchlist/toggle_public/<int:item_id>")
@login_required
def toggle_public(item_id: int) -> Response:
    item = WatchlistItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        item.is_public = not item.is_public
        db.session.commit()
    return redirect(url_for("watch.watchlist"))


@watch_bp.route("/add_watchlist/<symbol>")
@login_required
def add_watchlist(symbol: str) -> Response:
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
def favorites() -> str:
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
def delete_favorite(item_id: int) -> Response:
    item = FavoriteTicker.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("watch.favorites"))


@watch_bp.route("/add_favorite/<symbol>")
@login_required
def add_favorite(symbol: str) -> Response:
    symbol = symbol.upper()
    if not FavoriteTicker.query.filter_by(
        user_id=current_user.id, symbol=symbol
    ).first():
        db.session.add(FavoriteTicker(symbol=symbol, user_id=current_user.id))
        db.session.commit()
    return redirect(url_for("main.index", ticker=symbol))


@watch_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings() -> str:
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
        brokerage = request.form.get("brokerage_token")
        if currency:
            current_user.default_currency = currency
        if language:
            current_user.language = language
        if theme in ("light", "dark"):
            current_user.theme = theme
        if brokerage is not None:
            current_user.brokerage_token = brokerage.strip() or None
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
        brokerage_token=current_user.brokerage_token or "",
    )


@watch_bp.route("/toggle_theme", methods=["POST"])
@login_required
def toggle_theme() -> Response:
    current_user.theme = "dark" if current_user.theme == "light" else "light"
    db.session.commit()
    return redirect(request.referrer or url_for("main.index"))


@watch_bp.route("/export_history")
@login_required
def export_history() -> Response | tuple[str, int]:
    fmt = request.args.get("format", "csv").lower()
    entries = (
        History.query.filter_by(user_id=current_user.id)
        .order_by(History.timestamp.desc())
        .all()
    )
    if fmt == "csv":
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
    elif fmt == "xlsx":
        output = generate_xlsx(
            ["Symbol", "Timestamp"],
            [
                [e.symbol, format_datetime(e.timestamp, locale=get_locale())]
                for e in entries
            ],
        )
        response = make_response(output)
        response.headers["Content-Disposition"] = "attachment; filename=history.xlsx"
        response.headers["Content-Type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return response
    elif fmt == "json":
        data = [
            {
                "symbol": e.symbol,
                "timestamp": format_datetime(e.timestamp, locale=get_locale()),
            }
            for e in entries
        ]
        response = make_response(json.dumps(data))
        response.headers["Content-Disposition"] = "attachment; filename=history.json"
        response.headers["Content-Type"] = "application/json"
        return response
    else:
        return "Invalid format", 400


@watch_bp.route("/records")
@login_required
def records() -> str:
    entries = (
        StockRecord.query.filter_by(user_id=current_user.id)
        .order_by(StockRecord.timestamp.desc())
        .all()
    )
    return render_template("records.html", records=entries)


@watch_bp.route("/clear_records")
@login_required
def clear_records() -> Response:
    StockRecord.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    return redirect(url_for("watch.records"))


@watch_bp.route("/watchlist/public/<username>")
def public_watchlist(username: str) -> str:
    from ..models import User

    user = User.query.filter_by(username=username).first_or_404()
    items = WatchlistItem.query.filter_by(user_id=user.id, is_public=True).all()
    news = {i.symbol: get_stock_news(i.symbol, limit=3) for i in items}
    sentiments = {}
    for sym, articles in news.items():
        if articles:
            avg = sum(a.get("sentiment", 0) for a in articles) / len(articles)
            sentiments[sym] = round(avg, 2)
        else:
            sentiments[sym] = None
    return render_template(
        "public_watchlist.html",
        items=items,
        user=user,
        news=news,
        sentiments=sentiments,
    )
