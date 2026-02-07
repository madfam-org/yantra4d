"""
Centralized rate limit definitions for all API endpoints.
Import these constants instead of using inline strings.
"""

# Public / high-traffic
HEALTH = "1000/hour"
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
