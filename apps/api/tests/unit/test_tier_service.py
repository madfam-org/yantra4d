"""Tests for tier service."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.tier_service import resolve_tier, has_tier, get_tier_limits, check_feature, load_tiers


class TestResolveTier:
    def test_no_claims(self):
        assert resolve_tier(None) == "guest"

    def test_empty_claims(self):
        # Empty dict is falsy in Python, so resolve_tier returns "guest"
        assert resolve_tier({}) == "guest"

    def test_explicit_tier(self):
        assert resolve_tier({"yantra4d_tier": "pro"}) == "pro"

    def test_madfam_tier(self):
        assert resolve_tier({"yantra4d_tier": "madfam"}) == "madfam"

    def test_unknown_tier_fallback(self):
        assert resolve_tier({"yantra4d_tier": "enterprise"}) == "basic"


class TestHasTier:
    def test_same_tier(self):
        assert has_tier("pro", "pro") is True

    def test_higher_tier(self):
        assert has_tier("madfam", "pro") is True

    def test_lower_tier(self):
        assert has_tier("guest", "pro") is False

    def test_guest_meets_guest(self):
        assert has_tier("guest", "guest") is True

    def test_unknown_tier(self):
        # "unknown" defaults to 0 which equals "guest" (also 0)
        assert has_tier("unknown", "guest") is True


class TestGetTierLimits:
    def test_guest_limits(self):
        limits = get_tier_limits("guest")
        assert "renders_per_hour" in limits
        assert limits["renders_per_hour"] == 30

    def test_pro_limits(self):
        limits = get_tier_limits("pro")
        assert limits["renders_per_hour"] == 200

    def test_unknown_falls_back_to_guest(self):
        limits = get_tier_limits("unknown")
        assert limits["renders_per_hour"] == 30


class TestCheckFeature:
    def test_pro_has_github_import(self):
        assert check_feature("pro", "github_import") is True

    def test_guest_no_github_import(self):
        assert check_feature("guest", "github_import") is False

    def test_nonexistent_feature(self):
        assert check_feature("pro", "nonexistent_feature") is False


class TestLoadTiers:
    def test_loads_all_tiers(self):
        tiers = load_tiers()
        assert "guest" in tiers
        assert "basic" in tiers
        assert "pro" in tiers
        assert "madfam" in tiers
