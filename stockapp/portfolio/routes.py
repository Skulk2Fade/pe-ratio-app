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
from fpdf import FPDF

from ..extensions import db
from ..models import (
    PortfolioItem,
    PortfolioFollow,
    PortfolioComment,
    User,
)

from ..utils import (
    get_stock_data,
    get_historical_prices,
    get_stock_news,
    generate_xlsx,
    get_dividend_history,
    get_upcoming_dividends,
)
from ..forms import (
    PortfolioAddForm,
    PortfolioUpdateForm,
    PortfolioImportForm,
    CommentForm,
)
from .helpers import (
    import_portfolio_items,
    update_portfolio_item,
    add_portfolio_item,
    calculate_portfolio_analysis,
    sync_portfolio_from_brokerage,
)

portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.route("/export_portfolio")
@login_required
def export_portfolio() -> Response | tuple[str, int]:
    fmt = request.args.get("format", "csv").lower()
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Symbol", "Quantity", "Price Paid"])
        for item in items:
            writer.writerow([item.symbol, item.quantity, item.price_paid])
        response = make_response(output.getvalue())
        response.headers["Content-Disposition"] = "attachment; filename=portfolio.csv"
        response.headers["Content-Type"] = "text/csv"
        return response
    elif fmt == "xlsx":
        output = generate_xlsx(
            ["Symbol", "Quantity", "Price Paid"],
            [[item.symbol, item.quantity, item.price_paid] for item in items],
        )
        response = make_response(output)
        response.headers["Content-Disposition"] = "attachment; filename=portfolio.xlsx"
        response.headers["Content-Type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return response
    elif fmt == "json":
        data = [
            {
                "symbol": item.symbol,
                "quantity": item.quantity,
                "price_paid": item.price_paid,
            }
            for item in items
        ]
        response = make_response(json.dumps(data))
        response.headers["Content-Disposition"] = "attachment; filename=portfolio.json"
        response.headers["Content-Type"] = "application/json"
        return response
    elif fmt == "pdf":
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(0, 10, txt="Portfolio", ln=1)
        pdf.cell(60, 10, txt="Symbol", border=1)
        pdf.cell(40, 10, txt="Quantity", border=1)
        pdf.cell(40, 10, txt="Price Paid", border=1, ln=1)
        for item in items:
            pdf.cell(60, 10, txt=str(item.symbol), border=1)
            pdf.cell(40, 10, txt=str(item.quantity), border=1)
            pdf.cell(40, 10, txt=str(item.price_paid), border=1, ln=1)
        pdf_output = pdf.output(dest="S").encode("latin-1")
        response = make_response(pdf_output)
        response.headers["Content-Disposition"] = "attachment; filename=portfolio.pdf"
        response.headers["Content-Type"] = "application/pdf"
        return response
    else:
        return "Invalid format", 400


@portfolio_bp.route("/portfolio/sync")
@login_required
def sync_brokerage() -> Response:
    token = current_user.brokerage_access_token or current_user.brokerage_token
    if not token:
        return redirect(url_for("portfolio.portfolio"))
    sync_portfolio_from_brokerage(
        current_user.id,
        token,
        refresh=current_user.brokerage_refresh_token,
        expiry=current_user.brokerage_token_expiry,
    )
    return redirect(url_for("portfolio.portfolio"))


@portfolio_bp.route("/portfolio", methods=["GET", "POST"])
@login_required
def portfolio() -> str:
    symbol_prefill = request.args.get("symbol", "").upper()
    days = request.args.get("days", "30")
    try:
        days_int = int(days)
    except ValueError:
        days_int = 30
    add_form = PortfolioAddForm(symbol=symbol_prefill)
    import_form = PortfolioImportForm()
    update_form = PortfolioUpdateForm()

    if request.method == "POST":
        if request.files.get("file"):
            if import_form.validate_on_submit():
                import_portfolio_items(request.files["file"], current_user.id)
        elif request.form.get("item_id"):
            if update_form.validate_on_submit():
                update_portfolio_item(update_form, current_user.id)
        else:
            if add_form.validate_on_submit():
                add_portfolio_item(add_form, current_user.id)

    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    analysis = calculate_portfolio_analysis(
        items, get_stock_data, get_historical_prices, get_stock_news, days_int
    )

    return render_template(
        "portfolio.html",
        symbols=[row["item"].symbol for row in analysis["data"]],
        items=analysis["data"],
        symbol=symbol_prefill,
        totals=analysis["totals"],
        diversification=analysis["diversification"],
        risk_assessment=analysis["risk_assessment"],
        correlations=analysis["correlations"],
        portfolio_volatility=analysis["portfolio_volatility"],
        beta=analysis["beta"],
        sharpe_ratio=analysis["sharpe_ratio"],
        value_at_risk=analysis["value_at_risk"],
        monte_carlo_var=analysis["monte_carlo_var"],
        optimized_allocation=analysis["optimized_allocation"],
        maximum_drawdown=analysis["maximum_drawdown"],
        sector_correlations=analysis["sector_correlations"],
        sectors=sorted({row["sector"] for row in analysis["data"] if row["sector"]}),
        news=analysis["news"],
        news_summaries=analysis["news_summaries"],
        add_form=add_form,
        import_form=import_form,
        update_form=update_form,
    )


@portfolio_bp.route("/dividends")
@login_required
def dividends() -> str:
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    data = []
    for item in items:
        history = get_dividend_history(item.symbol, limit=5)
        upcoming = get_upcoming_dividends(item.symbol, days=30)
        info = get_stock_data(item.symbol)
        yield_pct = info[15]
        if yield_pct is not None:
            try:
                yield_pct = round(yield_pct * 100, 2)
            except Exception:
                yield_pct = None
        data.append(
            {
                "symbol": item.symbol,
                "history": history,
                "upcoming": upcoming,
                "yield": yield_pct,
            }
        )
    return render_template("dividends.html", dividends=data)


@portfolio_bp.route("/portfolio/delete/<int:item_id>")
@login_required
def delete_portfolio_item(item_id: int) -> Response:
    item = PortfolioItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("portfolio.portfolio"))


