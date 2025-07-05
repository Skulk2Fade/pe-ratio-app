from flask import Blueprint, render_template, request

calc_bp = Blueprint("calc", __name__, url_prefix="/calc")


@calc_bp.route("/interest", methods=["GET", "POST"])
def interest():
    interest_amount = interest_rate = interest_result = None
    error_message = None
    if request.method == "POST":
        try:
            interest_amount = float(request.form.get("amount", 0))
            interest_rate = float(request.form.get("rate", 0))
            interest_result = round(interest_amount * interest_rate / 100, 2)
        except ValueError:
            error_message = "Invalid amount or interest rate."
    return render_template(
        "interest.html",
        interest_amount=interest_amount,
        interest_rate=interest_rate,
        interest_result=interest_result,
        error_message=error_message,
    )


@calc_bp.route("/compound", methods=["GET", "POST"])
def compound():
    comp_principal = comp_rate = comp_years = comp_freq = comp_result = None
    error_message = None
    if request.method == "POST":
        try:
            comp_principal = float(request.form.get("principal", 0))
            comp_rate = float(request.form.get("rate", 0))
            comp_years = float(request.form.get("years", 0))
            comp_freq = int(request.form.get("frequency", 1))
            comp_result = round(
                comp_principal
                * (1 + (comp_rate / 100) / comp_freq) ** (comp_freq * comp_years),
                2,
            )
        except ValueError:
            error_message = "Invalid input for compound interest."
    return render_template(
        "compound.html",
        comp_principal=comp_principal,
        comp_rate=comp_rate,
        comp_years=comp_years,
        comp_freq=comp_freq,
        comp_result=comp_result,
        error_message=error_message,
    )


@calc_bp.route("/loan", methods=["GET", "POST"])
def loan():
    loan_amount = loan_rate = loan_years = None
    loan_result = None
    error_message = None
    if request.method == "POST":
        try:
            loan_amount = float(request.form.get("loan_amount", 0))
            loan_rate = float(request.form.get("loan_rate", 0))
            loan_years = float(request.form.get("loan_years", 0))
            monthly_rate = loan_rate / 100 / 12
            term_months = int(loan_years * 12)
            if monthly_rate == 0:
                monthly_payment = loan_amount / term_months
            else:
                monthly_payment = (
                    loan_amount
                    * monthly_rate
                    / (1 - (1 + monthly_rate) ** (-term_months))
                )
            total_payment = monthly_payment * term_months
            total_interest = total_payment - loan_amount
            balance = loan_amount
            schedule = []
            for i in range(1, term_months + 1):
                interest_paid = balance * monthly_rate
                principal_paid = monthly_payment - interest_paid
                balance -= principal_paid
                schedule.append(
                    {
                        "month": i,
                        "payment": round(monthly_payment, 2),
                        "interest": round(interest_paid, 2),
                        "principal": round(principal_paid, 2),
                        "balance": round(max(balance, 0), 2),
                    }
                )
            loan_result = {
                "monthly_payment": round(monthly_payment, 2),
                "total_interest": round(total_interest, 2),
                "schedule": schedule,
            }
        except ValueError:
            error_message = "Invalid input for loan calculator."
    return render_template(
        "loan.html",
        loan_amount=loan_amount,
        loan_rate=loan_rate,
        loan_years=loan_years,
        loan_result=loan_result,
        error_message=error_message,
    )


@calc_bp.route("/roi", methods=["GET", "POST"])
def roi():
    initial = final = None
    roi_result = None
    error_message = None
    if request.method == "POST":
        try:
            initial = float(request.form.get("initial", 0))
            final = float(request.form.get("final", 0))
            if initial != 0:
                roi_result = round(((final - initial) / initial) * 100, 2)
            else:
                error_message = "Initial investment cannot be zero."
        except ValueError:
            error_message = "Invalid input for ROI calculator."
    return render_template(
        "roi.html",
        initial=initial,
        final=final,
        roi_result=roi_result,
        error_message=error_message,
    )


@calc_bp.route("/dcf", methods=["GET", "POST"])
def dcf():
    cash_flow = rate = years = terminal_value = None
    dcf_result = None
    error_message = None
    if request.method == "POST":
        try:
            cash_flow = float(request.form.get("cash_flow", 0))
            rate = float(request.form.get("discount_rate", 0))
            years = int(request.form.get("years", 0))
            terminal_value = float(request.form.get("terminal_value", 0))
            discount = rate / 100
            total = 0
            for i in range(1, years + 1):
                total += cash_flow / (1 + discount) ** i
            total += terminal_value / (1 + discount) ** years
            dcf_result = round(total, 2)
        except ValueError:
            error_message = "Invalid input for DCF calculator."
    return render_template(
        "dcf.html",
        cash_flow=cash_flow,
        discount_rate=rate,
        years=years,
        terminal_value=terminal_value,
        dcf_result=dcf_result,
        error_message=error_message,
    )


@calc_bp.route("/tax", methods=["GET", "POST"])
def tax():
    purchase_price = sale_price = quantity = tax_rate = None
    tax_result = None
    error_message = None
    if request.method == "POST":
        try:
            purchase_price = float(request.form.get("purchase_price", 0))
            sale_price = float(request.form.get("sale_price", 0))
            quantity = float(request.form.get("quantity", 0))
            tax_rate = float(request.form.get("tax_rate", 0))
            gain = (sale_price - purchase_price) * quantity
            tax_due = gain * (tax_rate / 100)
            tax_result = {
                "gain": round(gain, 2),
                "tax_due": round(tax_due, 2),
            }
        except ValueError:
            error_message = "Invalid input for tax calculator."
    return render_template(
        "tax.html",
        purchase_price=purchase_price,
        sale_price=sale_price,
        quantity=quantity,
        tax_rate=tax_rate,
        tax_result=tax_result,
        error_message=error_message,
    )


@calc_bp.route("/wacc", methods=["GET", "POST"])
def wacc():
    """Weighted Average Cost of Capital calculator."""
    equity = debt = cost_equity = cost_debt = tax_rate = None
    wacc_result = None
    error_message = None
    if request.method == "POST":
        try:
            equity = float(request.form.get("equity", 0))
            debt = float(request.form.get("debt", 0))
            cost_equity = float(request.form.get("cost_equity", 0))
            cost_debt = float(request.form.get("cost_debt", 0))
            tax_rate = float(request.form.get("tax_rate", 0))
            total = equity + debt
            if total > 0:
                wacc_result = round(
                    (equity / total) * cost_equity
                    + (debt / total) * cost_debt * (1 - tax_rate / 100),
                    2,
                )
            else:
                error_message = "Equity and debt cannot both be zero."
        except ValueError:
            error_message = "Invalid input for WACC calculator."
    return render_template(
        "wacc.html",
        equity=equity,
        debt=debt,
        cost_equity=cost_equity,
        cost_debt=cost_debt,
        tax_rate=tax_rate,
        wacc_result=wacc_result,
        error_message=error_message,
    )
