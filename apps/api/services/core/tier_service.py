"""
Tier service: loads tier definitions, resolves user tier from JWT claims,
and provides feature-gating helpers.

Tier hierarchy:
  guest (0)      — unauthenticated visitors, most restricted
  essentials (1) — authenticated users / open-source self-hosters (was "basic")
  pro (2)        — paid premium features
  premium (3)    — ecosystem bundle (was "madfam"; the alias still resolves)

Deprecated names are accepted forever on every input path and normalised here,
never at a call site — see ``LEGACY_TIER_MAP`` and ``_normalize_tier``.
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_tiers: dict | None = None

TIER_HIERARCHY = {"guest": 0, "essentials": 1, "pro": 2, "premium": 3}

# The most privileged tier, derived from the hierarchy rather than spelled out
# again, so adding a tier above `premium` does not silently leave callers that
# mean "the top tier" pointing at the old one.
TOP_TIER = max(TIER_HIERARCHY, key=lambda name: TIER_HIERARCHY[name])

# Sentinel used in tiers.json for a limit with no cap. It was already the
# convention for ``max_projects``; ``is_unlimited`` makes it readable everywhere.
UNLIMITED = -1

# Name of the environment variable holding the identity -> tier override map.
# Its VALUE is deployment configuration (a Kubernetes secret): a JSON object
# mapping a lower-cased email address to a tier name, e.g.
#     {"someone@example.com": "premium"}
# Deprecated names are accepted here too: an operator secret still saying
# "madfam" seats the same top tier (see LEGACY_TIER_MAP). No identity is ever
# committed to this repository.
TIER_OVERRIDES_ENV = "TIER_OVERRIDES"

# Deprecated tier name -> canonical tier name.
#
# These aliases are PERMANENT. Every input path funnels through
# ``_normalize_tier``: the ``yantra4d_tier`` claim, the TIER_OVERRIDES values,
# and the tier arguments of ``has_tier`` / ``get_tier_limits``. Janua still
# synthesises the literal ``"madfam"`` for machine tokens and an operator's
# TIER_OVERRIDES secret may still say it, so removing an entry from this map
# would silently downgrade live callers to essentials (ADR-006 Decision 4).
# Outputs — /api/me, X-RateLimit-Tier, entitlement descriptions — always carry
# the canonical name.
LEGACY_TIER_MAP = {"basic": "essentials", "madfam": "premium"}

# Which deprecated names have already been announced this process. The aliases
# sit on the hot path (every render, every /api/me), and one warning per
# request would bury the notice it exists to make visible.
_alias_notices_seen: set[str] = set()


def reset_alias_deprecation_notices() -> None:
    """Forget which aliases have been announced (test seam)."""
    _alias_notices_seen.clear()


TIERS_FILE = Path(__file__).parent.parent.parent / "tiers.json"


def load_tiers() -> dict:
    """Load tier definitions from tiers.json (cached after first call)."""
    global _tiers
    if _tiers is None:
        with open(TIERS_FILE) as f:
            _tiers = json.load(f)
        logger.info("Loaded %d tier definitions", len(_tiers))
    return _tiers


def is_unlimited(value) -> bool:
    """Whether a tiers.json limit value means "no cap".

    ``-1`` is the sentinel (see ``UNLIMITED``). Booleans are excluded on
    purpose: ``True`` is an ``int`` in Python and a feature flag must never be
    mistaken for a quota.
    """
    return isinstance(value, int) and not isinstance(value, bool) and value <= UNLIMITED


# Cache for the parsed TIER_OVERRIDES map, keyed on the raw environment value.
# The env var is read at call time (like RENDER_SCOPE_ENFORCEMENT in
# middleware/auth.py) so a rolled secret takes effect without a restart and
# tests can monkeypatch it, but the JSON is parsed at most once per value.
_tier_overrides: dict[str, str] | None = None
_tier_overrides_raw: str | None = None


def _parse_tier_overrides(raw: str) -> dict[str, str]:
    """Parse the TIER_OVERRIDES JSON object, tolerating anything malformed.

    A broken or absent override map must never take the API down, so every
    failure degrades to "no overrides" with a warning. Email addresses are
    identities: they are counted, never logged above DEBUG.
    """
    raw = (raw or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError) as e:
        logger.warning(
            "%s is not valid JSON (%s) — no identity tier overrides are active.",
            TIER_OVERRIDES_ENV, e,
        )
        return {}

    if not isinstance(parsed, dict):
        logger.warning(
            "%s must be a JSON object mapping email to tier name, got %s — "
            "no identity tier overrides are active.",
            TIER_OVERRIDES_ENV, type(parsed).__name__,
        )
        return {}

    overrides: dict[str, str] = {}
    skipped = 0
    for key, value in parsed.items():
        if not isinstance(key, str) or not isinstance(value, str):
            skipped += 1
            continue
        email = key.strip().lower()
        tier = _normalize_tier(value.strip())
        if not email:
            skipped += 1
            continue
        if tier not in TIER_HIERARCHY:
            # The tier name is configuration, not an identity, so it is safe to
            # name here — that is the whole point of the warning.
            logger.warning(
                "%s entry ignored: %r is not a known tier. Known tiers: %s.",
                TIER_OVERRIDES_ENV, value, ", ".join(sorted(TIER_HIERARCHY)),
            )
            skipped += 1
            continue
        overrides[email] = tier

    if skipped:
        logger.warning("%s: ignored %d malformed entr%s.",
                       TIER_OVERRIDES_ENV, skipped, "y" if skipped == 1 else "ies")
    logger.info("Loaded %d identity tier override(s)", len(overrides))
    logger.debug("Tier override identities: %s", sorted(overrides))
    return overrides


def load_tier_overrides() -> dict[str, str]:
    """Return the identity -> tier override map (cached per raw env value)."""
    global _tier_overrides, _tier_overrides_raw
    raw = os.getenv(TIER_OVERRIDES_ENV, "") or ""
    if _tier_overrides is None or raw != _tier_overrides_raw:
        _tier_overrides = _parse_tier_overrides(raw)
        _tier_overrides_raw = raw
    return _tier_overrides


def tier_override_for(auth_claims: dict | None) -> str | None:
    """Tier configured for this identity, or None when it has no override.

    An override is AUTHORITATIVE: it may raise a tier (a staff identity to the
    top tier) or lower one, and it wins over whatever ``yantra4d_tier`` the
    token carries. That is deliberate — the override map is the operator's
    statement about who someone is, and the claim is the issuer's.
    """
    if not isinstance(auth_claims, dict):
        return None
    email = auth_claims.get("email")
    if not isinstance(email, str):
        return None
    email = email.strip().lower()
    if not email:
        return None
    tier = load_tier_overrides().get(email)
    if tier is None:
        return None
    # DEBUG only: an email address never belongs in routine logs.
    logger.debug("Tier override applied for %s -> %s", email, tier)
    return tier


def _normalize_tier(tier: str) -> str:
    """Map a deprecated tier name to its canonical name.

    This is the one place an alias is resolved, so every caller — claims,
    TIER_OVERRIDES values, hierarchy comparisons, limit lookups — sees the
    canonical name and nothing downstream has to know an alias exists.

    The deprecation note is emitted at most once per process per alias: the
    name is still supported, so this is a nudge, not an incident.
    """
    normalized = LEGACY_TIER_MAP.get(tier)
    if normalized:
        if tier not in _alias_notices_seen:
            _alias_notices_seen.add(tier)
            logger.warning(
                "Deprecated tier name '%s' used — mapped to '%s'. The alias stays "
                "supported indefinitely; update the caller to send '%s' directly. "
                "(Logged once per process.)",
                tier, normalized, normalized,
            )
        return normalized
    return tier


def _tier_from_claim(auth_claims: dict) -> str:
    """Tier as stated by the token, before any identity override."""
    tier = auth_claims.get("yantra4d_tier", "essentials")
    tier = _normalize_tier(tier)
    if tier not in TIER_HIERARCHY:
        logger.warning("Unknown tier '%s' in JWT, falling back to essentials", tier)
        return "essentials"
    return tier


def resolve_tier(auth_claims: dict | None) -> str:
    """Resolve tier string from JWT claims.

    - No claims (anonymous) -> "guest"
    - Claims without yantra4d_tier -> "essentials" (authenticated but no subscription)
    - Claims with yantra4d_tier -> that value (validated against known tiers)
    - An identity listed in TIER_OVERRIDES -> that tier, overriding the above

    This is the single funnel every tier decision goes through, which is why
    the override lives here rather than at each call site. Deprecated names on
    either input — the claim or the override value — are normalised on the way
    through, so what comes out is always a canonical tier name.
    """
    if not auth_claims:
        return "guest"
    tier = _tier_from_claim(auth_claims)
    override = tier_override_for(auth_claims)
    if override is not None:
        return override
    return tier


def describe_entitlement(auth_claims: dict | None) -> dict:
    """Explain how the tier was arrived at, so a bad claim is visible.

    `resolve_tier` deliberately fails closed: an unrecognised `yantra4d_tier`
    falls back to essentials and logs a warning. That is the right security
    posture and the wrong debugging experience — a customer who has paid, whose
    token carries the wrong value, is seated in essentials with no signal
    anywhere the operator or the customer can see.

    The likeliest way to get there is real: checkout sends `plan=yantra4d_pro`,
    and the tier name is `pro`. Anything that writes the plan id into the claim
    produces a paying customer with no entitlement and no error.

    This reports the raw claim beside the resolved tier and says which of them
    happened, without ever echoing the token.
    """
    if not auth_claims:
        return {
            "source": "anonymous",
            "claim_present": False,
            "raw_claim": None,
            "resolved_tier": "guest",
            "detail": "No authenticated claims; guest tier.",
        }

    raw = auth_claims.get("yantra4d_tier")
    resolved = resolve_tier(auth_claims)

    override = tier_override_for(auth_claims)
    if override is not None:
        # Report the override plainly. Without this, an operator looking at
        # /api/me would see a tier the token does not carry and no explanation
        # for it — the exact opacity this diagnostic exists to remove. The
        # identity itself is never echoed; it is already known to the caller.
        return {
            "source": "tier_override",
            "claim_present": raw is not None,
            "raw_claim": raw,
            "resolved_tier": resolved,
            "detail": (
                f"This identity is listed in {TIER_OVERRIDES_ENV} and is seated in "
                f"tier {override!r}. The override is authoritative: it applies "
                "whether it raises or lowers the tier the token claims"
                + (f" ({raw!r})." if raw is not None else ".")
            ),
        }

    if raw is None:
        return {
            "source": "claim_absent",
            "claim_present": False,
            "raw_claim": None,
            "resolved_tier": resolved,
            "detail": (
                "Authenticated, but the token carries no yantra4d_tier claim, so it "
                "resolved to essentials. If this account has an active subscription, "
                "the dhanam to Janua entitlement contract has not written the claim."
            ),
        }

    normalized = _normalize_tier(raw)
    if normalized in TIER_HIERARCHY:
        return {
            "source": "claim",
            "claim_present": True,
            "raw_claim": raw,
            "resolved_tier": resolved,
            "detail": (
                f"Claim {raw!r} recognised as tier {resolved!r}."
                if raw == resolved
                else f"Claim {raw!r} was a deprecated name, mapped to {resolved!r}."
            ),
        }

    hint = ""
    if isinstance(raw, str) and raw.startswith("yantra4d_"):
        # Normalise the candidate: the registered SKU is `yantra4d_madfam`, and
        # without this the rename would stop recognising the very plan id this
        # hint exists to catch.
        candidate = _normalize_tier(raw.removeprefix("yantra4d_"))
        if candidate in TIER_HIERARCHY:
            hint = (
                f" This looks like the checkout PLAN ID rather than the tier name — "
                f"send {candidate!r}, not {raw!r}."
            )

    return {
        "source": "claim_unrecognised",
        "claim_present": True,
        "raw_claim": raw,
        "resolved_tier": resolved,
        "detail": (
            f"Claim {raw!r} is not a known tier, so it fell back to {resolved!r}. "
            f"Known tiers: {', '.join(sorted(TIER_HIERARCHY))}.{hint}"
        ),
    }


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

    ``-1`` is returned unchanged: it is the unlimited sentinel, and callers
    decide what "no cap" means for them (``is_unlimited``). Formatting it into
    a rate-limit string would produce the nonsense "-1/hour".
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


def export_format_allowed(tier: str, export_format: str) -> bool:
    """Whether a tier's export_formats list includes the given format.

    The per-tier list in tiers.json is the single source of truth. The render
    routes used to gate on the blanket `premium_export` boolean over a
    hardcoded format set, which contradicted the list: essentials declares
    ["stl", "3mf", "obj"], the UI unlocked those buttons from the list, and
    the server then 403'd 3mf/obj because essentials lacks `premium_export` —
    a paying user hitting a guaranteed error on an advertised feature.
    """
    formats = get_tier_limits(tier).get("export_formats") or []
    return export_format in formats


def minimum_tier_for_export_format(export_format: str) -> str | None:
    """Lowest tier (by hierarchy) whose export_formats includes the format.

    Used to name the tier an upsell message should point at. None when no
    tier offers the format (an unknown or mistyped format).
    """
    tiers = load_tiers()
    best: str | None = None
    for name, limits in tiers.items():
        if export_format in (limits.get("export_formats") or []):
            normalized = _normalize_tier(name)
            if best is None or TIER_HIERARCHY.get(normalized, 0) < TIER_HIERARCHY.get(best, 0):
                best = normalized
    return best
