# Database & Analytics

Yantra4D uses a lightweight database layer for analytics event tracking. Most platform data lives in `project.json` manifests (files on disk), not in the database.

## Storage Backends

| Backend | When Active | Configuration |
|---------|-------------|---------------|
| **SQLite** (default) | `DATABASE_URL` not set | File at `data/analytics.db` (override via `ANALYTICS_DB_PATH`) |
| **PostgreSQL** | `DATABASE_URL` set | Standard connection URI: `postgresql://user:pass@host:5432/dbname` |

The backend auto-detects: if `DATABASE_URL` is set, it uses PostgreSQL; otherwise it falls back to SQLite. This is configured in `apps/api/config.py`.

## Schema

### `events` Table

The only table, tracking platform usage events:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer (PK, autoincrement) | Event ID |
| `project` | String(100), NOT NULL | Project slug |
| `event_type` | String(50), NOT NULL | Event category (e.g., `render`, `export`, `view`) |
| `event_data` | Text, nullable | JSON-encoded event payload |
| `created_at` | Float, NOT NULL | Unix timestamp |

**Indexes**: `idx_events_project` (by project slug), `idx_events_type` (by event type).

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/analytics/track` | POST | Record an analytics event |
| `/api/analytics/<slug>/summary` | GET | Aggregate analytics for a project (default: last 30 days) |

## Migrations

Migrations are managed by **Flask-Migrate** (Alembic). The `Dockerfile` runs `flask db upgrade` at startup.

### Current Migrations

| Revision | Name | Date |
|----------|------|------|
| `001` | `001_initial_analytics.py` | 2026-03-20 |

### Idempotency Requirement

All migrations **must** be idempotent — check for table existence before creating:

```python
def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "events" not in inspector.get_table_names():
        op.create_table("events", ...)
```

This is critical because the Dockerfile runs `flask db upgrade` on every pod startup. Non-idempotent migrations crash the pod on persistent volumes (the table already exists from the previous deploy).

### Creating New Migrations

```bash
cd apps/api
flask db migrate -m "description of change"
# Review the generated file in migrations/versions/
# Add the sa.inspect() guard for idempotency
flask db upgrade
```

## PostHog Integration

Frontend analytics are also sent to PostHog (if configured) via `apps/api/posthog_analytics.py`. This is separate from the database-backed analytics and runs in parallel.

## Key Files

| File | Purpose |
|------|---------|
| `apps/api/config.py` | Database URI selection (lines 74, 129-140) |
| `apps/api/extensions.py` | SQLAlchemy and Flask-Migrate initialization |
| `apps/api/migrations/versions/001_initial_analytics.py` | Initial schema migration |
| `apps/api/routes/integrations/analytics.py` | Track and summary endpoints |
| `apps/api/posthog_analytics.py` | PostHog event forwarding |
