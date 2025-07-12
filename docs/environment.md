# Environment Variables

The application reads most configuration values from environment variables. A `.env.example` file is provided with common options.
Copy it to `.env` and adjust as needed. When starting the app these variables are loaded automatically by **python-dotenv**.

## Common Settings

* `SECRET_KEY` &ndash; Flask session secret. **Required in production.**
* `API_KEY` &ndash; Financial Modeling Prep API key. If omitted, placeholder data is used.
* `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` &ndash; Credentials for sending email alerts.
* `FLASK_DEBUG` &ndash; Set to `1` to enable debug mode (defaults to `0`).
* `REDIS_URL` &ndash; Optional Redis connection string for caching API responses.
* `CELERY_BROKER_URL` &ndash; Message broker for background tasks (defaults to a local Redis instance).
* `CELERY_RESULT_BACKEND` &ndash; Storage for Celery task results (defaults to the same Redis instance).
* `CHECK_WATCHLISTS_CRON`, `SEND_TREND_SUMMARIES_CRON`, `SYNC_BROKERAGE_CRON`, `CHECK_DIVIDENDS_CRON`, `CLEANUP_OLD_DATA_CRON` &ndash; Cron schedules for background tasks.
* `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM` &ndash; Optional credentials for SMS notifications.

Example `.env` snippet:

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
export CHECK_WATCHLISTS_CRON="0 * * * *"
export SEND_TREND_SUMMARIES_CRON="0 8 * * *"
export SYNC_BROKERAGE_CRON="0 6 * * *"
export CHECK_DIVIDENDS_CRON="0 9 * * *"
export CLEANUP_OLD_DATA_CRON="0 3 * * *"
export TWILIO_SID="your_twilio_sid"
export TWILIO_TOKEN="your_twilio_token"
export TWILIO_FROM="+15551234567"
```
