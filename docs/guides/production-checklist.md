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

### Recommended

| Variable | Default | Purpose |
|----------|---------|---------|
| `LOG_FORMAT` | `text` | Set to `json` for structured logging in production |
| `REDIS_URL` | — | Redis URL for shared cache and rate limiting |
| `RATE_LIMIT_STORAGE` | `memory://` | Set to `redis://host:6379` for multi-worker rate limiting |
| `ANALYTICS_DB_PATH` | `data/analytics.db` | Path to analytics SQLite (use persistent volume) |
| `RENDER_TIMEOUT_S` | `300` | Max render time in seconds |

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
| Readiness | `GET /api/health/ready` | Checks OpenSCAD, Redis, disk, memory |

### Readiness States

- **healthy**: All checks pass
- **degraded**: Optional dependencies (OpenSCAD, Redis, analytics) unavailable — still serving requests (WASM fallback for rendering)
- **unhealthy** (503): Critical failure — should not receive traffic

## Docker Compose

For local Docker deployment, `docker-compose.yml` includes:

- Redis with AOF persistence (`redis_data` volume)
- Analytics DB on persistent volume (`analytics_data` volume)
- Rate limiting disabled by default for local dev

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
