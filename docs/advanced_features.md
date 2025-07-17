# Advanced Features

This page covers optional functionality that can be enabled in MarketMinder.

## Two-Factor Authentication

Users may secure their accounts with time-based one-time passwords (TOTP).
After enabling 2FA in the settings page they will be prompted for the
6‑digit code from their authenticator app after entering their username and
password.

## Background Tasks with Celery

Scheduled checks of watchlists are handled by Celery.  Run a worker alongside
the Flask application:

```bash
celery -A stockapp.tasks.celery worker -B --loglevel=info
```

Configure the broker and result backend using `CELERY_BROKER_URL` and
`CELERY_RESULT_BACKEND`.  `REDIS_URL` may be set to enable API response
caching.
The schedules for periodic tasks can also be overridden by setting
`CHECK_WATCHLISTS_CRON`, `SEND_TREND_SUMMARIES_CRON`, `SYNC_BROKERAGE_CRON`,
`CHECK_DIVIDENDS_CRON` and `CLEANUP_OLD_DATA_CRON` to cron strings.
Notification emails and SMS messages are queued through Celery so failed
deliveries are automatically retried.

## SMS Notifications

If the `TWILIO_SID`, `TWILIO_TOKEN` and `TWILIO_FROM` variables are provided,
the app can send SMS copies of alert emails.  Enable SMS alerts from the
Settings page after adding a phone number.

## WebSocket Streaming

The price feed supports a WebSocket endpoint at `/ws/price`. Clients send the
desired ticker symbol after connecting and receive periodic JSON updates. This
opens the door for real-time push notifications in the future.

Set `REALTIME_PROVIDER` to `yfinance` to fetch updates from Yahoo Finance
instead of Financial Modeling Prep. Use `PRICE_STREAM_INTERVAL` to control how
often updates are pushed to connected clients. Enable `ASYNC_REALTIME` to
perform these requests asynchronously for lower latency.

## Account Verification and Password Reset

After signing up the application sends a verification email containing a link to activate the account.
Users must verify their address before logging in. Verification links expire after 24 hours.
Password reset emails allow choosing a new password and remain valid for one hour.

## Custom P/E Thresholds

Each watchlist entry can override the default P/E ratio threshold. Alerts and warnings will use
the per-stock value if provided.

## Custom Alert Rules

Advanced users may define alert expressions using simple functions like
`price()` and `change()`. Navigate to the **Custom Rules** page and add a rule
such as `change('AAPL', 7) > 5` to be notified when Apple rises more than five
percent over seven days. Expressions evaluate in a restricted context and can
reference multiple tickers for cross‑asset comparisons.

## Additional Metrics

Alongside the standard P/E ratio the app displays:

* **Forward P/E** – estimated using the latest EPS growth data
* **PEG ratio** – P/E divided by the earnings growth rate
* **Price-to-Sales (P/S) ratio** – retrieved from Financial Modeling Prep
* **Enterprise Value/EBITDA** – valuation considering debt and equity financing
* **Price-to-Free-Cash-Flow (P/FCF) ratio** – valuation using free cash flow per share
* **Dividend Payout Ratio** – percentage of earnings distributed as dividends
* **Current Ratio** – current assets divided by current liabilities
* **MACD and Bollinger Bands** – extra technical indicators for chart analysis
* **Enhanced Charting** – candlestick views with optional overlays

These metrics also appear in exported CSV/PDF/XLSX/JSON files.

## Portfolio Import and Export

The portfolio page supports importing and exporting holdings to CSV, XLSX or JSON formats.
A diversification analyzer highlights concentration risk using metrics like Beta and Sharpe ratio.
An optimizer suggests asset weights that maximize the Sharpe ratio using recent price data.
Holdings can also be synced from a brokerage via OAuth when supported.

## Social Features

Public watchlists let you share ideas with other traders and follow interesting portfolios.
Check the **Leaderboard** to see which users have the most followers.

## Finance Calculators

Quick calculators are available at the `/calc/` routes for interest, compound growth, loan payments and WACC.

## Viewing Alerts

Triggered alerts are saved in the database. After logging in click the *Alerts* link to review them or clear old entries.

Old alerts and historical price records can build up over time. A scheduled task cleans up data older than 30 days. Control the timing with the `CLEANUP_OLD_DATA_CRON` variable.

## Historical Trend Notifications

MarketMinder can email weekly summaries of portfolio and watchlist changes.
Opt in from the Settings page. The Celery scheduler sends the summary each morning at 8&nbsp;AM by default.

## Progressive Web App

A small service worker enables offline caching of static assets so the app behaves like a Progressive Web App.
Mobile friendly styles and a dark theme are included. Browsers can subscribe to push notifications if VAPID keys
are configured.

## Frontend Assets

Bootstrap and Plotly are managed locally. Run `npm ci && npm run build` once after cloning to populate
`static/vendor/` so the service worker can cache the assets using the versions pinned in `package.json`.

## Localization

User language preferences are respected using **Flask-Babel**. Translations live in the `translations/` directory.
After editing `.po` files run `pybabel compile -d translations` to generate the binary `.mo` files.
