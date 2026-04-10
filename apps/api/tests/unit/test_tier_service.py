"""Tests for tier service."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from services.core.tier_service import resolve_tier, has_tier, get_tier_limits, get_render_limit, get_render_limit_for_project, check_feature, load_tiers


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
        assert resolve_tier({"yantra4d_tier": "enterprise"}) == "essentials"


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
        assert "backend_renders_per_hour" in limits
        assert limits["backend_renders_per_hour"] == 10

    def test_pro_limits(self):
        limits = get_tier_limits("pro")
        assert limits["backend_renders_per_hour"] == 150

    def test_unknown_falls_back_to_guest(self):
        limits = get_tier_limits("unknown")
        assert limits["backend_renders_per_hour"] == 10


class TestGetRenderLimit:
    def test_guest_render_limit(self):
        assert get_render_limit("guest") == 10

    def test_essentials_render_limit(self):
        assert get_render_limit("essentials") == 30

    def test_pro_render_limit(self):
        assert get_render_limit("pro") == 150

    def test_madfam_render_limit(self):
        assert get_render_limit("madfam") == 500


class TestGetRenderLimitForProject:
    def test_no_manifest_returns_tier_default(self):
        assert get_render_limit_for_project("guest", None) == 10

    def test_manifest_without_override_returns_tier_default(self):
        manifest = {"project": {"name": "Test"}}
        assert get_render_limit_for_project("guest", manifest) == 10

    def test_guest_with_project_override(self):
        manifest = {"project": {"name": "Demo", "guest_render_limit": 50}}
        assert get_render_limit_for_project("guest", manifest) == 50

    def test_override_only_applies_to_guest_tier(self):
        manifest = {"project": {"name": "Demo", "guest_render_limit": 50}}
        assert get_render_limit_for_project("pro", manifest) == 150
        assert get_render_limit_for_project("essentials", manifest) == 30

    def test_invalid_override_ignored(self):
        manifest = {"project": {"name": "Demo", "guest_render_limit": -1}}
        assert get_render_limit_for_project("guest", manifest) == 10

    def test_zero_override_ignored(self):
        manifest = {"project": {"name": "Demo", "guest_render_limit": 0}}
        assert get_render_limit_for_project("guest", manifest) == 10

    def test_string_override_ignored(self):
        manifest = {"project": {"name": "Demo", "guest_render_limit": "fifty"}}
        assert get_render_limit_for_project("guest", manifest) == 10


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
        assert "essentials" in tiers
        assert "pro" in tiers
        assert "madfam" in tiers
