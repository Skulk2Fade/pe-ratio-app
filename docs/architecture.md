# Architecture Overview

This page describes the main components of MarketMinder and how they interact.

```
+----------------+      +--------------------+      +--------------+
| Flask App      | <--> | SQLAlchemy Models  | <--> | Database      |
+----------------+      +--------------------+      +--------------+
        |
        | registers
        v
+----------------+      +-------------+
| Blueprints     |----->| Templates   |
+----------------+      +-------------+
        |
        | triggers
        v
+---------------+       +---------------+
| Celery Worker | <---- | Redis Broker  |
+---------------+       +---------------+
        |
        | schedules
        v
+-----------------+
| Background Jobs |
+-----------------+
```

- **Flask App** – created in `app.py` using `create_app()` from the `stockapp` package.
- **Blueprints** – modular routes for authentication, watchlists, portfolios and more.
- **SQLAlchemy Models** – define users, alerts, stock records and other data structures.
- **Database** – SQLite by default or PostgreSQL in production.
- **Flask-Migrate** – manages versioned database schema changes using Alembic.
- **Celery Worker** – executes scheduled tasks such as watchlist checks and email alerts.
- **Redis Broker** – default message broker for Celery and optional caching layer.

When the application starts it registers all blueprints and initializes the
extensions. Background jobs are scheduled through Celery and stored in the
configured broker. Results and user data are persisted in the database.
