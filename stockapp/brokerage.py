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
