"""
Shared validation utilities for API routes.
"""
import re

# Project slug: lowercase alphanumeric, hyphens, underscores. 3-50 chars.
_SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9_-]{1,48}[a-z0-9]$')


def validate_project_slug(slug: str) -> str | None:
    """Validate a project slug. Returns error message or None if valid."""
    if not slug:
        return "slug is required"
    if not _SLUG_RE.match(slug):
        return "Invalid slug: must be 3-50 lowercase alphanumeric characters, hyphens, or underscores"
    return None
