# MarketMinder

This Flask application calculates P/E ratios and stores user data using SQLAlchemy. Authentication is handled via **Flask-Login**.

## Quickstart

1. Copy `.env.example` to `.env` and edit the values.
2. Create the virtual environment and install dependencies:
   ```bash
   ./setup_env.sh
   source venv/bin/activate
   ```
3. Build the frontend assets:
   ```bash
   npm install
   npm run build
   ```
4. Start the application:
   ```bash
   python app.py
   ```
   For scheduled alerts run a Celery worker. See [docs/advanced_features.md](docs/advanced_features.md) for details.
5. Run the tests with `pytest`.

### Docker Compose

A `docker-compose.yml` file is provided to run the app along with Redis, Celery and PostgreSQL. Build and start the stack with:

```bash
docker compose up --build
```

The web interface will be available at http://localhost:5000.

Additional documentation can be found in [docs/advanced_features.md](docs/advanced_features.md) and [docs/contributing.md](docs/contributing.md).
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

* `SECRET_KEY` &ndash; Flask session secret. If omitted, a random key is generated
  at startup. **In production this variable must be set or the app will not start.**
* `API_KEY` &ndash; Financial Modeling Prep API key (required).
* `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` &ndash; SMTP
  credentials for sending alert emails.
* `FLASK_DEBUG` &ndash; Set to `1` to enable Flask debug mode (defaults to `0`).
* `REDIS_URL` &ndash; Optional Redis connection string for caching API responses.
* `CELERY_BROKER_URL` &ndash; Message broker for background tasks (defaults to a local Redis instance).
* `CELERY_RESULT_BACKEND` &ndash; Storage for Celery task results (defaults to the same Redis instance).
* `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM` &ndash; Optional credentials for sending SMS notifications.

You can place these settings in a `.env` file in the project root. They will be
loaded automatically when the app starts thanks to **python-dotenv**. An
`/.env.example` file is provided with common options. Copy it to `.env` and
adjust the values for your environment.

Example:

```bash
export SECRET_KEY="supersecret"
export API_KEY="your_fmp_api_key"
export SMTP_SERVER="smtp.example.com"
export SMTP_PORT=587
export SMTP_USERNAME="user@example.com"
export SMTP_PASSWORD="password"
export FLASK_DEBUG=1
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/0"
export CELERY_RESULT_BACKEND="redis://localhost:6379/0"
export TWILIO_SID="your_twilio_sid"
export TWILIO_TOKEN="your_twilio_token"
export TWILIO_FROM="+15551234567"
```

## Setup

Install dependencies and create a virtual environment by running the helper
script included in the repository:

```bash
./setup_env.sh
source venv/bin/activate
```

The script creates a `venv/` directory in the project root and installs the
packages listed in `requirements.txt`.

If your environment does not have internet access you can install dependencies
from a local **wheelhouse** directory instead. First, on a machine with
connectivity, download the required packages:

```bash
pip download -d wheelhouse -r requirements.txt
```

Copy the generated `wheelhouse/` directory alongside this repository and run:

```bash
./setup_env.sh --offline
```

This tells the setup script to install packages using the local cache so tests
can run without external network access.

Run the application:

The codebase is organized as a Flask package named `stockapp`. The main `app.py` file simply creates the Flask app from this package.


```bash
python app.py
```


### Production Configuration

For production deployments you should provide your own Redis instance and
configure Celery to use it. Set `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`
to the Redis connection string (e.g. `redis://hostname:6379/0`). The same Redis
URL can be assigned to `REDIS_URL` if you want API caching enabled.


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
to log in. Verification links expire after 24 hours. If you forget your password
you can request a reset link from the login page which will allow you to choose
a new password. Password reset links expire after 1 hour.


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
* **MACD and Bollinger Bands** – additional technical indicators for chart analysis.

These extra metrics appear on the main page and in exported CSV/PDF/XLSX/JSON files.

## Portfolio CSV/XLSX/JSON Import/Export

Within the Portfolio page you can now export all holdings to CSV, XLSX or JSON files or
import a file to quickly populate your portfolio. The CSV format uses the
columns `Symbol`, `Quantity` and `Price Paid`.

* **Portfolio Diversification Analyzer** – automatically analyzes sector allocations, asset correlations and overall portfolio volatility to highlight concentration risk. Enhanced metrics like Beta, Sharpe ratio, Value at Risk and Monte Carlo simulations provide deeper risk insights.
* **Brokerage Transaction Sync** – portfolio holdings and recent transactions can now be synchronized from connected brokerage accounts using the new stub API.

## Social Features

Public watchlists let you share ideas with other traders. Visit `/watchlist/public/<username>` to see another user's list. You can also follow portfolios you find interesting. Check out the **Leaderboard** link in the navigation bar to see which users have the most followers.

## Finance Calculators

Several quick calculators are available at their own routes:

* `/calc/interest` – simple interest
* `/calc/compound` – compound interest
* `/calc/loan` – **Loan/Mortgage payment** – computes monthly payment, total interest and shows a full amortization schedule.
* `/calc/wacc` – Weighted Average Cost of Capital

## Viewing Alerts


Triggered alerts are saved in the database. After logging in click the *Alerts* link to review them. The page also lets you clear old alerts.

## Historical Trend Notifications

MarketMinder can email you a brief summary of how your portfolio and watchlist changed over the last week. Opt in from the Settings page by checking **Email Weekly Summary**. The Celery scheduler sends the summary each morning at 8 AM by default.

## Progressive Web App Notes

The app registers a small service worker so it can behave like a Progressive
Web App. Only static assets are cached. The main pages are always fetched from
the server so that dynamic CSRF tokens stay valid.

### WebSocket Price Streaming

Price updates are now pushed over a WebSocket connection. When viewing a
ticker, the browser opens `ws://host/ws/price`, sends the symbol and receives
periodic JSON messages containing the latest price and EPS. This enables future
bidirectional features like push alerts.

### Frontend Assets

Bootstrap and Plotly are now managed locally instead of pulled from a CDN. A
small build script copies the files from `node_modules` into `static/vendor`.
Run the following once after cloning:

```bash
npm install
npm run build
```

This populates the `static/vendor/` directory so the service worker can cache
the assets even when offline.

## Localization

User language preferences are now respected using **Flask-Babel**. Set the
desired language from the Settings page. Translations live in the `translations/`
folder. Only the `.po` files are tracked in git. After editing them run
`pybabel compile -d translations` to generate the binary `.mo` files locally.

