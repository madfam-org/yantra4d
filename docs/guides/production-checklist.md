# Production Deployment Checklist

Essential configuration for deploying Yantra4D in production.

## Environment Variables

### Required

| Variable | Example | Purpose |
|----------|---------|---------|
| `AUTH_ENABLED` | `true` | Enable JWT authentication (never `false` in production) |
| `CORS_ORIGINS` | `https://app.yantra4d.com,https://yantra4d.com` | Allowed origins (comma-separated) |
| `JANUA_ISSUER` | `https://auth.madfam.io` | JWT issuer URL |
| `JANUA_AUDIENCE` | `yantra4d-api` | JWT audience claim |
| `RENDER_WORKER_REQUIRED` | `true` | Fail readiness when the render worker heartbeat is stale or missing |

### Recommended

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_FORMAT` | `text` | Set to `json` for structured logging in production |
| `REDIS_URL` | — | Redis URL for shared cache and rate limiting |
| `RENDER_WORKER_HEARTBEAT_KEY` | `yantra_render_worker_heartbeat` | Shared Redis key used for worker liveness checks |
| `RENDER_WORKER_HEARTBEAT_TTL_SECONDS` | `60` | TTL for worker heartbeat window (also used as staleness baseline in API) |
| `RATE_LIMIT_STORAGE` | `memory://` | Set to `redis://host:6379` for multi-worker rate limiting |
| `ANALYTICS_DB_PATH` | `data/analytics.db` | Path to analytics SQLite (ephemeral is acceptable for stateless API pods; use Postgres for durable user/analytics data) |
| `RENDER_TIMEOUT_S` | `300` | Max render time in seconds |
| `ACTIVE_JOB_LEASE_GRACE_SECONDS` | `120` | Grace added to `RENDER_TIMEOUT_S` to derive the active-job lease TTL. A render job's Redis entry expires unless a live worker keeps renewing it on each heartbeat tick, so a pod roll or an OOM kill cannot leave the reported active-job count stuck above zero forever. Raise it only if the post-render format conversion legitimately needs longer |
| `RENDER_GC_TTL` | `86400` | Age at which a finished render artifact is deleted. On the `s3` store, **set a matching bucket lifecycle rule when provisioning** — the GC's age pass runs through the store, but a bucket that outlives the API should expire objects on its own too |
| `JWKS_CACHE_LIFESPAN` | `3600` | How long a fetched JWKS is served as fresh |
| `JWKS_STALE_MAX_AGE` | `86400` | Ceiling past which a stale JWKS is no longer served. Between the two, a JWKS whose refresh is failing keeps being served with a warning, so a brief issuer outage does not log everyone out; past the ceiling — or with nothing ever fetched — auth fails closed |
| `JWKS_REFRESH_BACKOFF` | `30` | Minimum seconds between refresh attempts, single-flighted |

### Render artifact storage (optional)

Finished renders go through an `ArtifactStore` on both the write and the read
path. The default **is** today's static directory, so leaving these unset
changes nothing. Full runbook, including the migration and rollback order:
[Render artifact storage](../operations/render-artifact-storage.md).

| Variable | Default | Purpose |
|----------|---------|---------|
| `RENDER_ARTIFACT_STORE` | `fs` | `fs` — the API's static directory. `s3` — an S3-compatible bucket. Any other value **refuses to start** |
| `RENDER_ARTIFACT_S3_ENDPOINT` | — | Base URL of the S3-compatible endpoint. Leave unset for real AWS S3 |
| `RENDER_ARTIFACT_S3_BUCKET` | — | Bucket name. Required when the store is `s3`; an unreachable bucket **fails closed at startup** |
| `RENDER_ARTIFACT_S3_REGION` | `us-east-1` | Region. MinIO ignores it, botocore requires one |
| `RENDER_ARTIFACT_S3_PREFIX` | — | Key namespace inside the bucket, e.g. `renders/v1`, so one bucket can hold more than one environment |

Credentials come from the standard `AWS_*` environment variables only. Set the
same values on **both** the API and the render-worker containers: they are two
ends of one store. Artifacts are always streamed through the API and never
redirected to a bucket URL — a redirect would bypass the private-artifact gate
and the download access checks, which parse the artifact *name*.

### AI Features (optional)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AI_PROVIDER` | `anthropic` | LLM provider (anthropic or openai) |
| `AI_API_KEY` | — | API key for the AI provider |
| `AI_MODEL` | — | Model override (uses provider default if empty) |

## Health Probes

Configure K8s/load balancer probes:

| Probe | Endpoint | Purpose |
|-------|----------|---------|
| Liveness | `GET /api/health/live` | Always 200 unless process hung |
| Readiness | `GET /api/health/ready` | Checks OpenSCAD, Redis, render worker heartbeat, disk, memory |

The readiness payload includes render-worker heartbeat age plus Redis queue
depth and active job count when Redis is reachable. Treat a missing or stale
render-worker heartbeat as a degraded render plane even if the API process is
otherwise alive. The active-job count is lease-backed: an entry whose lease no
live worker is renewing is pruned before the count is reported, so `active jobs`
above `queue depth 0` now means work is genuinely in flight rather than an id
left behind by a killed pod. An unreadable Redis reports `active_jobs: null`,
not `0` — "I could not read" and "there is nothing" are different answers.

### Readiness States

- **healthy**: All checks pass
- **degraded**: Optional dependencies (OpenSCAD, Redis, analytics) unavailable — still serving requests. OpenSCAD cartridges are largely unaffected because the browser is the default render placement; anything hard-pinned to the server (a `cadquery`/`graph`/`implicit` mode, `render.server_only`) has nowhere to run
- **unhealthy** (503): Critical failure — should not receive traffic

## Docker Compose

For local Docker deployment, `docker-compose.yml` includes:

- Redis with AOF persistence (`redis_data` volume)
- Analytics DB on persistent volume (`analytics_data` volume)
- Rate limiting disabled by default for local dev

## Production Storage and Rollouts

The backend must remain schedulable even when analytics persistence is
unavailable. Do not block API readiness on a single-writer SQLite PVC. For
production:

- Prefer `DATABASE_URL` pointing to managed Postgres for durable users and analytics.
- If SQLite is used as a fallback, mount `ANALYTICS_DB_PATH` on `emptyDir` and accept ephemeral analytics data.
- Use `Recreate` rollout strategy for any deployment that mounts an RWO volume.
- Keep the render worker in the same pod as the API only when shared render artifacts are required; otherwise prefer a separate worker deployment plus shared object storage.
- Set `PYTHONPATH=/app/backend` for the render worker or keep the worker import path bootstrapped in `apps/worker/render_worker.py`.

## Multi-Worker Rate Limiting

The default rate limiter uses per-process memory. In production with multiple gunicorn workers, set:

```bash
RATE_LIMIT_STORAGE=redis://redis:6379
REDIS_URL=redis://redis:6379
```

This ensures rate limits are shared across all workers.

## Backup

Analytics data is stored in a SQLite database. Back it up periodically:

```bash
./scripts/backup/backup-analytics.sh [source_path] [backup_dir]
```

The script retains the 30 most recent backups.

## Security Checklist

- [ ] `AUTH_ENABLED=true`
- [ ] `CORS_ORIGINS` restricted to production domains
- [ ] `FLASK_DEBUG=false`
- [ ] CSP headers configured in nginx/ingress
- [ ] `RATE_LIMIT_ENABLED=true` (default when `FLASK_DEBUG=false`)
- [ ] GitHub import tokens scoped to minimum permissions
- [ ] AI API keys stored in secrets manager
