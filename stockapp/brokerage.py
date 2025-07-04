"""Simple brokerage API client stub for tests.

This module provides a function to retrieve a user's holdings from a
brokerage service. In the real application this would make HTTP requests
to the brokerage provider, but for the test environment we simply return
static data when a special token is used.
"""

from typing import List, Dict


def get_holdings(api_token: str) -> List[Dict[str, float]]:
    """Return a list of holdings for the given API token.

    Parameters
    ----------
    api_token: str
        Authentication token for the brokerage account.

    Returns
    -------
    list of dict
        Each dictionary contains ``symbol``, ``quantity`` and ``price_paid``.
    """
    if api_token == "demo-token":
        return [
            {"symbol": "AAA", "quantity": 2, "price_paid": 90},
            {"symbol": "BBB", "quantity": 1, "price_paid": 110},
        ]
    return []


def get_transactions(api_token: str) -> List[Dict[str, object]]:
    """Return a list of recent transactions for the given API token.

    In production this would contact the brokerage REST API. For the test
    environment we simply return a fixed set of transactions when the special
    ``demo-token`` is used.

    Each transaction dictionary contains ``symbol``, ``quantity``, ``price``,
    ``type`` and ``timestamp`` keys.
    """
    if api_token == "demo-token":
        return [
            {
                "symbol": "AAA",
                "quantity": 1,
                "price": 95,
                "type": "BUY",
                "timestamp": "2023-01-01",
            },
            {
                "symbol": "BBB",
                "quantity": 1,
                "price": 120,
                "type": "BUY",
                "timestamp": "2023-01-02",
            },
        ]
    return []
