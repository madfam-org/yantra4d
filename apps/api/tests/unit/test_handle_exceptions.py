"""Tests for handle_exceptions decorator."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))

from flask import Flask, jsonify
from utils.route_helpers import handle_exceptions


class TestHandleExceptions:
    def setup_method(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True

        @self.app.route("/test-ok")
        @handle_exceptions
        def ok_route():
            return jsonify({"status": "ok"})

        @self.app.route("/test-error")
        @handle_exceptions
        def error_route():
            raise ValueError("test error")

        self.client = self.app.test_client()

    def test_normal_request_passes_through(self):
        resp = self.client.get("/test-ok")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"

    def test_exception_returns_500(self):
        resp = self.client.get("/test-error")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["status"] == "error"
        assert data["error"] == "Internal server error"
        assert data["error_code"] == "INTERNAL_ERROR"

    def test_exception_does_not_leak_details(self):
        resp = self.client.get("/test-error")
        data = resp.get_json()
        # The actual exception message should NOT appear in the response
        assert "test error" not in data["error"]
