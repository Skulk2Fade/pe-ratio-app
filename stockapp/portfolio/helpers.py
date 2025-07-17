from __future__ import annotations
import csv
import io
from typing import Callable, Dict, List, Tuple
from statistics import correlation, stdev
import random
from babel.numbers import format_currency
from flask_login import current_user

from datetime import datetime

from ..extensions import db
from ..models import PortfolioItem, Transaction, User
from ..utils import get_locale, convert_currency
from .. import brokerage


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


def sync_portfolio_from_brokerage(
    user_id: int, token: str, refresh: str | None = None, expiry: datetime | None = None
) -> None:
    """Synchronize holdings from a brokerage account."""
    if refresh and expiry and expiry <= datetime.utcnow():
        data = brokerage.refresh_access_token(refresh)
        if data and data.get("access_token"):
            token = data["access_token"]
            refresh = data.get("refresh_token", refresh)
            expiry = brokerage.token_expiry_time(data.get("expires_in", 0))
            user = User.query.get(user_id)
            if user:
                user.brokerage_access_token = token
                user.brokerage_refresh_token = refresh
                user.brokerage_token_expiry = expiry
                db.session.commit()
    holdings = brokerage.get_holdings(token)
    for h in holdings:
        symbol = h.get("symbol", "").upper()
        qty = h.get("quantity")
        price = h.get("price_paid")
        if not symbol or qty is None or price is None:
            continue
        item = PortfolioItem.query.filter_by(user_id=user_id, symbol=symbol).first()
        if item:
            item.quantity = qty
            item.price_paid = price
        else:
            db.session.add(
                PortfolioItem(
                    symbol=symbol,
                    quantity=qty,
                    price_paid=price,
                    user_id=user_id,
                )
            )
    db.session.commit()


