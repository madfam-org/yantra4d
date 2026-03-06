"""Tests for request ID middleware and error_response integration."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from app import create_app


class TestRequestId:
    def setup_method(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_response_has_request_id_header(self):
        resp = self.client.get("/api/health")
        assert "X-Request-ID" in resp.headers
        # Must be a valid UUID4
        rid = resp.headers["X-Request-ID"]
        uuid.UUID(rid, version=4)

    def test_propagates_client_request_id(self):
        custom_id = "test-trace-id-123"
        resp = self.client.get("/api/health", headers={"X-Request-ID": custom_id})
        assert resp.headers["X-Request-ID"] == custom_id

    def test_error_response_includes_request_id(self):
        resp = self.client.get("/api/nonexistent")
        data = resp.get_json()
        assert "request_id" in data
        assert data["request_id"] == resp.headers["X-Request-ID"]

    def test_different_requests_get_different_ids(self):
        r1 = self.client.get("/api/health")
        r2 = self.client.get("/api/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


class TestErrorResponseFields:
    """Verify error_response includes error_code and request_id."""

    def setup_method(self):
        self.app = create_app()
        self.app.config["TESTING"] = True

        @self.app.route("/test-error-auto-code")
        def _auto_code():
            from utils.route_helpers import error_response
            return error_response("Request body must be JSON", 400)

        @self.app.route("/test-error-explicit-code")
        def _explicit_code():
            from utils.route_helpers import error_response
            return error_response("Something failed", 500, error_code="CUSTOM_CODE")

        self.client = self.app.test_client()

    def test_auto_derived_error_code(self):
        resp = self.client.get("/test-error-auto-code")
        data = resp.get_json()
        assert data["error_code"] == "request_body_must_be_json"
        assert data["status"] == "error"

    def test_explicit_error_code_override(self):
        resp = self.client.get("/test-error-explicit-code")
        data = resp.get_json()
        assert data["error_code"] == "CUSTOM_CODE"

    def test_error_always_has_error_code_field(self):
        resp = self.client.get("/test-error-auto-code")
        data = resp.get_json()
        assert "error_code" in data
