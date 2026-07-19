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
- **Reports reuse `status_service.list_expiring_soon`** rather than
  re-deriving "what counts as expiring soon" independently — one definition
  of that business rule, not two that can drift apart. Pandas is used for
  what it's actually good at (`groupby`/`agg`), not for filtering.
- **JSON output from the reporting endpoints is explicitly sanitized** —
  pandas aggregation produces `numpy.int64`/`numpy.float64` scalars, which
  Flask's default JSON encoder can't serialize at all, and raw `date` objects,
  which it silently renders as RFC-822 strings instead of the ISO format used
  everywhere else in this API. Both are normalized before `jsonify`.
- **One Dockerfile, two run modes** — the image's default `CMD` runs gunicorn
  (what a real deployment would use); docker-compose overrides it with
  `flask run --debug` plus a bind mount, for hot-reload local dev. Same
  image either way, no dev-only Dockerfile to keep in sync.
- **The app container's `DATABASE_URL` points at `db:5432`**, not
  `localhost:5433` — containers reach each other by service name over the
  compose network at the container's own port; the host-remapped `5433` from
  `.env` only means anything from outside Docker. Set explicitly in
  `docker-compose.yml`, not inherited from `.env`.
- **Migrations run automatically on container start** (`docker/entrypoint.sh`
  runs `flask db upgrade` before exec'ing the main process) — convenient for
  a single local instance. Note this doesn't scale to multiple replicas
  without a migration race; a real deployment would run migrations as a
  separate release step instead.
- **Logs are shipped via a shared file, not Docker log/container autodiscovery**
  — the app writes structured JSON to `/var/log/app/app.log` on a named
  volume; Filebeat tails that file directly. The more common
  container-autodiscovery pattern reads from `/var/lib/docker/containers` on
  the host, which is unreliable across different Docker setups (breaks on
  Docker Desktop's VM-backed installs). File-tailing works identically
  everywhere and doesn't need the Docker socket mounted into Filebeat.
- **The `app_logs` volume needs `appuser` ownership set inside the image**
  (`Dockerfile`, before `USER appuser`) — a fresh named volume mounted over
  an empty path is created root-owned by default; Docker only inherits
  ownership from the image if that path already exists there first. Skipping
  this causes a `PermissionError` on container start.
- **Elasticsearch and Kibana run with security disabled** (`xpack.security.enabled=false`)
  — fine for a local single-node dev stack behind no exposed ports beyond
  localhost; a real deployment would need TLS + auth enabled.
- **Metrics are labeled by Flask's route pattern, not the resolved request
  path** (`request.url_rule.rule`, e.g. `/api/contracts/<uuid:contract_id>`)
  — labeling by `request.path` would create a new Prometheus time series per
  contract UUID ever requested, unbounded cardinality that quietly grows
  Prometheus's memory/storage forever. Verified with a test asserting a real
  UUID never appears in `/metrics` output.
- **Grafana's datasource and dashboard are provisioned as files**, not
  clicked together manually — `docker/grafana/provisioning/`. Reproducible,
  and the dashboard is there immediately on first `docker compose up`.
- **`docker-compose.prod.yml` is app + Postgres only** — the deployed EC2
  instance is a free-tier `t3.micro` (1GB RAM), which the ELK + Prometheus +
  Grafana stack doesn't fit on (Elasticsearch alone wants 2GB+). A real
  production deployment of this size would use managed equivalents (CloudWatch
  Logs instead of self-hosted ELK, Amazon Managed Prometheus/Grafana) or a
  larger instance — this is a deliberate scope trim for the free tier, not
  a gap.
- **Prod compose has no bind mount and no `command:` override** — runs from
  the built image only (no live-reload), and falls back to the Dockerfile's
  default `gunicorn` CMD instead of dev's `flask run --debug`. Required
  secrets (`SECRET_KEY`, `POSTGRES_PASSWORD`) use `${VAR:?message}` syntax so
  compose refuses to start with a clear error instead of silently running
  with an insecure default.
- **Postgres isn't exposed to the host at all in prod** — no port mapping,
  reachable only from the `app` container over the compose network. The dev
  compose exposes `5433` for local psql access; production has no reason to.

## Data model

- **Contract** — `id, title, counterparty, value, start_date, end_date,
  status, category, created_at, updated_at`. `status` is one of
  `draft, active, expiring, expired, renewed`.
- **RenewalHistory** — audit trail of renewals, one row per renewal event
  (`contract_id, previous_end_date, new_end_date, renewed_at, notes`).
- **Document** — attachment metadata only, not file bytes
  (`contract_id, filename, storage_path, content_type, size_bytes, uploaded_at`).

## Local setup

Requires Docker.

```bash
cp .env.example .env
docker compose up --build
```

That's it — Postgres, the test DB, and the Flask app all come up together.
App is on `http://localhost:5000`, dev DB is reachable from the host on
`localhost:5433` (not 5432 — see below). Edits to `.py` files reload the
running server automatically.

<details>
<summary>Running without Docker (host venv)</summary>

```bash
docker compose up -d db   # just Postgres
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export FLASK_APP=wsgi.py
flask db upgrade
flask run
```

</details>

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

### Reports

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/reports/value-by-category` | Contract count + total value grouped by category |
| GET | `/api/reports/expiring-soon-summary?days=` | Same grouping, restricted to contracts expiring within the threshold |

Both accept `?format=json` (default) or `?format=csv` (downloads as an
attachment).

Run tests (from the host venv, against the dockerized Postgres):
`TEST_DATABASE_URL=postgresql+psycopg2://contract_user:contract_pass@localhost:5433/contract_db_test pytest`

## Error tracking

[Sentry](https://sentry.io) free tier (5K events/month) is enough for this
project — no paid tier needed.

1. Sign up, create a Flask project, copy its DSN.
2. Put it in `.env` as `SENTRY_DSN=...` (works for both `docker compose up`
   and the host venv).
3. Leave it blank to disable entirely — the default, and what CI/tests run
   with.

Only genuinely unhandled exceptions (real bugs) reach Sentry. The expected
`400`/`404` error paths in this API are handled by dedicated error handlers
that return a response directly, so they never trigger Flask's unhandled
exception signal — Sentry stays quiet for expected client errors and only
fires for actual server-side failures.

## Logging (ELK)

`docker compose up` also brings up Elasticsearch, Kibana, and Filebeat —
no separate step needed, no cloud tier involved (self-hosted, local only).

Every request logs one JSON line (`app/utils/request_logging.py`):
`method, path, status_code, duration_ms, remote_addr`, plus the usual
`timestamp, level, logger, message`. Written to stdout (`docker compose logs
app`) and to `/var/log/app/app.log` on a shared volume, which Filebeat tails
and ships to Elasticsearch as `contract-api-logs-*`.

To view logs:

1. Open Kibana at `http://localhost:5601`.
2. **Stack Management → Data Views → Create data view**, pattern
   `contract-api-logs-*`, timestamp field `@timestamp`.
3. **Discover** to browse/query — e.g. `status_code >= 400` to find errors,
   or `duration_ms > 100` for slow requests.

Sanity check without Kibana: `curl localhost:9200/contract-api-logs-*/_search?pretty`.

Elasticsearch typically wants 2GB+ RAM to start reliably — if it's not
becoming healthy, check `docker compose logs elasticsearch` first.

## Metrics (Prometheus + Grafana)

Also part of `docker compose up` — no extra step, no cloud tier
(self-hosted, local only, and much lighter than the ELK stack).

The app exposes `GET /metrics` in Prometheus text format:
`http_requests_total{method,endpoint,status_code}` (counter) and
`http_request_duration_seconds{method,endpoint}` (histogram). Prometheus
scrapes it every 5s (`docker/prometheus.yml`).

Open Grafana at `http://localhost:3000` (anonymous viewer access enabled,
or `admin`/`admin`) — the **Contract API Overview** dashboard is already
there: request rate by endpoint, p95 latency by endpoint, 5xx error rate,
total requests. No manual setup, it's provisioned from
`docker/grafana/provisioning/`.

Sanity check without Grafana:
`curl 'localhost:9090/api/v1/query?query=sum(http_requests_total)'`.

## Deployment (AWS)

Deployed to a single free-tier EC2 instance (`t3.micro`, eu-central-1) —
Elastic Beanstalk was the other option, but a plain EC2 instance running the
same `docker-compose.prod.yml` we already use locally is simpler for a solo
project and reuses the container work directly instead of translating it
into a PaaS-specific format.

**Provisioning** (one-time, done manually): default VPC, a security group
opening `22` (SSH) and `5000` (app) to `0.0.0.0/0` — narrower in a real
deployment, left open here since this is a single demo instance with no
sensitive data — Amazon Linux 2023 AMI, Docker + Compose plugin installed
via user-data on first boot.

**Deploy flow**: `.github/workflows/ci-cd.yml` runs on every push —

1. `test` job: spins up a Postgres service container, runs the full pytest
   suite, does a Docker build sanity check.
2. `deploy` job (main branch only, gated on `test` passing): SSHes into the
   EC2 instance, `git pull`, `docker compose -f docker-compose.prod.yml
   --env-file .env up -d --build`.

The server's `.env` (real `SECRET_KEY`/`POSTGRES_PASSWORD`, generated with
`openssl rand -hex` directly on the instance) lives only on the instance
itself — never committed, never passed through CI.

**Free-tier notes**: `t3.micro` is free-tier eligible (750 hrs/month for 12
months); Elastic Beanstalk itself has no extra charge but its default
environment adds a load balancer that isn't — using a bare EC2 instance
avoids that. No RDS — Postgres runs in the same compose stack as the app,
one fewer billable resource for a project this size.

## Project status

- [x] Data model + migrations (Contract, RenewalHistory, Document)
- [x] CRUD REST API + Pydantic schemas
- [x] Status transition business logic
- [x] Pandas reporting/export endpoint
- [x] Full Docker Compose (app + db)
- [x] Sentry error tracking
- [x] Structured logging → Elasticsearch/Kibana
- [x] Prometheus + Grafana metrics
- [x] AWS deployment + CI
