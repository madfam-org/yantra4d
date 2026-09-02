"""
Centralized rate limit definitions for all API endpoints.
Import these constants instead of using inline strings.

Note: render rate limits apply to **backend (server-side) renders only**.
Client-side WASM rendering never hits these endpoints and is unlimited.
Per-tier backend render limits are defined in tiers.json
(key: ``backend_renders_per_hour``) and enforced dynamically in render.py.
"""

# Public / high-traffic
# Health endpoints are exempt from rate limiting (K8s probes)
ESTIMATE = "200/hour"
VERIFY = "50/hour"

# GET /api/projects/<slug>/wasm-bundle is deliberately UNLIMITED-BY-TIER: it
# carries only the app-wide default and has no constant here, on purpose.
# It is the free browser path — the response is an in-process cached blob of
# source text, so serving it costs a dictionary lookup and no CPU, while every
# request it satisfies is a *server* render that never happens. Rationing it by
# tier would push exactly that traffic back onto /api/render, which is the
# expensive thing the tiers exist to ration. Same reasoning as the WASM note
# above: browser rendering is unlimited at every tier, and the bundle is what
# makes browser rendering possible at all.

# AI
AI_SESSION = "30/hour"
# AI chat uses dynamic per-tier limits — see ai.py:_get_ai_rate_limit()

# Placeholder returned by a dynamic limit callable for a tier whose limit is the
# unlimited sentinel (-1 in tiers.json). It is never enforced: the same
# decorators pass an ``exempt_when`` predicate that makes flask-limiter skip the
# bucket. It exists because flask-limiter parses the limit string before it
# consults ``exempt_when`` (so "-1/hour" raises), and because a decorated limit
# is what suppresses the app-wide default — returning nothing would cap an
# unlimited tier at that default. Kept high so the fallback, if it were ever
# reached, is a ceiling rather than a throttle.
UNLIMITED_PLACEHOLDER = "1000000/hour"

# Editor (SCAD file CRUD)
EDITOR_READ = "120/hour"
EDITOR_WRITE = "120/hour"
EDITOR_CREATE = "30/hour"
EDITOR_DELETE = "30/hour"

# Git operations
GIT_STATUS = "60/hour"
GIT_DIFF = "60/hour"
GIT_COMMIT = "30/hour"
GIT_PUSH = "20/hour"
GIT_PULL = "20/hour"
GIT_CONNECT = "10/hour"
GIT_LOG = "60/hour"

# GitHub import
GITHUB_VALIDATE = "30/hour"
GITHUB_IMPORT = "10/hour"
GITHUB_SYNC = "20/hour"

# Projects
PROJECT_ANALYZE = "20/hour"
PROJECT_CREATE = "10/hour"
PROJECT_FORK = "10/hour"  # uses PROJECT_CREATE limit

# Onboarding
ONBOARD_ANALYZE = "20/hour"
ONBOARD_CREATE = "10/hour"

# Geometry analysis
ANALYSIS_THICKNESS = "20/hour"
ANALYSIS_OVERHANG = "20/hour"

# Simulation (pro-gated, dispatches GPU/CPU-heavy jobs)
SIMULATE_PHYSICS = "20/hour"
SIMULATE_OPTIMIZE = "20/hour"

# Animation flipbook rendering (N frames x M parts per request, streamed over SSE)
ANIMATION_RENDER = "10/hour"

# Analytics (unauthenticated — guests legitimately produce analytics)
ANALYTICS_TRACK = "120/hour"
ANALYTICS_SUMMARY = "60/hour"

# External integrations
COTIZA_EXPORT = "20/hour"
