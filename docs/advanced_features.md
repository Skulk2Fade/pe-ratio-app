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
`CHECK_WATCHLISTS_CRON`, `SEND_TREND_SUMMARIES_CRON`, `SYNC_BROKERAGE_CRON` and
`CHECK_DIVIDENDS_CRON` to cron strings.

## SMS Notifications

If the `TWILIO_SID`, `TWILIO_TOKEN` and `TWILIO_FROM` variables are provided,
the app can send SMS copies of alert emails.  Enable SMS alerts from the
Settings page after adding a phone number.

## WebSocket Streaming

The price feed supports a WebSocket endpoint at `/ws/price`. Clients send the
desired ticker symbol after connecting and receive periodic JSON updates. This
opens the door for real-time push notifications in the future.
