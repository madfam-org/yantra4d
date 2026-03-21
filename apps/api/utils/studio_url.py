"""Utilities for building public Studio URLs."""

import os
from urllib.parse import urlencode

from flask import request


def get_studio_base_url() -> str:
    """Return the public Studio base URL (no trailing slash).

    Reads ``PUBLIC_STUDIO_URL`` env var.  Falls back to the current
    request's host URL (works for local dev where API and Studio share
    a host).
    """
    base = os.getenv("PUBLIC_STUDIO_URL", "").rstrip("/")
    if not base:
        base = request.host_url.rstrip("/")
    return base


def build_project_url(
    slug: str,
    *,
    mode: str | None = None,
    preset_id: str | None = None,
    params: dict | None = None,
) -> str:
    """Build a path-based project URL with optional query parameters.

    Returns e.g. ``https://4d-app.madfam.io/project/tablaco?mode=storefront``
    """
    base = get_studio_base_url()
    url = f"{base}/project/{slug}"

    qs: dict[str, str] = {}
    if mode:
        qs["mode"] = mode
    if preset_id:
        qs["preset"] = preset_id
    if params:
        qs.update({str(k): str(v) for k, v in params.items()})

    if qs:
        url = f"{url}?{urlencode(qs)}"

    return url
