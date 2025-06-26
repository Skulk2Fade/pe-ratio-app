# MarketMinder

This Flask application calculates P/E ratios and stores user data using SQLAlchemy. Authentication is handled via **Flask-Login**.

## Database Configuration

The app uses SQLite by default for local development. To deploy to platforms like Render with PostgreSQL, set a `DATABASE_URL` environment variable. When `DATABASE_URL` starts with `postgres://` it will automatically be converted to the `postgresql://` format expected by SQLAlchemy.

Example:

```bash
export DATABASE_URL="postgres://user:password@hostname:5432/dbname"
```

If `DATABASE_URL` is not provided, a local `app.db` SQLite file will be used.

## Environment Variables

Several settings are loaded from environment variables so you do not need to
store secrets in the source code:

* `SECRET_KEY` &ndash; Flask session secret.
* `API_KEY` &ndash; Financial Modeling Prep API key (required).
* `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` &ndash; SMTP
  credentials for sending alert emails.
* `FLASK_DEBUG` &ndash; Set to `1` to enable Flask debug mode (defaults to `0`).

Example:

```bash
export SECRET_KEY="supersecret"
export API_KEY="your_fmp_api_key"
export SMTP_SERVER="smtp.example.com"
export SMTP_PORT=587
export SMTP_USERNAME="user@example.com"
export SMTP_PASSWORD="password"
export FLASK_DEBUG=1
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

The codebase is organized as a Flask package named `stockapp`. The main `app.py` file simply creates the Flask app from this package.


```bash
python app.py
```

### Default Login

On startup the app creates a verified user if it doesn't already exist. The
default credentials are:

* Username: `testuser`
* Password: `testpass`

You can override these by setting the `DEFAULT_USERNAME` and `DEFAULT_PASSWORD`
environment variables before running the app.

## Account Verification and Password Reset

After signing up the app sends a verification email containing a link to
activate your account. Users must verify their email address before being able
to log in. If you forget your password you can request a reset link from the
login page which will allow you to choose a new password.

## Custom P/E Thresholds

When adding tickers to your watchlist you can specify a custom P/E ratio
threshold for each stock. Alerts and warnings use this per-stock value. If no
threshold is provided the default of 30 is used.

## Additional Metrics

Alongside the standard P/E ratio the app now fetches and displays:

* **Forward P/E** – estimated using the latest EPS growth data.
* **PEG ratio** – P/E divided by the earnings growth rate.
* **Price-to-Sales (P/S) ratio** – retrieved from Financial Modeling Prep.
* **Enterprise Value/EBITDA** – helps assess valuation considering both debt and equity financing.
* **Price-to-Free-Cash-Flow (P/FCF) ratio** – calculates valuation using free cash flow per share.
* **Dividend Payout Ratio** – shows what percentage of earnings are distributed as dividends.
* **Current Ratio** – current assets divided by current liabilities, indicating short-term liquidity.

These extra metrics appear on the main page and in exported CSV/PDF files.

## Portfolio CSV Import/Export

Within the Portfolio page you can now export all holdings to a CSV file or
import a file to quickly populate your portfolio. The CSV format uses the
columns `Symbol`, `Quantity` and `Price Paid`.

* **Portfolio Diversification Analyzer** – automatically analyzes sector allocations to highlight concentration risk.

## Finance Calculators

The main page also hosts several quick calculators:

* Simple interest
* Compound interest
* **Loan/Mortgage payment** – computes monthly payment, total interest and shows a full amortization schedule.

## Scheduled Alerts

Alert emails are sent on a schedule using **APScheduler**. Each user can
configure how often their watchlist should be checked. Visit the *Settings*
page after logging in to choose an alert frequency in hours. The default is 24
hours. The background job runs hourly and only sends alerts when your selected
interval has elapsed.

## Viewing Alerts

Triggered alerts are saved in the database. After logging in click the *Alerts* link to review them. The page also lets you clear old alerts.

## Progressive Web App Notes

The app registers a small service worker so it can behave like a Progressive
Web App. Only static assets are cached. The main pages are always fetched from
the server so that dynamic CSRF tokens stay valid.

