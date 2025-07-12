# Secure Deployment

This guide covers the minimum configuration required to run MarketMinder in production.

## Required Environment Variables

At a minimum the following variables **must** be provided when `FLASK_ENV=production`:

- `SECRET_KEY` – secret used by Flask for sessions
- `DATABASE_URL` – connection string for the production database
- `TWILIO_SID`, `TWILIO_TOKEN` and `TWILIO_FROM` – credentials for SMS alerts

Set these values as environment variables rather than storing them in source control. A sample snippet is shown below:

```bash
export FLASK_ENV=production
export SECRET_KEY="change_me"
export DATABASE_URL="postgresql://user:pass@db-host/dbname"
export TWILIO_SID="ACxxxxxxxx"
export TWILIO_TOKEN="your_auth_token"
export TWILIO_FROM="+15551234567"
```

## Starting the Application

After setting the variables above you can start the server with a WSGI runner such as Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 'stockapp:create_app()'
```

When deploying with Docker or another container system make sure these variables are provided in the runtime environment.
