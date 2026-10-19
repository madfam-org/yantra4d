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
| `RENDER_RLIMIT_AS_MB` | `1536` | Address-space ceiling (RLIMIT_AS) for each OpenSCAD / CadQuery render subprocess, warm CadQuery workers included. Linux only. Keeps one runaway render from OOM-killing the 2Gi worker container and every render in it: the render fails with `MemoryError` / `std::bad_alloc` instead. `MALLOC_ARENA_MAX=2` is set in the child while it applies. `0` disables |
| `RENDER_RLIMIT_CPU_S` | `RENDER_TIMEOUT_S + 60` | CPU-seconds ceiling (RLIMIT_CPU) for each one-shot render subprocess, a backstop behind the wall-clock timeout; the render fails with "exceeded its CPU-time limit". A warm CadQuery worker gets this times `YANTRA4D_CQ_WORKER_MAX_JOBS` for its lifetime (none when it never recycles). `0` disables |
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

### Mesh oracle (geom-core) (optional)

Mesh analysis — the watertight/manifold verdict, quote volume, surface area,
bounding box — goes through one seam, `services/engine/mesh_metrics.py`
(`MeshOracle`). The default **is** today's trimesh code
(`mesh_integrity.assess` plus trimesh's `volume`/`area`/`bounds`), so leaving
this unset changes nothing. The alternative backend is
[geom-core](https://github.com/madfam-org/geom-core), the shared C++ mesh
library of the geometry factories, whose integrity check is a port of
`mesh_integrity.py`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `MESH_ORACLE` | `trimesh` | `trimesh` — today's code. `geomcore` — geom-core answers. `both` — both run, **trimesh's numbers are returned**, every metric logs a `mesh_oracle_parity {json}` record (`slug`, `mode`, `metric`, `trimesh`, `geomcore`, `delta`, `match`) and each disagreement increments `mesh_oracle_parity_mismatch_total{metric}`. An unknown value, or `geomcore`/`both` without the wheel installed, logs an **error** once per process and runs on trimesh |

Where the seam is wired:

- **Cotiza quote export** (`routes/integrations/cotiza_export.py`): volume,
  surface area, bbox. Trimesh stays the default. geom-core computes surface
  area as a plain triangle sum; trimesh's `area` is the same sum, and the
  differential suite holds them to 1e-6 relative.
- **Render completion** (`apps/worker/render_worker.py`, both the sync and the
  stream path): under `geomcore` or `both` only, the worker assesses the
  finished mesh and logs the verdict (`mesh_oracle render integrity …`).
  Observation only — a render is never rejected. Under the default nothing is
  loaded, so the render path does exactly the work it did before. The worker
  serves no `/metrics`, so render-time parity is in the worker's logs; the
  counter is scraped from the API (quote export).
- Not in the seam: wall thickness and overhang (`/analyze/*`) return
  per-vertex/per-face arrays that geom-core does not expose to Python; the
  print estimator is the Studio's TypeScript (`apps/studio/src/lib/printEstimator.ts`,
  geom-core's WASM path, lane G3).

Known differences the parity soak measures (asserted in
`apps/api/tests/unit/test_mesh_oracle_differential.py`, not hidden by a
tolerance): geom-core welds exactly coincident vertices on load, so an
in-memory, never-welded mesh can differ (unwelded soup: same verdict, no merge
tolerance reported; two touching shells: two closed bodies to trimesh, a
non-manifold contact to geom-core). Every file the API reads goes through
`trimesh.load`, which welds first, so both agree on loaded files — including all
15 reference exports in `projects/*/exports/`. Centroids of open surfaces
differ (neither has a volumetric centroid; no caller reads one). geom-core is handed a
binary STL of the loaded mesh, i.e. float32 vertices, so float deltas of order
1e-8 relative are expected and sit far inside the 1e-6 parity tolerance.

**Installing the wheel.** geom-core is not on PyPI. It ships as GitHub Release
wheels, one per CPython version, and is installed only when the image is built
with both build args (the SHA-256 is mandatory with the URL; a mismatch, or a
wheel that does not import, fails the build):

```bash
docker build -f apps/api/Dockerfile \
  --build-arg GEOM_CORE_WHEEL_URL=https://github.com/madfam-org/geom-core/releases/download/v0.2.0/geom_core-0.2.0-cp312-cp312-linux_x86_64.whl \
  --build-arg GEOM_CORE_WHEEL_SHA256=cb386870f56e468d4d59cc0504977b50d8e81b6e0b91ebecd0e0ecc26975633d .
```

The production image is `python:3.12-slim`, so it needs a **cp312** wheel; pip
refuses a wheel for another interpreter and the build fails, visibly. v0.1.0
had no cp312 wheel; v0.2.0 does. `deploy.yml` (build-backend) passes exactly
this URL and digest, and CI's `mesh-oracle-differential` job installs the same
wheel on Python 3.12; `scripts/tests/test_geom_core_wheel_pin.py` fails when
the two pins differ or the wheel's CPython tag does not match the image.

The v0.2.0 Linux wheels are tagged plain `linux_x86_64`, not `manylinux`: the
extension needs `GLIBCXX_3.4.32` (GCC 13's libstdc++) and `GLIBC_2.32`. The
current `python:3.12-slim` (Debian trixie) has both; a Debian bookworm base
(`GLIBCXX_3.4.30`) would fail the build's import check. geom-core's next
release is meant to ship `manylinux_2_28` wheels, which remove this constraint.

**Bumping geom-core.** Change the URL and the SHA-256 in both `deploy.yml`
(build-backend `build-args`) and `ci.yml` (`mesh-oracle-differential` `env`),
taking the digest from the release asset
(`gh release view vX.Y.Z -R madfam-org/geom-core --json assets`).

**Flip plan.**

1. **Parity soak** — the image is built with the two build args and the
   **backend container** runs `MESH_ORACLE=both`
   (`k8s/production/yantra4d-backend-deployment.yaml`). Watch
   `mesh_oracle_parity_mismatch_total` and the `mesh_oracle_parity` log lines;
   every mismatch is either a geom-core bug (fix there, new release) or a
   documented difference (add it to the differential suite). **Starting it:**
   a change to `deploy.yml` alone does not rebuild the backend (its
   change filter is `apps/api/**`, `apps/worker/**`, the commons, `libs/**`…),
   while Argo applies the manifest at once. Until a backend build carries the
   wheel, each API process logs one ERROR (`MESH_ORACLE=both` without the
   wheel) and runs on trimesh. The wheel arrives with the next backend build:
   any backend-path merge, or the owner's
   `gh workflow run deploy.yml -R madfam-org/yantra4d --ref main -f force_deploy=true`
   (rebuilds every service). The soak clock starts when the API logs no
   wheel ERROR after a rollout.
2. **Default geomcore** — with the counter flat over the soak, set
   `MESH_ORACLE=geomcore`, then make it the default in `mesh_metrics.py`
   (`DEFAULT_MODE`) and install the wheel unconditionally.
3. **Remove the duplicates** — only then delete the trimesh metric code and
   `services/engine/mesh_integrity.py`; `mesh_integrity.py` stays until step 3,
   because it is the oracle the differential suite measures geom-core against.

**What the API soak covers.** On the backend container the seam runs only in
the Cotiza quote export (`POST /api/projects/<slug>/cotiza-quote-request`), which
computes the metrics before it calls Cotiza. So the soak compares
`volume_mm3`, `surface_area_mm2` and `bbox_mm`, once per export; it never
compares the integrity verdict or the body count (those run only in the
worker's `observe_render`, and the body count is not a compared metric in
yantra4d at all). Its sample size is the export traffic, which may be small;
the success criterion below therefore needs a minimum number of samples.

**Soak success criterion (proposed; the owner confirms it).** The geom-core
decision record (internal-devops
`decisions/2026-10-18-geom-core-shared-mesh-analysis-layer.md`) does not set
one; this is the coordinator's proposal for step 1 → step 2:

- at least 7 days with the wheel-built image serving and `MESH_ORACLE=both`;
- at least 200 quote exports (each logs one `mesh_oracle_parity` record per
  metric) across at least 20 distinct slugs; if real traffic is lower, the
  owner decides whether to drive exports for the commons slugs (the production
  manifest sets no `COTIZA_API_URL` today, so such a call computes the metrics
  and then fails at the Cotiza step without creating a quote);
- zero records with `"match": false`, or every one explained by a geom-core fix
  (released and re-soaked) or by a documented difference added to
  `test_mesh_oracle_differential.py`;
- no `geom-core wheel` / unknown-mode ERROR lines after the first minute of each
  pod (the wheel imports in every gunicorn worker);
- p95 latency of the quote export no worse than before the soak.

The default flip (step 2) also waits for the owner's ruling on the geom-core
body-count definition, although this API does not compare body counts (the
ruling decides what geom-core's `get_body_count()` means for every consumer).

**Reading the counter.** gunicorn runs `WEB_CONCURRENCY` (4) workers and
`prometheus_client` is not in multiprocess mode, so each `/metrics` scrape
reads one worker's counter: a mismatch shows up, but `increase()` undercounts
and can step down when the scrape lands on another worker. The log lines are
the count of record; the counter is the alarm. An alert for the platform
Prometheus (this repo has no PrometheusRule; the in-cluster scrape is the
Service annotation in `k8s/production/yantra4d-backend-service.yaml`; the
namespace label's name depends on that scrape job's relabelling):

```yaml
- alert: Yantra4dMeshOracleParityMismatch
  expr: sum by (metric) (max_over_time(mesh_oracle_parity_mismatch_total{namespace="yantra4d"}[1h])) > 0
  labels: {severity: warning, service: yantra4d-backend}
  annotations:
    summary: "trimesh and geom-core disagree on {{ $labels.metric }} (MESH_ORACLE=both soak)"
    description: >-
      Read the mesh_oracle_parity log lines with "match": false; each one is a
      geom-core bug or a documented difference. Rollback: MESH_ORACLE=trimesh.
```

**Why not the render worker yet.** `observe_render` runs synchronously at the
end of every render under `both`: it reloads the finished mesh and runs both
integrity checks. Measured on an x86_64 Mac (Python 3.12, geom-core 0.2.0,
icospheres): 82k faces +0.37 s and ~170 MB peak RSS; 328k faces +1.7 s and
~380 MB; 1.3M faces +7.5 s and ~1.15 GB. The worker's limit is 2Gi and the
commons has multi-million-face renders (the chainmail panel is 2.5M faces), so
the worker needs a face-count cap on `observe_render` (or a higher limit)
before it joins the soak. Its parity would be logs only: the worker serves no
`/metrics`.

**Rollback.** `MESH_ORACLE` back to `trimesh` (or removed) in the backend
Deployment; Argo syncs it and the API stops loading geom-core. The wheel can
stay in the image: unused, it changes nothing.

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
