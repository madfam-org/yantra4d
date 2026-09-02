"""The `madfam` -> `premium` alias: every input path, and what comes back out.

ADR-006 Decision 4 renamed the top tier. The old name is not deprecated-then-
removed — it is accepted **forever**, because Janua still synthesises the
literal `"madfam"` for machine tokens and an operator's `TIER_OVERRIDES`
secret may still say it. These tests are the guarantee, not a migration aid:
if one of them ever has to be deleted, a live caller has been silently
downgraded to essentials.

The other half of the contract is that nothing *emits* the old name. Inputs
accept both; outputs are canonical.
"""
import json
import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.tier_service import (
    LEGACY_TIER_MAP,
    TIER_HIERARCHY,
    TIER_OVERRIDES_ENV,
    TOP_TIER,
    describe_entitlement,
    get_render_limit,
    get_tier_limits,
    has_tier,
    load_tier_overrides,
    load_tiers,
    reset_alias_deprecation_notices,
    resolve_tier,
    tier_override_for,
)

LEGACY_TOP = "madfam"
CANONICAL_TOP = "premium"


@pytest.fixture(autouse=True)
def _clean_slate(monkeypatch):
    monkeypatch.delenv(TIER_OVERRIDES_ENV, raising=False)
    load_tier_overrides()
    reset_alias_deprecation_notices()
    yield
    reset_alias_deprecation_notices()


class TestTheLadder:
    def test_the_top_tier_is_premium(self):
        assert TOP_TIER == CANONICAL_TOP
        assert TIER_HIERARCHY[CANONICAL_TOP] == 3

    def test_the_old_name_is_not_a_tier_any_more(self):
        assert LEGACY_TOP not in TIER_HIERARCHY
        assert LEGACY_TOP not in load_tiers()

    def test_the_alias_is_declared_and_permanent(self):
        assert LEGACY_TIER_MAP[LEGACY_TOP] == CANONICAL_TOP
        # The `basic` alias predates this rename and must survive it.
        assert LEGACY_TIER_MAP["basic"] == "essentials"


class TestClaimInputPath:
    def test_a_legacy_claim_seats_the_top_tier(self):
        assert resolve_tier({"yantra4d_tier": LEGACY_TOP}) == CANONICAL_TOP

    def test_a_legacy_claim_is_not_a_silent_downgrade(self):
        """The failure this guards against: falling through to essentials."""
        assert resolve_tier({"yantra4d_tier": LEGACY_TOP}) != "essentials"

    def test_a_legacy_claim_gets_the_top_tier_limits(self):
        assert get_render_limit(LEGACY_TOP) == get_render_limit(CANONICAL_TOP)
        assert get_tier_limits(LEGACY_TOP) == get_tier_limits(CANONICAL_TOP)

    def test_hierarchy_comparisons_accept_the_alias_on_both_sides(self):
        assert has_tier(LEGACY_TOP, "pro") is True
        assert has_tier(LEGACY_TOP, LEGACY_TOP) is True
        assert has_tier(CANONICAL_TOP, LEGACY_TOP) is True
        assert has_tier("pro", LEGACY_TOP) is False


class TestOverrideInputPath:
    def test_a_legacy_override_value_is_stored_canonically(self, monkeypatch):
        monkeypatch.setenv(TIER_OVERRIDES_ENV,
                           json.dumps({"someone@example.com": LEGACY_TOP}))
        assert load_tier_overrides() == {"someone@example.com": CANONICAL_TOP}

    def test_a_legacy_override_value_seats_the_top_tier(self, monkeypatch):
        """The operator's Secret may say `madfam`; that is what the alias is for."""
        monkeypatch.setenv(TIER_OVERRIDES_ENV,
                           json.dumps({"staff@example.com": LEGACY_TOP}))
        claims = {"email": "staff@example.com", "yantra4d_tier": "essentials"}
        assert tier_override_for(claims) == CANONICAL_TOP
        assert resolve_tier(claims) == TOP_TIER

    def test_a_legacy_override_value_is_not_dropped_as_unknown(self, monkeypatch):
        monkeypatch.setenv(TIER_OVERRIDES_ENV, json.dumps({
            "legacy@example.com": LEGACY_TOP,
            "bogus@example.com": "enterprise",
        }))
        assert load_tier_overrides() == {"legacy@example.com": CANONICAL_TOP}

    def test_a_legacy_override_value_gets_the_top_tier_limits(self, monkeypatch):
        """The production Secret still says `madfam`, so this is the live path."""
        monkeypatch.setenv(TIER_OVERRIDES_ENV,
                           json.dumps({"staff@example.com": LEGACY_TOP}))
        seated = resolve_tier({"email": "staff@example.com"})
        assert get_tier_limits(seated) == get_tier_limits(CANONICAL_TOP)
        assert get_render_limit(seated) == get_render_limit(CANONICAL_TOP)


