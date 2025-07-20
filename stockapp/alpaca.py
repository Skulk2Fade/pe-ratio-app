"""Minimal Alpaca brokerage integration stub."""

from __future__ import annotations
from typing import List, Dict, Optional
import os

from .utils import session

ALPACA_API_BASE = os.environ.get("ALPACA_API_BASE")


def _api_get(path: str, token: str) -> Optional[Dict[str, object]]:
    if not ALPACA_API_BASE:
        return None
    try:
        resp = session.get(
            f"{ALPACA_API_BASE.rstrip('/')}/{path.lstrip('/')}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def get_holdings(access_token: str) -> List[Dict[str, float]]:
    """Return holdings for the given Alpaca access token."""
    if access_token == "demo-alpaca-token":
        return [
            {"symbol": "AAA", "quantity": 5, "price_paid": 100},
            {"symbol": "BBB", "quantity": 2, "price_paid": 105},
        ]
    data = _api_get("positions", access_token)
    if isinstance(data, list):
        result = []
        for h in data:
            symbol = h.get("symbol", "").upper()
            try:
                qty = float(h.get("qty", h.get("quantity", 0)))
                price = float(h.get("avg_entry_price", h.get("price_paid", 0)))
            except Exception:
                continue
            result.append({"symbol": symbol, "quantity": qty, "price_paid": price})
        return result
    return []


def get_transactions(access_token: str) -> List[Dict[str, object]]:
    """Return recent trade activities."""
    if access_token == "demo-alpaca-token":
        return [
            {
                "symbol": "AAA",
                "quantity": 1,
                "price": 101,
                "type": "BUY",
                "timestamp": "2023-01-03",
            },
        ]
    data = _api_get("activities", access_token)
    if isinstance(data, list):
        return data
    return []


def get_account_balance(access_token: str) -> Optional[float]:
    """Return the cash balance for the account."""
    if access_token == "demo-alpaca-token":
        return 2500.0
    data = _api_get("account", access_token)
    if isinstance(data, dict):
        try:
            return float(data.get("cash", data.get("cash_balance", 0)))
        except Exception:
            return None
    return None
