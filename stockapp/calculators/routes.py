from flask import Blueprint, render_template, request

calc_bp = Blueprint('calc', __name__, url_prefix='/calc')

@calc_bp.route('/interest', methods=['GET', 'POST'])
def interest():
    interest_amount = interest_rate = interest_result = None
    error_message = None
    if request.method == 'POST':
        try:
            interest_amount = float(request.form.get('amount', 0))
            interest_rate = float(request.form.get('rate', 0))
            interest_result = round(interest_amount * interest_rate / 100, 2)
        except ValueError:
            error_message = 'Invalid amount or interest rate.'
    return render_template('interest.html', interest_amount=interest_amount,
                           interest_rate=interest_rate,
                           interest_result=interest_result,
                           error_message=error_message)

@calc_bp.route('/compound', methods=['GET', 'POST'])
def compound():
    comp_principal = comp_rate = comp_years = comp_freq = comp_result = None
    error_message = None
    if request.method == 'POST':
        try:
            comp_principal = float(request.form.get('principal', 0))
            comp_rate = float(request.form.get('rate', 0))
            comp_years = float(request.form.get('years', 0))
            comp_freq = int(request.form.get('frequency', 1))
            comp_result = round(comp_principal * (1 + (comp_rate / 100) / comp_freq) ** (comp_freq * comp_years), 2)
        except ValueError:
            error_message = 'Invalid input for compound interest.'
    return render_template('compound.html', comp_principal=comp_principal,
                           comp_rate=comp_rate, comp_years=comp_years,
                           comp_freq=comp_freq, comp_result=comp_result,
                           error_message=error_message)

@calc_bp.route('/loan', methods=['GET', 'POST'])
def loan():
    loan_amount = loan_rate = loan_years = None
    loan_result = None
    error_message = None
    if request.method == 'POST':
        try:
            loan_amount = float(request.form.get('loan_amount', 0))
            loan_rate = float(request.form.get('loan_rate', 0))
            loan_years = float(request.form.get('loan_years', 0))
            monthly_rate = loan_rate / 100 / 12
            term_months = int(loan_years * 12)
            if monthly_rate == 0:
                monthly_payment = loan_amount / term_months
            else:
                monthly_payment = loan_amount * monthly_rate / (1 - (1 + monthly_rate) ** (-term_months))
            total_payment = monthly_payment * term_months
            total_interest = total_payment - loan_amount
            balance = loan_amount
            schedule = []
            for i in range(1, term_months + 1):
                interest_paid = balance * monthly_rate
                principal_paid = monthly_payment - interest_paid
                balance -= principal_paid
                schedule.append({
                    'month': i,
                    'payment': round(monthly_payment, 2),
                    'interest': round(interest_paid, 2),
                    'principal': round(principal_paid, 2),
                    'balance': round(max(balance, 0), 2),
                })
            loan_result = {
                'monthly_payment': round(monthly_payment, 2),
                'total_interest': round(total_interest, 2),
                'schedule': schedule,
            }
        except ValueError:
            error_message = 'Invalid input for loan calculator.'
    return render_template('loan.html', loan_amount=loan_amount, loan_rate=loan_rate,
                           loan_years=loan_years, loan_result=loan_result,
                           error_message=error_message)