@portfolio_bp.route("/portfolio/<username>")
@login_required
def view_portfolio(username: str) -> str:
    user = User.query.filter_by(username=username).first_or_404()
    items = PortfolioItem.query.filter_by(user_id=user.id).all()
    following = PortfolioFollow.query.filter_by(
        follower_id=current_user.id, followed_id=user.id
    ).first()
    comments = (
        PortfolioComment.query.filter_by(portfolio_owner_id=user.id)
        .order_by(PortfolioComment.timestamp.desc())
        .all()
    )
    comment_form = CommentForm()
    return render_template(
        "public_portfolio.html",
        items=items,
        user=user,
        following=bool(following),
        comments=comments,
        comment_form=comment_form,
    )


@portfolio_bp.route("/portfolio/follow/<username>")
@login_required
def follow_portfolio(username: str) -> Response:
    user = User.query.filter_by(username=username).first_or_404()
    if user.id == current_user.id:
        return redirect(url_for("portfolio.view_portfolio", username=username))
    existing = PortfolioFollow.query.filter_by(
        follower_id=current_user.id, followed_id=user.id
    ).first()
    if existing:
        db.session.delete(existing)
    else:
        db.session.add(
            PortfolioFollow(follower_id=current_user.id, followed_id=user.id)
        )
    db.session.commit()
    return redirect(url_for("portfolio.view_portfolio", username=username))


@portfolio_bp.route("/portfolio/comment/<username>", methods=["POST"])
@login_required
def comment_portfolio(username: str) -> Response:
    user = User.query.filter_by(username=username).first_or_404()
    form = CommentForm()
    if form.validate_on_submit():
        db.session.add(
            PortfolioComment(
                user_id=current_user.id,
                portfolio_owner_id=user.id,
                content=form.content.data,
            )
        )
        db.session.commit()
    return redirect(url_for("portfolio.view_portfolio", username=username))


@portfolio_bp.route("/leaderboard")
def leaderboard() -> str:
    from sqlalchemy import func

    results = (
        db.session.query(User.username, func.count(PortfolioFollow.id).label("count"))
        .outerjoin(PortfolioFollow, User.id == PortfolioFollow.followed_id)
        .group_by(User.id)
        .order_by(func.count(PortfolioFollow.id).desc())
        .limit(10)
        .all()
    )
    return render_template("leaderboard.html", leaders=results)
