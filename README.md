# Home Depot Price & Inventory Intelligence Tracker

## Stage 1: manual price tracking

This Flask application provides a password-protected dashboard for manually entered products. Add a name and a SKU, Internet number, model number, or Home Depot URL; enter or correct the original and current prices; edit, pause, resume, or delete products; and search, sort, and filter the dashboard. Deleting a product also deletes its history.

Each changed, known price is appended to price history. The original price is not automatically replaced by a later price. Current and maximum discounts are calculated from the manually maintained original price and current or lowest recorded price; correcting the original price therefore recalculates both. Savings and discounts are floored at zero. A missing price is unknown, not zero. Separate sale cycles are recorded when a known price moves below the original and later returns to or exceeds it. These are manual observations, not proof of a Home Depot clearance.

**No Home Depot data is retrieved in Stage 1.** There is no mock or live feed, store lookup, inventory tracking UI, background monitoring, alerts, charts, configurable thresholds, or automatic clearance scoring yet. Pause is saved for a future monitoring service; it does not schedule or stop a task today. The database includes foundational tables for later stages, not implementations of those features. Bootstrap is loaded from a public CDN; the app remains usable without the CDN but will not have Bootstrap styling.

## Installation and local use

Requires Python 3.10+ and pip. From the project root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Flask, Flask-SQLAlchemy, Flask-WTF, and pytest are listed in `requirements.txt`. Create a random session secret and a password hash (the password prompt is hidden and is not placed in shell history):

```sh
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
python -c 'from app import hash_password; hash_password()'
```

Copy the printed hash into an environment variable, quoting it so shell metacharacters are not expanded:

```sh
export APP_PASSWORD_HASH='paste-the-generated-hash-here'
python -m flask --app wsgi init-db
python -m flask --app wsgi run
```

Open <http://127.0.0.1:5000> and sign in. Keep `SECRET_KEY` and `APP_PASSWORD_HASH` stable across restarts: changing the secret invalidates sessions. Never commit them or put passwords in source control. The default database is `instance/tracker.sqlite`. `init-db` creates missing tables, but does not migrate an existing schema.

Optional environment variables:

* `DATABASE_URL`: SQLAlchemy database URL. SQLite is the default. PostgreSQL requires an installed compatible driver and an appropriate URL such as `postgresql+psycopg://...`; this has not yet been deployment-tested.
* `SESSION_COOKIE_SECURE=true`: send session cookies only over HTTPS. Enable this behind HTTPS in any deployment.

## Testing

```sh
python -m pytest -q
```

Tests cover discounts, historical maximums, sale cycles, product management, validation, authentication, and CSRF. They do not contact Home Depot.

## Deployment, monitoring, and backups

Stage 1 is intended for local use or a trusted private network, **not an Internet-facing production deployment**. It has a single shared password and CSRF protection, but does not yet include login rate limiting, account management, operational hardening, migrations, or a production server configuration. Before exposing it, add those controls, use HTTPS with secure cookies, protect environment variables, and run a production WSGI server behind a properly configured reverse proxy. The Flask development server is not a production server.

There is no scheduler to configure in Stage 1. Closing the browser does not delete saved data, but no prices or inventory are checked in the background. Email and provider credentials are not used.

For SQLite, create a consistent backup with Python's SQLite backup API (choose a protected location outside the repository):

```sh
python -c 'import sqlite3; src=sqlite3.connect("instance/tracker.sqlite"); dst=sqlite3.connect("/secure/path/tracker-backup.sqlite"); src.backup(dst); dst.close(); src.close()'
```

To restore, stop all application processes, preserve the current database, copy the backup over `instance/tracker.sqlite`, and restart. For PostgreSQL use the database's native backup and restore tools instead. Test restores and restrict access to backups.

## Next stage

Stage 2 should investigate official or authorized Home Depot data sources and implement an interchangeable provider interface, store search/selection, scheduled price and store-specific inventory observations, and retrieval failure handling. Do not infer zero stock from missing provider data. Stage 3 will add clearance scoring and notifications; Stage 4 charts and settings; Stage 5 hardened deployment and continuous monitoring.

**Exact next step:** identify an authorized product and store-inventory data source and its access terms before implementing a provider.
