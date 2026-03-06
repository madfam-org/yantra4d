"""Tests for utils.route_helpers — error_response, handle_exceptions, _derive_error_code."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))


from utils.route_helpers import _derive_error_code


class TestDeriveErrorCode:
    def test_simple_message(self):
        assert _derive_error_code("Not found") == "not_found"

    def test_message_with_special_chars(self):
        assert _derive_error_code("Request body must be JSON!") == "request_body_must_be_json"

    def test_message_with_multiple_spaces(self):
        assert _derive_error_code("Too   many   spaces") == "too_many_spaces"

    def test_empty_message(self):
        assert _derive_error_code("") == ""

    def test_message_with_hyphens_and_dots(self):
        assert _derive_error_code("Rate-limit exceeded.") == "rate_limit_exceeded"

    def test_message_with_quotes(self):
        assert _derive_error_code("Project 'foo' not found") == "project_foo_not_found"


class TestHandleExceptionsDecorator:
    def setup_method(self):
        from app import create_app
        self.app = create_app()
        self.app.config["TESTING"] = True

        from utils.route_helpers import handle_exceptions

        @self.app.route("/test-unhandled")
        @handle_exceptions
        def _boom():
            raise RuntimeError("unexpected failure")

        @self.app.route("/test-ok-wrapped")
        @handle_exceptions
        def _ok():
            from flask import jsonify
            return jsonify({"ok": True})

        self.client = self.app.test_client()

    def test_catches_unhandled_exception(self):
        resp = self.client.get("/test-unhandled")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["error_code"] == "INTERNAL_ERROR"
        assert "request_id" in data

    def test_passes_through_on_success(self):
        resp = self.client.get("/test-ok-wrapped")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
