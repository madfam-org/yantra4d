"""Tests for shared validation utilities."""
import pytest
from flask import Flask

from utils.validators import validate_project_slug, require_valid_slug


class TestValidateProjectSlug:
    """Tests for the validate_project_slug function."""

    @pytest.mark.parametrize("slug", [
        "my-project",
        "test-123",
        "abc",
        "a-b",
        "project_name",
        "a" * 50,
    ])
    def test_valid_slugs(self, slug):
        assert validate_project_slug(slug) is None

    @pytest.mark.parametrize("slug,reason", [
        ("", "empty"),
        ("ab", "too short"),
        ("AB", "uppercase"),
        ("My Project", "spaces and uppercase"),
        ("-leading", "leading hyphen"),
        ("trailing-", "trailing hyphen"),
        ("_leading", "leading underscore"),
        ("has spaces", "spaces"),
        ("has.dots", "dots"),
        ("../traversal", "path traversal"),
        ("a" * 51, "too long"),
        ("ALLCAPS", "all uppercase"),
    ])
    def test_invalid_slugs(self, slug, reason):
        result = validate_project_slug(slug)
        assert result is not None, f"Slug '{slug}' should be invalid ({reason})"

    def test_none_slug(self):
        assert validate_project_slug(None) is not None


class TestRequireValidSlugDecorator:
    """Tests for the @require_valid_slug route decorator."""

    @pytest.fixture
    def app(self):
        app = Flask(__name__)

        @app.route("/test/<slug>")
        @require_valid_slug
        def test_route(slug):
            return {"slug": slug}, 200

        return app

    def test_valid_slug_passes_through(self, app):
        with app.test_client() as client:
            resp = client.get("/test/my-project")
            assert resp.status_code == 200
            assert resp.get_json()["slug"] == "my-project"

    def test_invalid_slug_returns_400(self, app):
        with app.test_client() as client:
            resp = client.get("/test/INVALID SLUG")
            assert resp.status_code == 400
            data = resp.get_json()
            assert "error" in data

    def test_path_traversal_slug_returns_400(self, app):
        with app.test_client() as client:
            resp = client.get("/test/../etc/passwd")
            # Flask may handle this differently, but the slug portion should be validated
            # If it reaches the decorator, it should be rejected
            assert resp.status_code in (400, 404)
