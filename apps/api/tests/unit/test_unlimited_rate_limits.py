"""Tests for the unlimited (-1) tier limit and how it reaches flask-limiter.

The interesting part is not the sentinel but the plumbing: flask-limiter parses
a decorated limit string before it consults ``exempt_when``, so "-1/hour" is not
expressible, and a decorated limit is what suppresses the app-wide default, so
returning nothing would silently cap an unlimited tier at that default instead.
These tests pin both halves of the pair that works.
"""
import sys
from pathlib import Path

import pytest
from flask import Flask
from limits import parse_many

sys.path.insert(0, str(Path(__file__).parent.parent))

import rate_limits
from routes.engine.render import (
    _get_tiered_limit,
    _make_rate_limit_headers,
    _render_limit_exempt,
)
from routes.integrations.ai import _ai_limit_exempt, _get_ai_rate_limit

MADFAM = {"sub": "u1", "yantra4d_tier": "madfam"}
ESSENTIALS = {"sub": "u2", "yantra4d_tier": "essentials"}


@pytest.fixture
def app():
    application = Flask(__name__)
    application.config["TESTING"] = True
    return application


def _request(app, claims, body=None):
    """A request context with claims attached the way the auth middleware does."""
    ctx = app.test_request_context("/api/render", json=body or {})
    ctx.push()
    from flask import request
    request.auth_claims = claims
    return ctx


class TestRateLimitHeaders:
    def test_unlimited_tier_reports_the_word(self):
        headers = _make_rate_limit_headers("madfam")
        assert headers["X-RateLimit-Limit"] == "unlimited"
        assert headers["X-RateLimit-Tier"] == "madfam"
        assert headers["X-RateLimit-Type"] == "backend"

    def test_unlimited_tier_omits_remaining_and_reset(self):
        """There is nothing to remain out of, and no window to reset."""
        headers = _make_rate_limit_headers("madfam")
        assert "X-RateLimit-Remaining" not in headers
        assert "X-RateLimit-Reset" not in headers

    @pytest.mark.parametrize("tier,expected", [
        ("guest", "10"), ("essentials", "30"), ("pro", "150"),
    ])
    def test_capped_tiers_report_the_number(self, tier, expected):
        assert _make_rate_limit_headers(tier)["X-RateLimit-Limit"] == expected


class TestRenderLimitProvider:
    def test_unlimited_tier_gets_the_placeholder_not_a_negative_limit(self, app):
        ctx = _request(app, MADFAM, {"project": "nope"})
        try:
            assert _get_tiered_limit() == rate_limits.UNLIMITED_PLACEHOLDER
            assert "-1" not in _get_tiered_limit()
        finally:
            ctx.pop()

    def test_unlimited_tier_is_exempt(self, app):
        ctx = _request(app, MADFAM, {"project": "nope"})
        try:
            assert _render_limit_exempt() is True
        finally:
            ctx.pop()

    def test_capped_tier_gets_its_limit_and_is_not_exempt(self, app):
        ctx = _request(app, ESSENTIALS, {"project": "nope"})
        try:
            assert _get_tiered_limit() == "30/hour"
            assert _render_limit_exempt() is False
        finally:
            ctx.pop()

    def test_anonymous_caller_is_not_exempt(self, app):
        ctx = _request(app, None, {"project": "nope"})
        try:
            assert _get_tiered_limit() == "10/hour"
            assert _render_limit_exempt() is False
        finally:
            ctx.pop()

    def test_guest_project_override_still_applies(self, app, monkeypatch):
        """The per-project guest_render_limit path must survive the sentinel work."""
        import routes.engine.render as render_mod

        monkeypatch.setattr(
            render_mod, "get_manifest",
            lambda slug: {"project": {"guest_render_limit": 50}},
        )
        ctx = _request(app, None, {"project": "demo"})
        try:
            assert _get_tiered_limit() == "50/hour"
            assert _render_limit_exempt() is False
        finally:
            ctx.pop()


class TestAiLimitProvider:
    def test_unlimited_tier_gets_the_placeholder(self, app):
        ctx = _request(app, MADFAM)
        try:
            assert _get_ai_rate_limit() == rate_limits.UNLIMITED_PLACEHOLDER
            assert _ai_limit_exempt() is True
        finally:
            ctx.pop()

    def test_capped_tier_is_unchanged(self, app):
        ctx = _request(app, ESSENTIALS)
        try:
            assert _get_ai_rate_limit() == "20/hour"
            assert _ai_limit_exempt() is False
        finally:
            ctx.pop()

    def test_zero_is_a_real_limit_not_an_unlimited_one(self, app):
        """guest sits at 0/hour; that must keep blocking, not become a bypass."""
        ctx = _request(app, None)
        try:
            assert _get_ai_rate_limit() == "0/hour"
            assert _ai_limit_exempt() is False
        finally:
            ctx.pop()


class TestPlaceholderIsUsableByFlaskLimiter:
    def test_the_placeholder_parses(self):
        """If this ever stops parsing, every unlimited request 500s."""
        parsed = parse_many(rate_limits.UNLIMITED_PLACEHOLDER)
        assert parsed

    def test_a_negative_limit_string_would_not_parse(self):
        """Documents why the placeholder exists at all."""
        with pytest.raises(ValueError):
            parse_many("-1/hour")


class TestLimiterIntegration:
    """The claim that matters: an unlimited tier is not throttled by anything.

    A local Limiter with a deliberately tiny default (5/hour) stands in for the
    app-wide default. If the placeholder/exempt_when pair were replaced by
    "return no limit at all", that default would silently apply and this test
    would fail at request six.
    """

    @pytest.fixture
    def limited_app(self):
        from flask_limiter import Limiter

        limiter = Limiter(
            key_func=lambda: "test-key",
            default_limits=["5 per hour"],
            storage_uri="memory://",
            enabled=True,
            headers_enabled=True,
        )
        application = Flask(__name__)
        application.config["TESTING"] = True
        limiter.init_app(application)

        @application.route("/render", methods=["POST"])
        @limiter.limit(
            _get_tiered_limit,
            key_func=lambda: "test-key",
            exempt_when=_render_limit_exempt,
        )
        def render():
            from flask import jsonify
            return jsonify(ok=True)

        @application.before_request
        def _claims():
            from flask import request
            request.auth_claims = application.config.get("CLAIMS")

        return application

    def test_unlimited_tier_is_never_throttled(self, limited_app):
        limited_app.config["CLAIMS"] = MADFAM
        client = limited_app.test_client()
        codes = [client.post("/render", json={}).status_code for _ in range(30)]
        assert set(codes) == {200}

    def test_capped_tier_is_still_throttled_at_its_limit(self, limited_app):
        limited_app.config["CLAIMS"] = None  # guest: 10/hour
        client = limited_app.test_client()
        codes = [client.post("/render", json={}).status_code for _ in range(15)]
        assert codes.count(200) == 10
        assert codes.count(429) == 5
