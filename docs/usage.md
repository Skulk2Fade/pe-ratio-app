# Usage

This page covers basic setup and workflow for running MarketMinder locally.

## Quickstart

1. Copy `.env.example` to `.env` and edit the values.
2. Install dependencies and build the frontend assets:
   ```bash
   ./scripts/bootstrap.sh
   source venv/bin/activate
   ```
   You may also run `./setup_env.sh` and `npm ci && npm run build` manually to
   use the pinned asset versions.
   Apply the database migrations:
   ```bash
   flask db upgrade
   ```
3. Start the application:
   ```bash
   python app.py
   ```
   For scheduled alerts run a Celery worker. See [advanced_features.md](advanced_features.md) for details.
4. Run the tests with `pytest`.

### Docker Compose

A `docker-compose.yml` file is provided to run the app along with Redis, Celery and PostgreSQL.
Build and start the stack with:

```bash
docker compose up --build
```

The web interface will be available at <http://localhost:5000>.

### Standalone Docker Image

If you prefer running a single container, a `Dockerfile` is provided. Build and
run the image with:

```bash
docker build -t marketminder .
docker run -p 5000:5000 --env-file .env marketminder
```

This uses Gunicorn to serve the application on port 5000.

### Database Configuration

SQLite is used by default for local development. To use PostgreSQL set `DATABASE_URL`.
When the URL begins with `postgres://` it is automatically converted to the `postgresql://`
format expected by SQLAlchemy.

Example:

```bash
export DATABASE_URL="postgres://user:password@hostname:5432/dbname"
```

### Setup Details

If your environment lacks internet access you can create a `wheelhouse/` directory on a machine
with connectivity:

```bash
pip download -d wheelhouse -r requirements.txt
```

Place that directory next to the repository and run:

```bash
./setup_env.sh --offline
```

This installs packages from the local cache.

### Running the Application

The project is organized as a Flask package named `stockapp`. The `app.py` file creates the Flask
application instance. After activating the virtual environment you can start the server with:

```bash
python app.py
```

### Production Configuration

Provide your own Redis instance for Celery in production. Set `CELERY_BROKER_URL` and
`CELERY_RESULT_BACKEND` to the connection string. Assign the same value to `REDIS_URL` if you
would like API caching enabled.

When running with `FLASK_ENV=production` the app requires several environment
variables:

- `SECRET_KEY`
- `DATABASE_URL`
- `TWILIO_SID`, `TWILIO_TOKEN`, `TWILIO_FROM`

See [Secure deployment](deployment.md) for a sample startup snippet.

### Default Login

When `FLASK_ENV=development` a verified user is created automatically if one does not already
exist. The default credentials are `testuser`/`testpass`. Override these by setting
`DEFAULT_USERNAME` and `DEFAULT_PASSWORD`.
