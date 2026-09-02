"""Tests for identity tier overrides (TIER_OVERRIDES) and the unlimited sentinel.

Every address here is an example.com address. The real override map is
deployment configuration (a Kubernetes secret) and never repository content.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.tier_service import (
    TIER_OVERRIDES_ENV,
    TOP_TIER,
    describe_entitlement,
    is_unlimited,
    load_tier_overrides,
    resolve_tier,
    tier_override_for,
)


@pytest.fixture(autouse=True)
def _clear_override_cache(monkeypatch):
    """The loader caches per raw env value; start every test from unset."""
    monkeypatch.delenv(TIER_OVERRIDES_ENV, raising=False)
    load_tier_overrides()
    yield


def set_overrides(monkeypatch, value):
    monkeypatch.setenv(TIER_OVERRIDES_ENV, value if isinstance(value, str) else json.dumps(value))


class TestLoadTierOverrides:
    def test_unset_is_empty(self):
        assert load_tier_overrides() == {}

    def test_empty_string_is_empty(self, monkeypatch):
        set_overrides(monkeypatch, "")
        assert load_tier_overrides() == {}

    def test_whitespace_only_is_empty(self, monkeypatch):
        set_overrides(monkeypatch, "   ")
        assert load_tier_overrides() == {}

    def test_invalid_json_is_empty(self, monkeypatch):
        set_overrides(monkeypatch, "{not json at all")
        assert load_tier_overrides() == {}

    def test_json_array_is_empty(self, monkeypatch):
        """The contract is an object; a list is configuration nobody can mean."""
        set_overrides(monkeypatch, '["someone@example.com"]')
        assert load_tier_overrides() == {}

    def test_valid_map_is_parsed(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "madfam"})
        assert load_tier_overrides() == {"someone@example.com": "madfam"}

    def test_emails_are_lower_cased_and_stripped(self, monkeypatch):
        set_overrides(monkeypatch, {"  SoMeOne@Example.COM  ": "madfam"})
        assert load_tier_overrides() == {"someone@example.com": "madfam"}

    def test_unknown_tier_entry_is_dropped(self, monkeypatch):
        set_overrides(monkeypatch, {
            "good@example.com": "pro",
            "bad@example.com": "enterprise",
        })
        assert load_tier_overrides() == {"good@example.com": "pro"}

    def test_legacy_tier_name_is_normalized(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "basic"})
        assert load_tier_overrides() == {"someone@example.com": "essentials"}

    def test_non_string_values_are_dropped(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": 3, "other@example.com": "pro"})
        assert load_tier_overrides() == {"other@example.com": "pro"}

    def test_reparses_when_env_changes(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "pro"})
        assert load_tier_overrides() == {"someone@example.com": "pro"}
        set_overrides(monkeypatch, {"someone@example.com": "madfam"})
        assert load_tier_overrides() == {"someone@example.com": "madfam"}


class TestTierOverrideFor:
    def test_none_claims(self):
        assert tier_override_for(None) is None

    def test_no_email_claim(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "madfam"})
        assert tier_override_for({"sub": "u1"}) is None

    def test_non_string_email_claim(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "madfam"})
        assert tier_override_for({"email": ["someone@example.com"]}) is None

    def test_claim_email_is_matched_case_insensitively(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "madfam"})
        assert tier_override_for({"email": "SOMEONE@Example.com"}) == "madfam"

    def test_unlisted_identity(self, monkeypatch):
        set_overrides(monkeypatch, {"someone@example.com": "madfam"})
        assert tier_override_for({"email": "other@example.com"}) is None


class TestResolveTierWithOverrides:
    def test_override_raises_tier(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        claims = {"sub": "u1", "email": "staff@example.com"}
        assert resolve_tier(claims) == "madfam"
        assert resolve_tier(claims) == TOP_TIER

    def test_override_raises_over_an_explicit_lower_claim(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        claims = {"email": "staff@example.com", "yantra4d_tier": "essentials"}
        assert resolve_tier(claims) == "madfam"

    def test_override_lowers_tier(self, monkeypatch):
        """An override is authoritative in both directions, not a maximum."""
        set_overrides(monkeypatch, {"demoted@example.com": "guest"})
        claims = {"email": "demoted@example.com", "yantra4d_tier": "pro"}
        assert resolve_tier(claims) == "guest"

    def test_override_applies_over_an_unrecognised_claim(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "pro"})
        claims = {"email": "staff@example.com", "yantra4d_tier": "enterprise"}
        assert resolve_tier(claims) == "pro"

    def test_anonymous_is_still_guest(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        assert resolve_tier(None) == "guest"

    def test_other_identities_are_untouched(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        assert resolve_tier({"email": "someone@example.com"}) == "essentials"
        assert resolve_tier({"email": "someone@example.com", "yantra4d_tier": "pro"}) == "pro"

    def test_invalid_env_leaves_claim_resolution_alone(self, monkeypatch):
        set_overrides(monkeypatch, "}{")
        assert resolve_tier({"email": "staff@example.com", "yantra4d_tier": "pro"}) == "pro"


class TestDescribeEntitlementWithOverrides:
    def test_reports_tier_override_source(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        d = describe_entitlement({"email": "staff@example.com", "yantra4d_tier": "essentials"})
        assert d["source"] == "tier_override"
        assert d["resolved_tier"] == "madfam"
        assert d["raw_claim"] == "essentials"
        assert "authoritative" in d["detail"]

    def test_override_without_a_tier_claim(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        d = describe_entitlement({"email": "staff@example.com"})
        assert d["source"] == "tier_override"
        assert d["claim_present"] is False
        assert d["resolved_tier"] == "madfam"

    def test_detail_never_echoes_the_identity(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        d = describe_entitlement({"email": "staff@example.com"})
        assert "staff@example.com" not in json.dumps(d)

    def test_unlisted_identity_keeps_the_claim_source(self, monkeypatch):
        set_overrides(monkeypatch, {"staff@example.com": "madfam"})
        d = describe_entitlement({"email": "other@example.com", "yantra4d_tier": "pro"})
        assert d["source"] == "claim"


class TestIsUnlimited:
    @pytest.mark.parametrize("value", [-1, -5])
    def test_negative_sentinels(self, value):
        assert is_unlimited(value) is True

    @pytest.mark.parametrize("value", [0, 1, 30, 500])
    def test_real_quotas(self, value):
        assert is_unlimited(value) is False

    @pytest.mark.parametrize("value", [None, "unlimited", "-1", 1.5, [], {}])
    def test_non_integers(self, value):
        assert is_unlimited(value) is False

    def test_booleans_are_not_quotas(self):
        """True is an int in Python; a feature flag must not read as a quota."""
        assert is_unlimited(True) is False
        assert is_unlimited(False) is False
