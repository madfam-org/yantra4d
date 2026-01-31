"""Tests for JWT auth middleware."""
import json
from unittest.mock import patch, MagicMock

import pytest
from flask import Flask

from middleware.auth import require_auth, require_role, optional_auth, decode_token


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/protected")
    @require_auth
    def protected():
        from flask import request, jsonify
        return jsonify({"claims": getattr(request, "auth_claims", None)})

    @app.route("/admin")
    @require_role("admin")
    def admin():
        from flask import jsonify
        return jsonify({"ok": True})

    @app.route("/optional")
    @optional_auth
    def optional():
        from flask import request, jsonify
        return jsonify({"claims": getattr(request, "auth_claims", None)})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


MOCK_CLAIMS = {"sub": "user123", "iss": "https://auth.madfam.io", "roles": ["user"], "exp": 9999999999}
ADMIN_CLAIMS = {"sub": "admin1", "iss": "https://auth.madfam.io", "roles": ["admin"], "exp": 9999999999}


class TestRequireAuth:
    def test_returns_401_without_token(self, client):
        resp = client.get("/protected")
        assert resp.status_code == 401
        assert "Authentication required" in resp.get_json()["error"]

    def test_returns_401_with_invalid_token(self, client):
        with patch("middleware.auth.decode_token", side_effect=Exception("bad")):
            resp = client.get("/protected", headers={"Authorization": "Bearer bad.token.here"})
            assert resp.status_code == 401

    def test_passes_with_valid_token(self, client):
        with patch("middleware.auth.decode_token", return_value=MOCK_CLAIMS):
            resp = client.get("/protected", headers={"Authorization": "Bearer valid.token"})
            assert resp.status_code == 200
            assert resp.get_json()["claims"]["sub"] == "user123"


class TestRequireRole:
    def test_returns_403_when_role_missing(self, client):
        with patch("middleware.auth.decode_token", return_value=MOCK_CLAIMS):
            resp = client.get("/admin", headers={"Authorization": "Bearer valid.token"})
            assert resp.status_code == 403
            assert "Insufficient permissions" in resp.get_json()["error"]

    def test_passes_with_correct_role(self, client):
        with patch("middleware.auth.decode_token", return_value=ADMIN_CLAIMS):
            resp = client.get("/admin", headers={"Authorization": "Bearer admin.token"})
            assert resp.status_code == 200


class TestOptionalAuth:
    def test_sets_none_for_anonymous(self, client):
        resp = client.get("/optional")
        assert resp.status_code == 200
        assert resp.get_json()["claims"] is None

    def test_sets_claims_when_valid_token_present(self, client):
        with patch("middleware.auth.decode_token", return_value=MOCK_CLAIMS):
            resp = client.get("/optional", headers={"Authorization": "Bearer valid.token"})
            assert resp.status_code == 200
            assert resp.get_json()["claims"]["sub"] == "user123"

    def test_sets_none_for_invalid_token(self, client):
        with patch("middleware.auth.decode_token", side_effect=Exception("bad")):
            resp = client.get("/optional", headers={"Authorization": "Bearer bad.token"})
            assert resp.status_code == 200
            assert resp.get_json()["claims"] is None


class TestAuthDisabled:
    """When AUTH_ENABLED=false, decorators become no-ops."""

    def test_require_auth_noop(self, client):
        with patch("middleware.auth.Config") as mock_config:
            mock_config.AUTH_ENABLED = False
            resp = client.get("/protected")
            assert resp.status_code == 200

    def test_require_role_noop(self, client):
        with patch("middleware.auth.Config") as mock_config:
            mock_config.AUTH_ENABLED = False
            resp = client.get("/admin")
            assert resp.status_code == 200