def sync_transactions_from_brokerage(
    user_id: int, token: str, refresh: str | None = None, expiry: datetime | None = None
) -> None:
    """Import transaction history and update portfolio positions."""
    if refresh and expiry and expiry <= datetime.utcnow():
        data = brokerage.refresh_access_token(refresh)
        if data and data.get("access_token"):
            token = data["access_token"]
            refresh = data.get("refresh_token", refresh)
            expiry = brokerage.token_expiry_time(data.get("expires_in", 0))
            user = User.query.get(user_id)
            if user:
                user.brokerage_access_token = token
                user.brokerage_refresh_token = refresh
                user.brokerage_token_expiry = expiry
                db.session.commit()
    transactions = brokerage.get_transactions(token)
    for t in transactions:
        symbol = t.get("symbol", "").upper()
        qty = t.get("quantity")
        price = t.get("price")
        txn_type = t.get("type", "").upper()
        ts = t.get("timestamp")
        try:
            ts_dt = (
                datetime.fromisoformat(ts) if isinstance(ts, str) else datetime.utcnow()
            )
        except Exception:
            ts_dt = datetime.utcnow()
        if not symbol or qty is None or price is None or not txn_type:
            continue
        db.session.add(
            Transaction(
                symbol=symbol,
                quantity=qty,
                price=price,
                txn_type=txn_type,
                timestamp=ts_dt,
                user_id=user_id,
            )
        )
        item = PortfolioItem.query.filter_by(user_id=user_id, symbol=symbol).first()
        if txn_type == "BUY":
            if item:
                new_qty = item.quantity + qty
                total_cost = item.price_paid * item.quantity + price * qty
                item.quantity = new_qty
                item.price_paid = total_cost / new_qty
            else:
                db.session.add(
                    PortfolioItem(
                        symbol=symbol,
                        quantity=qty,
                        price_paid=price,
                        user_id=user_id,
                    )
                )
        elif txn_type == "SELL" and item:
            item.quantity = max(item.quantity - qty, 0)
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
        target_currency = currency
        if current_user.is_authenticated and current_user.default_currency:
            target_currency = current_user.default_currency
        if price is not None and currency != target_currency:
            price = convert_currency(price, currency, target_currency)
        currency = target_currency
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
        beta = None
        sharpe_ratio = None
        value_at_risk = None
        monte_carlo_var = None
        optimized_allocation = None
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
                        vol_daily = stdev(portfolio_returns)
                        vol = vol_daily * (252**0.5)
                        portfolio_volatility = round(vol * 100, 2)
                    except Exception:
                        portfolio_volatility = None
                    try:
                        avg_return = sum(portfolio_returns) / len(portfolio_returns)
                        sharpe_ratio = (
                            round((avg_return / vol_daily) * (252**0.5), 2)
                            if vol_daily
                            else None
                        )
                    except Exception:
                        sharpe_ratio = None
                    try:
                        sorted_returns = sorted(portfolio_returns)
                        idx_var = max(int(len(sorted_returns) * 0.05) - 1, 0)
                        var_pct = sorted_returns[idx_var]
                        value_at_risk = format_currency(
                            -var_pct * total_value,
                            totals_currency,
                            locale=get_locale(),
                        )
                    except Exception:
                        value_at_risk = None
                    try:
                        _m_dates, m_prices = get_historical_prices_func("SPY", days=30)
                        market_returns: List[float] = []
                        for i in range(1, len(m_prices)):
                            if m_prices[i - 1]:
                                market_returns.append(
                                    (m_prices[i] - m_prices[i - 1]) / m_prices[i - 1]
                                )
                        if (
                            len(market_returns) >= len(portfolio_returns)
                            and stdev(market_returns[-n:]) != 0
                        ):
                            b = correlation(
                                portfolio_returns[-n:], market_returns[-n:]
                            ) * (
                                stdev(portfolio_returns[-n:])
                                / stdev(market_returns[-n:])
                            )
                            beta = round(b, 2)
                    except Exception:
                        beta = None
                try:
                    sims = []
                    for _ in range(500):
                        val = total_value
                        for _ in range(n):
                            r = random.choice(portfolio_returns)
                            val *= 1 + r
                        sims.append(val)
                    sims.sort()
                    mc_var_val = total_value - sims[int(len(sims) * 0.05)]
                    monte_carlo_var = format_currency(
                        mc_var_val,
                        totals_currency,
                        locale=get_locale(),
                    )
                except Exception:
                    monte_carlo_var = None
                try:
                    optimized_allocation = optimize_portfolio(returns)
                except Exception:
                    optimized_allocation = None
        else:
            correlations = []
            portfolio_volatility = None
            beta = None
            sharpe_ratio = None
            value_at_risk = None
            optimized_allocation = None
            monte_carlo_var = None

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
        "beta": beta,
        "sharpe_ratio": sharpe_ratio,
        "value_at_risk": value_at_risk,
        "monte_carlo_var": monte_carlo_var,
        "optimized_allocation": optimized_allocation,
        "news": news_data,
    }


def optimize_portfolio(
    returns: Dict[str, List[float]], risk_free_rate: float = 0.0, samples: int = 5000
) -> Dict[str, float] | None:
    """Return weights that maximize the Sharpe ratio.

    This Monte Carlo approach avoids external dependencies and
    works with a small number of assets.
    """

    if not returns:
        return None

    n = min(len(r) for r in returns.values())
    if n < 2:
        return None

    symbols = list(returns.keys())
    truncated = {sym: r[-n:] for sym, r in returns.items()}

    def mean(x: List[float]) -> float:
        return sum(x) / len(x)

    def cov(x: List[float], y: List[float]) -> float:
        mx = mean(x)
        my = mean(y)
        return sum((xi - mx) * (yi - my) for xi, yi in zip(x, y)) / (len(x) - 1)

    means = {sym: mean(vals) for sym, vals in truncated.items()}
    cov_matrix = [
        [cov(truncated[s1], truncated[s2]) for s2 in symbols] for s1 in symbols
    ]

    best_weights = None
    best_sharpe = float("-inf")

    for _ in range(samples):
        raw = [random.random() for _ in symbols]
        total = sum(raw)
        weights = [r / total for r in raw]

        exp_return = sum(means[s] * w for s, w in zip(symbols, weights))

        variance = 0.0
        for i in range(len(symbols)):
            for j in range(len(symbols)):
                variance += weights[i] * weights[j] * cov_matrix[i][j]

        std = variance**0.5
        if std == 0:
            continue
        sharpe = (exp_return - risk_free_rate) / std
        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_weights = {sym: round(weights[idx], 4) for idx, sym in enumerate(symbols)}

    return best_weights
