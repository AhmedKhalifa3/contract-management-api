# Contract & Document Management API

Backend service for managing business contracts — metadata, lifecycle status,
renewal history, and reporting. Built as a portfolio piece demonstrating
Flask/PostgreSQL backend engineering.

## Architecture decisions

- **App factory pattern** (`app/create_app()`) instead of a global `Flask(__name__)`
  instance — lets tests spin up isolated app/DB instances per test run.
- **UUID primary keys**, not autoincrement integers — avoids exposing
  sequential/guessable IDs in a REST API.
- **Pydantic schemas kept separate from SQLAlchemy models** — models describe
  the DB shape, schemas describe the API contract. Keeps request validation
  and response serialization independent of storage schema.
- **Service layer** sits between routes and models — business logic (status
  transitions, expiring-soon detection, report aggregation) lives in
  `app/services/`, not scattered across route handlers.
- **`category` is a plain indexed string**, validated at the Pydantic layer,
  not a Postgres `ENUM` — changing the allowed category list is a code change
  + deploy, not a DB migration (`ALTER TYPE ... ADD VALUE` is awkward inside
  transactions). `status` *is* a Postgres enum since its values are fixed
  lifecycle states, not a business-configurable list.
- **Local dev DB runs on host port 5433**, not 5432 — this machine already had
  a native Postgres instance bound to 5432.
- **Status changes go through a dedicated `/transition` action endpoint**, not
  the generic PATCH — PATCH edits plain attributes, transitions are validated
  against an explicit state machine (`app/services/status_service.py`) so
  illegal jumps like `draft -> expired` are rejected with `400`, not silently
  written.
- **`expiring` is a stored status, not computed on every read** — a sweep
  endpoint (`POST /expiring-soon/sweep`) bulk-transitions contracts crossing
  the threshold, meant to be hit by a scheduled job in production. Read-only
  detection is available separately via `GET /expiring-soon` without mutating
  anything, useful for reporting before/without running the sweep.

## Data model

- **Contract** — `id, title, counterparty, value, start_date, end_date,
  status, category, created_at, updated_at`. `status` is one of
  `draft, active, expiring, expired, renewed`.
- **RenewalHistory** — audit trail of renewals, one row per renewal event
  (`contract_id, previous_end_date, new_end_date, renewed_at, notes`).
- **Document** — attachment metadata only, not file bytes
  (`contract_id, filename, storage_path, content_type, size_bytes, uploaded_at`).

## Local setup

Requires Docker and Python 3.12+.

```bash
# 1. start Postgres (dev DB on host port 5433, test DB created automatically)
docker compose up -d

# 2. python env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. env vars
cp .env.example .env

# 4. run migrations
export FLASK_APP=wsgi.py
flask db upgrade

# 5. run the app
flask run
```

## API

All endpoints under `/api/contracts`, JSON in/out.

| Method | Path                  | Description                              |
|--------|-----------------------|-------------------------------------------|
| POST   | `/api/contracts`      | Create a contract (defaults to `draft`)  |
| GET    | `/api/contracts`      | List, filter by `?status=`/`?category=`, paginate via `?page=`/`?per_page=` |
| GET    | `/api/contracts/<id>` | Retrieve one                             |
| PATCH  | `/api/contracts/<id>` | Partial update                           |
| DELETE | `/api/contracts/<id>` | Delete                                   |
| POST   | `/api/contracts/<id>/transition` | Move to a new status, validated against the state machine below |
| POST   | `/api/contracts/<id>/renew`      | Extend `end_date`, logs a `RenewalHistory` row, sets status to `renewed` |
| GET    | `/api/contracts/expiring-soon`   | Read-only: active contracts with `end_date` within `?days=` (default 30) |
| POST   | `/api/contracts/expiring-soon/sweep` | Bulk-transition qualifying active contracts to `expiring` |
| POST   | `/api/contracts/expired/sweep`   | Bulk-transition past-due active/expiring contracts to `expired` |

Status state machine:

```
draft    -> active
active   -> expiring, renewed
expiring -> expired, renewed
expired  -> renewed
renewed  -> active
```

Validation errors return `400` with `{"error": "validation_error", ...}`.
Missing resources return `404` with `{"error": "not_found", ...}`.

Run tests: `pytest` (needs `TEST_DATABASE_URL` env var or the docker-compose
default; test DB is created automatically alongside the dev DB).

## Project status

- [x] Data model + migrations (Contract, RenewalHistory, Document)
- [x] CRUD REST API + Pydantic schemas
- [x] Status transition business logic
- [ ] Pandas reporting/export endpoint
- [ ] Full Docker Compose (app + db)
- [ ] Sentry error tracking
- [ ] Structured logging → Elasticsearch/Kibana
- [ ] Prometheus + Grafana metrics
- [ ] AWS deployment + CI
