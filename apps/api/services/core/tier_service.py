"""
Tier service: loads tier definitions, resolves user tier from JWT claims,
and provides feature-gating helpers.

Tier hierarchy:
  guest (0)      — unauthenticated visitors, most restricted
  essentials (1) — authenticated users / open-source self-hosters (was "basic")
  pro (2)        — paid premium features
  madfam (3)     — ecosystem bundle
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_tiers: dict | None = None

TIER_HIERARCHY = {"guest": 0, "essentials": 1, "pro": 2, "madfam": 3}

# Legacy tier name mapping
LEGACY_TIER_MAP = {"basic": "essentials"}

TIERS_FILE = Path(__file__).parent.parent.parent / "tiers.json"


def load_tiers() -> dict:
    """Load tier definitions from tiers.json (cached after first call)."""
    global _tiers
    if _tiers is None:
        with open(TIERS_FILE) as f:
            _tiers = json.load(f)
        logger.info("Loaded %d tier definitions", len(_tiers))
    return _tiers


def _normalize_tier(tier: str) -> str:
    """Normalize legacy tier names to current names."""
    normalized = LEGACY_TIER_MAP.get(tier)
    if normalized:
        logger.warning("Deprecated tier name '%s' used — mapped to '%s'. "
                       "Update client to use '%s' directly.", tier, normalized, normalized)
        return normalized
    return tier


def resolve_tier(auth_claims: dict | None) -> str:
    """Resolve tier string from JWT claims.

    - No claims (anonymous) -> "guest"
    - Claims without yantra4d_tier -> "essentials" (authenticated but no subscription)
    - Claims with yantra4d_tier -> that value (validated against known tiers)
    """
    if not auth_claims:
        return "guest"
    tier = auth_claims.get("yantra4d_tier", "essentials")
    tier = _normalize_tier(tier)
    if tier not in TIER_HIERARCHY:
        logger.warning("Unknown tier '%s' in JWT, falling back to essentials", tier)
        return "essentials"
    return tier


def has_tier(user_tier: str, required_tier: str) -> bool:
    """Check if user_tier meets or exceeds required_tier in hierarchy."""
    user_tier = _normalize_tier(user_tier)
    required_tier = _normalize_tier(required_tier)
    return TIER_HIERARCHY.get(user_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)


def get_tier_limits(tier: str) -> dict:
    """Return the limits dict for a given tier."""
    tiers = load_tiers()
    tier = _normalize_tier(tier)
    return tiers.get(tier, tiers["guest"])


def get_render_limit(tier: str) -> int:
    """Return backend renders-per-hour for a tier.

    Reads ``backend_renders_per_hour`` with fallback to the legacy
    ``renders_per_hour`` key for backward compatibility.
    """
    limits = get_tier_limits(tier)
    return limits.get("backend_renders_per_hour", limits.get("renders_per_hour", 30))


def get_render_limit_for_project(tier: str, manifest=None) -> int:
    """Return backend renders-per-hour, checking for per-project guest override.

    Projects can declare ``guest_render_limit`` in ``project.json`` to allow
    higher render rates for unauthenticated visitors (e.g., client demos).
    The override only applies to the ``guest`` tier.

    Accepts both ``ProjectManifest`` objects and raw dicts.
    """
    if manifest and tier == "guest":
        # ProjectManifest has .project attribute; raw dicts use .get()
        project = getattr(manifest, "project", None)
        if project is None and isinstance(manifest, dict):
            project = manifest.get("project", {})
        if isinstance(project, dict):
            override = project.get("guest_render_limit")
            if isinstance(override, int) and override > 0:
                return override
    return get_render_limit(tier)


def check_feature(tier: str, feature: str) -> bool:
    """Check if a tier has access to a specific feature (boolean key in tier config)."""
    limits = get_tier_limits(tier)
    return bool(limits.get(feature, False))
