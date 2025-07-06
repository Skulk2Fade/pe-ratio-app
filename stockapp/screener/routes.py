from flask import Blueprint, render_template, request

from ..utils import screen_stocks

screener_bp = Blueprint("screener", __name__)


@screener_bp.route("/screener")
def screener():
    filters = {
        "pe_min": request.args.get("pe_min", type=float),
        "pe_max": request.args.get("pe_max", type=float),
        "peg_min": request.args.get("peg_min", type=float),
        "peg_max": request.args.get("peg_max", type=float),
        "yield_min": request.args.get("yield_min", type=float),
        "sector": request.args.get("sector", type=str),
    }
    if any(v is not None for v in filters.values()):
        results = screen_stocks(**filters)
    else:
        results = []
    return render_template("screener.html", results=results)
