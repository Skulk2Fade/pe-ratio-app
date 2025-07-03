from __future__ import annotations
import csv
import io
from typing import Callable, Dict, List, Tuple
from statistics import correlation, stdev
from babel.numbers import format_currency

from ..extensions import db
from ..models import PortfolioItem
from ..utils import get_locale


# portfolio management helpers


def import_portfolio_items(file_storage, user_id: int) -> None:
    """Import portfolio items from an uploaded CSV file."""
    content = file_storage.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    for row in reader:
        symbol = row.get("Symbol", "").upper()
        try:
            quantity = float(row.get("Quantity", 0))
            price_paid = float(row.get("Price Paid", 0))
        except (TypeError, ValueError):
            continue
        if symbol and quantity and price_paid:
            if not PortfolioItem.query.filter_by(
                user_id=user_id, symbol=symbol
            ).first():
                db.session.add(
                    PortfolioItem(
                        symbol=symbol,
                        quantity=quantity,
                        price_paid=price_paid,
                        user_id=user_id,
                    )
                )
    db.session.commit()


def update_portfolio_item(form, user_id: int) -> None:
    """Update an existing portfolio item from a Flask form."""
    item_id = form.item_id.data
    quantity = form.quantity.data
    price_paid = form.price_paid.data
    notes = form.notes.data
    tags = form.tags.data
    item = PortfolioItem.query.get_or_404(item_id)
    if item.user_id == user_id:
        if quantity is not None:
            item.quantity = quantity
        if price_paid is not None:
            item.price_paid = price_paid
        item.notes = notes
        item.tags = tags
        db.session.commit()


def add_portfolio_item(form, user_id: int) -> None:
    """Add a new portfolio item from a Flask form."""
    symbol = form.symbol.data.upper()
    quantity = form.quantity.data
    price_paid = form.price_paid.data
    notes = form.notes.data
    tags = form.tags.data
    if quantity is not None and price_paid is not None:
        if not PortfolioItem.query.filter_by(user_id=user_id, symbol=symbol).first():
            db.session.add(
                PortfolioItem(
                    symbol=symbol,
                    quantity=quantity,
                    price_paid=price_paid,
                    user_id=user_id,
                    notes=notes,
                    tags=tags,
                )
            )
            db.session.commit()


def calculate_portfolio_analysis(
    items: List[PortfolioItem],
    get_stock_data_func: Callable[[str], Tuple],
    get_historical_prices_func: Callable[[str], Tuple[List[str], List[float]]],
    get_stock_news_func: Callable[[str], List[Dict]],
) -> Dict[str, object]:
    """Return aggregated portfolio metrics for rendering."""
    data: List[Dict[str, object]] = []
    total_value = 0.0
    total_pl = 0.0
    totals_currency = None
    sector_totals: Dict[str, float] = {}

    for item in items:
        (
            _name,
            _logo_url,
            sector,
            _industry,
            _exchange,
            currency,
            price,
            *_rest,
        ) = get_stock_data_func(item.symbol)
        if price is not None:
            current_price = format_currency(price, currency, locale=get_locale())
            value_num = price * item.quantity
            pl_num = (price - item.price_paid) * item.quantity
            value = format_currency(value_num, currency, locale=get_locale())
            pl = format_currency(pl_num, currency, locale=get_locale())
            total_value += value_num
            total_pl += pl_num
            if totals_currency is None:
                totals_currency = currency
            if sector:
                sector_totals[sector] = sector_totals.get(sector, 0) + value_num
        else:
            current_price = value = pl = None
            value_num = 0
        data.append(
            {
                "item": item,
                "current_price": current_price,
                "value": value,
                "profit_loss": pl,
                "price_num": price,
                "value_num": value_num,
            }
        )

    totals = None
    if items and totals_currency:
        totals = {
            "value": format_currency(total_value, totals_currency, locale=get_locale()),
            "profit_loss": format_currency(
                total_pl, totals_currency, locale=get_locale()
            ),
        }

    diversification = []
    risk_assessment = None
    if total_value > 0:
        for sec, val in sector_totals.items():
            pct = round(val / total_value * 100, 2)
            diversification.append({"sector": sec, "percentage": pct})
        diversification.sort(key=lambda x: x["percentage"], reverse=True)
        if diversification:
            top = diversification[0]
            if top["percentage"] > 50:
                risk_assessment = f"High concentration in {top['sector']}"
            elif top["percentage"] > 30:
                risk_assessment = f"Moderate concentration in {top['sector']}"
            else:
                risk_assessment = "Well diversified across sectors."

        returns: Dict[str, List[float]] = {}
        weights: Dict[str, float] = {}
        for row in data:
            sym = row["item"].symbol
            price_num = row["price_num"]
            if price_num is None:
                continue
            weights[sym] = row["value_num"] / total_value if total_value else 0
            _dates, prices = get_historical_prices_func(sym, days=30)
            if len(prices) > 1:
                r: List[float] = []
                for i in range(1, len(prices)):
                    try:
                        if prices[i - 1]:
                            r.append((prices[i] - prices[i - 1]) / prices[i - 1])
                    except Exception:
                        pass
                if r:
                    returns[sym] = r
        correlations = []
        if returns:
            syms = list(returns.keys())
            for i in range(len(syms)):
                r1 = returns[syms[i]]
                for j in range(i + 1, len(syms)):
                    r2 = returns[syms[j]]
                    n = min(len(r1), len(r2))
                    if n > 1:
                        try:
                            c = correlation(r1[-n:], r2[-n:])
                            correlations.append(
                                {"pair": f"{syms[i]}-{syms[j]}", "value": round(c, 2)}
                            )
                        except Exception:
                            pass
        portfolio_volatility = None
        if returns and len(returns) > 0:
            n = min(len(r) for r in returns.values())
            if n > 1:
                portfolio_returns: List[float] = []
                for idx in range(-n, 0):
                    day_ret = 0.0
                    for sym, r in returns.items():
                        if len(r) >= n:
                            day_ret += weights.get(sym, 0) * r[idx]
                    portfolio_returns.append(day_ret)
                if len(portfolio_returns) > 1:
                    try:
                        vol = stdev(portfolio_returns) * (252**0.5)
                        portfolio_volatility = round(vol * 100, 2)
                    except Exception:
                        portfolio_volatility = None
    else:
        correlations = []
        portfolio_volatility = None

    news_data = {
        row["item"].symbol: get_stock_news_func(row["item"].symbol, limit=3)
        for row in data
    }

    return {
        "data": data,
        "totals": totals,
        "diversification": diversification,
        "risk_assessment": risk_assessment,
        "correlations": correlations,
        "portfolio_volatility": portfolio_volatility,
        "news": news_data,
    }