class TestOutputsAreCanonical:
    def test_resolve_tier_never_returns_the_old_name(self):
        for claim in (LEGACY_TOP, CANONICAL_TOP):
            assert resolve_tier({"yantra4d_tier": claim}) == CANONICAL_TOP

    def test_the_entitlement_description_reports_the_canonical_tier(self):
        d = describe_entitlement({"yantra4d_tier": LEGACY_TOP})
        assert d["source"] == "claim"
        assert d["resolved_tier"] == CANONICAL_TOP
        # The raw claim is reported verbatim — that is the diagnostic's whole job.
        assert d["raw_claim"] == LEGACY_TOP
        assert "deprecated" in d["detail"].lower()

    def test_the_known_tier_list_offers_the_new_name(self):
        d = describe_entitlement({"yantra4d_tier": "platinum"})
        assert CANONICAL_TOP in d["detail"]

    def test_the_override_description_reports_the_canonical_tier(self, monkeypatch):
        monkeypatch.setenv(TIER_OVERRIDES_ENV,
                           json.dumps({"staff@example.com": LEGACY_TOP}))
        d = describe_entitlement({"email": "staff@example.com"})
        assert d["source"] == "tier_override"
        assert d["resolved_tier"] == CANONICAL_TOP
        assert repr(CANONICAL_TOP) in d["detail"]


class TestDeprecationNotice:
    def test_the_alias_is_announced(self, caplog):
        with caplog.at_level(logging.WARNING, logger="services.core.tier_service"):
            resolve_tier({"yantra4d_tier": LEGACY_TOP})
        assert LEGACY_TOP in caplog.text
        assert CANONICAL_TOP in caplog.text

    def test_it_is_announced_at_most_once_per_process(self, caplog):
        """The alias is on the hot path; a warning per request buries the notice."""
        with caplog.at_level(logging.WARNING, logger="services.core.tier_service"):
            for _ in range(25):
                resolve_tier({"yantra4d_tier": LEGACY_TOP})
        notices = [r for r in caplog.records if "Deprecated tier name" in r.getMessage()]
        assert len(notices) == 1

    def test_each_alias_gets_its_own_notice(self, caplog):
        with caplog.at_level(logging.WARNING, logger="services.core.tier_service"):
            resolve_tier({"yantra4d_tier": LEGACY_TOP})
            resolve_tier({"yantra4d_tier": "basic"})
        notices = [r for r in caplog.records if "Deprecated tier name" in r.getMessage()]
        assert len(notices) == 2

    def test_the_canonical_name_is_silent(self, caplog):
        with caplog.at_level(logging.WARNING, logger="services.core.tier_service"):
            resolve_tier({"yantra4d_tier": CANONICAL_TOP})
        assert "Deprecated tier name" not in caplog.text


class TestTheDevUnlock:
    """`effective_tier`'s auth-off + debug unlock names the top tier by CONSTANT.

    The unlock (middleware/auth.py, shared since #87 by the generation-time and
    retrieval-time export-format gates) used to `return "madfam"`. A spelled-out
    tier name there is the one place a rename can half-land without a single
    test going red: `get_tier_limits` and `check_feature` normalise their
    argument, so the gates keep passing — but the string is also reported
    verbatim as `X-RateLimit-Tier`, and `TIER_HIERARCHY.get(...)` of a name the
    hierarchy no longer holds is `0`, i.e. guest.
    """

    def _unlocked_tier(self, monkeypatch, *, debug=True, auth_enabled=False):
        from flask import Flask

        from config import Config
        from middleware.auth import effective_tier

        monkeypatch.setattr(Config, "AUTH_ENABLED", auth_enabled)
        app = Flask(__name__)
        app.debug = debug
        with app.test_request_context("/"):
            return effective_tier()

    def test_the_unlock_seats_the_canonical_top_tier(self, monkeypatch):
        assert self._unlocked_tier(monkeypatch) == CANONICAL_TOP

    def test_the_unlocked_name_is_a_tier_this_build_ranks_highest(self, monkeypatch):
        """What a leftover literal loses: a rank in the hierarchy."""
        tier = self._unlocked_tier(monkeypatch)
        assert tier in TIER_HIERARCHY
        assert TIER_HIERARCHY[tier] == max(TIER_HIERARCHY.values())
        assert has_tier(tier, "pro") is True

    def test_the_unlock_still_needs_debug(self, monkeypatch):
        """Auth-off with debug off is the state the tier suites run in: guest."""
        assert self._unlocked_tier(monkeypatch, debug=False) == "guest"

    def test_auth_on_is_never_unlocked(self, monkeypatch):
        assert self._unlocked_tier(monkeypatch, auth_enabled=True) == "guest"

    def test_the_reported_rate_limit_tier_is_canonical(self, monkeypatch):
        """The unlocked name reaches a client verbatim in this header."""
        from flask import Flask

        from config import Config
        from routes.engine.render import _effective_tier, _make_rate_limit_headers

        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        app = Flask(__name__)
        app.debug = True
        with app.test_request_context("/"):
            headers = _make_rate_limit_headers(_effective_tier())
        assert headers["X-RateLimit-Tier"] == CANONICAL_TOP
        assert headers["X-RateLimit-Tier"] != LEGACY_TOP


class TestUpsellCopy:
    """403 upsell copy names canonical tiers only."""

    def test_every_labelled_tier_is_a_current_tier(self):
        from middleware.auth import _TIER_LABELS

        assert set(_TIER_LABELS) <= set(TIER_HIERARCHY)
        assert LEGACY_TOP not in _TIER_LABELS

    def test_the_top_tier_has_a_label(self):
        from middleware.auth import _TIER_LABELS

        assert _TIER_LABELS[TOP_TIER] == "Premium"
