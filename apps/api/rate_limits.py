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

# AI
AI_SESSION = "30/hour"
# AI chat uses dynamic per-tier limits — see ai.py:_get_ai_rate_limit()

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

# External integrations
COTIZA_EXPORT = "20/hour"
