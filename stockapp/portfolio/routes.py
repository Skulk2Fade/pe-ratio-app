from flask import Blueprint, render_template, request, redirect, url_for, make_response
from flask_login import login_required, current_user
import csv
import io

from ..extensions import db
from ..models import PortfolioItem, PortfolioFollow, User

from ..utils import get_stock_data, get_historical_prices, get_stock_news
from ..forms import PortfolioAddForm, PortfolioUpdateForm, PortfolioImportForm
from .helpers import (
    import_portfolio_items,
    update_portfolio_item,
    add_portfolio_item,
    calculate_portfolio_analysis,
)

portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.route("/export_portfolio")
@login_required
def export_portfolio():
    items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Symbol", "Quantity", "Price Paid"])
    for item in items:
        writer.writerow([item.symbol, item.quantity, item.price_paid])
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=portfolio.csv"
    response.headers["Content-Type"] = "text/csv"
    return response


@portfolio_bp.route("/portfolio", methods=["GET", "POST"])
@login_required
def portfolio():
    symbol_prefill = request.args.get("symbol", "").upper()
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
        items, get_stock_data, get_historical_prices, get_stock_news
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
        news=analysis["news"],
        add_form=add_form,
        import_form=import_form,
        update_form=update_form,
    )


@portfolio_bp.route("/portfolio/delete/<int:item_id>")
@login_required
def delete_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    if item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for("portfolio.portfolio"))


@portfolio_bp.route("/portfolio/<username>")
@login_required
def view_portfolio(username):
    user = User.query.filter_by(username=username).first_or_404()
    items = PortfolioItem.query.filter_by(user_id=user.id).all()
    following = PortfolioFollow.query.filter_by(
        follower_id=current_user.id, followed_id=user.id
    ).first()
    return render_template(
        "public_portfolio.html",
        items=items,
        user=user,
        following=bool(following),
    )


@portfolio_bp.route("/portfolio/follow/<username>")
@login_required
def follow_portfolio(username):
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
