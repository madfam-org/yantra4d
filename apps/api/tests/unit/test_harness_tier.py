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

The tier the audit asks for is spelled `premium` since ADR-006 Decision 4. It is
written here as ``TOP_TIER`` wherever the assertion means "the most privileged
tier", so a later rename moves one constant rather than a scatter of literals —
and as the bare literal in exactly the two places where the point is that the
string an operator types (the value in `.github/workflows/e2e-audit.yml`) is one
this build accepts.
The deprecated `madfam` is still accepted, because `harness_tier_override()`
normalises through `_normalize_tier`; that is pinned below rather than assumed,
since the cost of it being wrong is the nightly silently running as `guest`.
"""
import sys
from pathlib import Path

import pytest
from flask import Flask, request

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from services.core.tier_service import TOP_TIER, harness_tier_override


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
        """The literal the nightly workflow sets, resolved by this build.

        Spelled out rather than written as ``TOP_TIER`` on purpose: this is the
        one assertion that goes red if the tier is renamed again and
        `.github/workflows/e2e-audit.yml` is not renamed with it — which is the
        failure that silently seats the audit at `guest`.
        """
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "premium")
        assert harness_tier_override() == TOP_TIER

    def test_deprecated_top_tier_name_still_resolves(self, monkeypatch):
        """A harness still saying `madfam` is seated at the top tier, not dropped.

        `harness_tier_override()` refuses any value that is not a tier this
        build knows, and refuses it *quietly* — a warning, then the request runs
        gated. So the rename would have turned every `HARNESS_TIER=madfam`
        (this workflow before the rename, an operator's local shell, a fork that
        has not rebased) into a `guest` audit whose renders come back 403 and
        whose only symptom is the studio's upgrade prompt: run #168 again.

        It does not, because the override normalises through `_normalize_tier`
        and so inherits LEGACY_TIER_MAP, the permanent alias. This is the test
        that says so out loud.
        """
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        monkeypatch.setattr(Config, "HARNESS_TIER", "madfam")
        assert harness_tier_override() == TOP_TIER

    def test_ignored_when_auth_enabled(self, monkeypatch):
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        monkeypatch.setattr(Config, "HARNESS_TIER", TOP_TIER)
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
        monkeypatch.setattr(Config, "HARNESS_TIER", "premium")
        with app.test_request_context():
            assert _effective_tier() == TOP_TIER

    def test_auth_on_harness_tier_cannot_widen(self, app, monkeypatch):
        """Set in a real (auth-on) deployment it is inert: claims still decide."""
        monkeypatch.setattr(Config, "AUTH_ENABLED", True)
        monkeypatch.setattr(Config, "HARNESS_TIER", TOP_TIER)
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
            assert _effective_tier() == TOP_TIER
