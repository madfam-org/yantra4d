"""Tests for HARNESS_TIER — the opt-in tier an auth-disabled harness runs as.

Why this exists: the nightly browser audit (apps/studio/e2e/tests/23-browser-audit)
drives REAL renders, and gridfinity's default `bin` mode is CadQuery, which the
`guest` tier may not use. The audit runs the API with AUTH_ENABLED=false and
FLASK_DEBUG=false, so before HARNESS_TIER it was gated as guest and every render
came back 403 — run #168 lost two tests to the studio's upgrade prompt.

Both directions are pinned here, because the danger is symmetrical:

  - unset, it must change NOTHING. The whole API test suite runs auth-off
    (conftest `_isolate_config`), and the tier-enforcement tests depend on
    seeing guest refusals in exactly that state.
  - set, it must be inert whenever AUTH_ENABLED is true, so the variable
    escaping into a real deployment cannot widen anybody's entitlements.
"""
import sys
from pathlib import Path

import pytest
from flask import Flask, request

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.core.tier_service import harness_tier_override


@pytest.fixture
def app():
    """Bare app with debug OFF — the state the nightly harness runs in."""
    return Flask(__name__)


def _effective_tier():
    """Call the render route's gating helper (imported late; it needs Config)."""
    from routes.engine.render import _effective_tier as impl
    return impl()


class TestHarnessTierOverride:
    def test_unset_is_none(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "")
        assert harness_tier_override() is None

    def test_honoured_when_auth_disabled(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "madfam")
        assert harness_tier_override() == "madfam"

    def test_ignored_when_auth_enabled(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        monkeypatch.setattr(Config, "HARNESS_TIER", "madfam")
        assert harness_tier_override() is None

    def test_unknown_tier_ignored(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "enterprise")
        assert harness_tier_override() is None

    def test_case_and_whitespace_tolerated(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "  PRO  ")
        assert harness_tier_override() == "pro"

    def test_legacy_name_normalised(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "basic")
        assert harness_tier_override() == "essentials"

    def test_guest_is_a_valid_request(self, monkeypatch):
        """Naming the default tier is legal, not an error."""
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "guest")
        assert harness_tier_override() == "guest"


class TestEffectiveTier:
    def test_auth_off_debug_off_unset_is_guest(self, app, monkeypatch):
        """The state the API test suite runs in — gates must stay closed."""
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "")
        with app.test_request_context():
            assert _effective_tier() == "guest"

    def test_auth_off_harness_tier_applies(self, app, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "madfam")
        with app.test_request_context():
            assert _effective_tier() == "madfam"

    def test_auth_on_harness_tier_cannot_widen(self, app, monkeypatch):
        """Set in a real (auth-on) deployment it is inert: claims still decide."""
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        monkeypatch.setattr(Config, "HARNESS_TIER", "madfam")
        with app.test_request_context():
            assert _effective_tier() == "guest"
            request.auth_claims = {"yantra4d_tier": "pro"}
            assert _effective_tier() == "pro"

    def test_debug_unlock_still_wins(self, monkeypatch):
        """The pre-existing dev rule is untouched, and outranks a lower request."""
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "guest")
        debug_app = Flask(__name__)
        debug_app.debug = True
        with debug_app.test_request_context():
            assert _effective_tier() == "madfam"
