"""Stub functions for Plaid brokerage integration.

These placeholder functions emulate Plaid's API so unit tests can run
without network access or real credentials.
"""
from __future__ import annotations
from typing import List, Dict, Optional


def get_holdings(access_token: str) -> List[Dict[str, float]]:
    """Return holdings for the given Plaid access token."""
    if access_token == "demo-plaid-token":
        return [
            {"symbol": "AAA", "quantity": 3, "price_paid": 100},
            {"symbol": "BBB", "quantity": 2, "price_paid": 105},
        ]
    return []


def get_transactions(access_token: str) -> List[Dict[str, object]]:
    """Return recent transactions for the given token."""
    if access_token == "demo-plaid-token":
        return [
            {
                "symbol": "AAA",
                "quantity": 1,
                "price": 100,
                "type": "BUY",
                "timestamp": "2023-01-01",
            },
            {
                "symbol": "BBB",
                "quantity": 1,
                "price": 105,
                "type": "BUY",
                "timestamp": "2023-01-02",
            },
        ]
    return []


def get_account_balance(access_token: str) -> Optional[float]:
    """Return the cash balance for the Plaid account."""
    if access_token == "demo-plaid-token":
        return 5000.0
    return None
