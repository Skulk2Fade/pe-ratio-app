import re
from typing import Any

from .utils import get_historical_prices


def backtest_custom_rule(rule: str, days: int = 30) -> list[dict[str, Any]]:
    """Evaluate a custom rule over historical data.

    Returns a list of dictionaries with ``date`` and ``result`` keys.
    ``days`` controls how many days are tested counting back from the
    most recent historical record.
    """

    # Extract symbols and maximum change window from the rule
    symbol_pattern = re.compile(r"(?:price|change)\(\s*['\"]([^'\"]+)['\"]")
    change_pattern = re.compile(r"change\(\s*['\"][^'\"]+['\"],\s*(\d+)\s*\)")

    symbols = set(symbol_pattern.findall(rule))
    max_days = 0
    for m in change_pattern.findall(rule):
        try:
            max_days = max(max_days, int(m))
        except ValueError:
            pass

    if not symbols:
        return []

    history: dict[str, tuple[list[str], list[float]]] = {}
    for sym in symbols:
        dates, prices = get_historical_prices(sym, days=days + max_days)
        history[sym] = (dates, prices)

    if not history:
        return []

    min_len = min(len(p[1]) for p in history.values())
    results: list[dict[str, Any]] = []

    for idx in range(max_days, min(max_days + days, min_len)):
        def price_fn(symbol: str) -> float | None:
            ds, ps = history.get(symbol, ([], []))
            if idx < len(ps):
                return ps[idx]
            return None

        def change_fn(symbol: str, window: int) -> float | None:
            ds, ps = history.get(symbol, ([], []))
            if idx < len(ps) and idx - window >= 0:
                start = ps[idx - window]
                end = ps[idx]
                if start and end:
                    try:
                        return round((end - start) / start * 100, 2)
                    except Exception:
                        return None
            return None

        try:
            result = bool(eval(rule, {"__builtins__": {}}, {"price": price_fn, "change": change_fn}))
        except Exception:
            result = False

        date = next(iter(history.values()))[0][idx] if history else ""
        results.append({"date": date, "result": result})

    return results
