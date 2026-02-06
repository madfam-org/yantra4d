"""
Tier service: loads tier definitions, resolves user tier from JWT claims,
and provides feature-gating helpers.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_tiers: dict | None = None

TIER_HIERARCHY = {"guest": 0, "basic": 1, "pro": 2, "madfam": 3}

TIERS_FILE = Path(__file__).parent.parent / "tiers.json"


def load_tiers() -> dict:
    """Load tier definitions from tiers.json (cached after first call)."""
    global _tiers
    if _tiers is None:
        with open(TIERS_FILE) as f:
            _tiers = json.load(f)
        logger.info("Loaded %d tier definitions", len(_tiers))
    return _tiers


def resolve_tier(auth_claims: dict | None) -> str:
    """Resolve tier string from JWT claims.

    - No claims (anonymous) -> "guest"
    - Claims without yantra4d_tier -> "basic"
    - Claims with yantra4d_tier -> that value (validated against known tiers)
    """
    if not auth_claims:
        return "guest"
    tier = auth_claims.get("yantra4d_tier", "basic")
    if tier not in TIER_HIERARCHY:
        logger.warning("Unknown tier '%s' in JWT, falling back to basic", tier)
        return "basic"
    return tier


def has_tier(user_tier: str, required_tier: str) -> bool:
    """Check if user_tier meets or exceeds required_tier in hierarchy."""
    return TIER_HIERARCHY.get(user_tier, 0) >= TIER_HIERARCHY.get(required_tier, 0)


def get_tier_limits(tier: str) -> dict:
    """Return the limits dict for a given tier."""
    tiers = load_tiers()
    return tiers.get(tier, tiers["guest"])


def check_feature(tier: str, feature: str) -> bool:
    """Check if a tier has access to a specific feature (boolean key in tier config)."""
    limits = get_tier_limits(tier)
    return bool(limits.get(feature, False))
