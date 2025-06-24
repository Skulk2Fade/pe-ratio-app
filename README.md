# Stock Analysis App

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

Example:

```bash
export SECRET_KEY="supersecret"
export API_KEY="your_fmp_api_key"
export SMTP_SERVER="smtp.example.com"
export SMTP_PORT=587
export SMTP_USERNAME="user@example.com"
export SMTP_PASSWORD="password"
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
python app.py
```

The Flask code is now organized as a package under `app/` using Blueprints.
The `app.py` file simply creates the application via `create_app()` and starts
the server.

## Custom P/E Thresholds

When adding tickers to your watchlist you can specify a custom P/E ratio
threshold for each stock. Alerts and warnings use this per-stock value. If no
threshold is provided the default of 30 is used.

## Scheduled Alerts

Alert emails are sent on a schedule using **APScheduler**. Each user can
configure how often their watchlist should be checked. Visit the *Settings*
page after logging in to choose an alert frequency in hours. The default is 24
hours. The background job runs hourly and only sends alerts when your selected
interval has elapsed.

