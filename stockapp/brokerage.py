"""Simple brokerage API client stub for tests.

This module provides a function to retrieve a user's holdings from a
brokerage service. In the real application this would make HTTP requests
to the brokerage provider, but for the test environment we simply return
static data when a special token is used.
"""

import os
import importlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from .utils import session

# Determine which brokerage integration to use. The default "basic"
# implementation uses the simple stub defined in this module. Setting the
# ``BROKERAGE_PROVIDER`` environment variable to ``"plaid"`` will delegate to
# the Plaid stub in ``stockapp.plaid``.
BROKERAGE_PROVIDER = os.environ.get("BROKERAGE_PROVIDER", "basic").lower()
provider = None
if BROKERAGE_PROVIDER != "basic":
    try:
        provider = importlib.import_module(f".{BROKERAGE_PROVIDER}", __package__)
    except Exception:  # pragma: no cover - unknown provider
        provider = None

BROKERAGE_CLIENT_ID = os.environ.get("BROKERAGE_CLIENT_ID")
BROKERAGE_CLIENT_SECRET = os.environ.get("BROKERAGE_CLIENT_SECRET")
BROKERAGE_AUTH_URL = os.environ.get("BROKERAGE_AUTH_URL")
BROKERAGE_TOKEN_URL = os.environ.get("BROKERAGE_TOKEN_URL")
BROKERAGE_API_BASE = os.environ.get("BROKERAGE_API_BASE")


def generate_state() -> str:
    """Return a random string for OAuth state parameter."""
    return os.urandom(8).hex()


def get_authorization_url(state: str) -> str:
    """Return the authorization URL for the brokerage OAuth flow."""
    if not BROKERAGE_AUTH_URL or not BROKERAGE_CLIENT_ID:
        return "#"
    return (
        f"{BROKERAGE_AUTH_URL}?response_type=code&client_id="
        f"{BROKERAGE_CLIENT_ID}&state={state}"
    )


def exchange_code_for_token(code: str) -> Optional[Dict[str, object]]:
    """Exchange an authorization code for an access token."""
    if (
        not BROKERAGE_TOKEN_URL
        or not BROKERAGE_CLIENT_ID
        or not BROKERAGE_CLIENT_SECRET
    ):
        return None
    try:
        resp = session.post(
            BROKERAGE_TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": BROKERAGE_CLIENT_ID,
                "client_secret": BROKERAGE_CLIENT_SECRET,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, object]]:
    """Refresh an expired access token."""
    if (
        not BROKERAGE_TOKEN_URL
        or not BROKERAGE_CLIENT_ID
        or not BROKERAGE_CLIENT_SECRET
    ):
        return None
    try:
        resp = session.post(
            BROKERAGE_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": BROKERAGE_CLIENT_ID,
                "client_secret": BROKERAGE_CLIENT_SECRET,
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def token_expiry_time(expires_in: int) -> datetime:
    """Return the datetime when a token will expire."""
    return datetime.utcnow() + timedelta(seconds=expires_in)


def _api_get(path: str, access_token: str) -> Optional[Dict[str, object]]:
    if not BROKERAGE_API_BASE:
        return None
    try:
        resp = session.get(
            f"{BROKERAGE_API_BASE.rstrip('/')}/{path.lstrip('/')}",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


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
    if provider and hasattr(provider, "get_holdings"):
        return provider.get_holdings(api_token)

    if api_token == "demo-token":
        return [
            {"symbol": "AAA", "quantity": 2, "price_paid": 90},
            {"symbol": "BBB", "quantity": 1, "price_paid": 110},
        ]
    data = _api_get("holdings", api_token)
    if isinstance(data, list):
        return [
            {
                "symbol": h.get("symbol", "").upper(),
                "quantity": float(h.get("quantity", 0)),
                "price_paid": float(h.get("price_paid", 0)),
            }
            for h in data
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
    if provider and hasattr(provider, "get_transactions"):
        return provider.get_transactions(api_token)

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
    data = _api_get("transactions", api_token)
    if isinstance(data, list):
        return data
    return []


def get_account_balance(api_token: str) -> Optional[float]:
    """Return the account cash balance for the given token."""
    if provider and hasattr(provider, "get_account_balance"):
        return provider.get_account_balance(api_token)

    if api_token == "demo-token":
        return 10000.0
    data = _api_get("balance", api_token)
    if isinstance(data, dict):
        try:
            return float(data.get("cash", 0))
        except Exception:
            return None
    return None
