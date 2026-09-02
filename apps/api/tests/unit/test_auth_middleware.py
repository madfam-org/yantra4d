"""Tests for JWT auth middleware."""
from unittest.mock import patch

import pytest
from flask import Flask

from middleware.auth import optional_auth, require_auth, require_role


@pytest.fixture(autouse=True)
def _enable_auth(monkeypatch):
    """Auth middleware tests need AUTH_ENABLED=True (conftest disables it globally)."""
    from config import Config
    monkeypatch.setattr(Config, "AUTH_ENABLED", True)


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    @app.route("/protected")
    @require_auth
    def protected():
        from flask import jsonify, request
        return jsonify({"claims": getattr(request, "auth_claims", None)})

    @app.route("/admin")
    @require_role("admin")
    def admin():
        from flask import jsonify
        return jsonify({"ok": True})

    @app.route("/optional")
    @optional_auth
    def optional():
        from flask import jsonify, request
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


# ──────────────────────────────────────────────
# JWKS stale-while-revalidate
# ──────────────────────────────────────────────


class _StubJwksEndpoint:
    """Stands in for PyJWKClient: returns `result`, or raises it if it is an error."""

    def __init__(self, result):
        self.result = result
        self.calls = 0

    def fetch_data(self):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture(scope="module")
def rsa_key():
    from cryptography.hazmat.primitives.asymmetric import rsa

    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _jwks_document(private_key, kid):
    import json

    from jwt.algorithms import RSAAlgorithm

    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return {"keys": [jwk]}


def _sign(private_key, kid):
    import time

    import jwt as pyjwt

    from config import Config

    return pyjwt.encode(
        {
            "sub": "user123",
            "iss": Config.JANUA_ISSUER,
            "aud": Config.JANUA_AUDIENCE,
            "exp": int(time.time()) + 3600,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


class TestJwksStaleWhileRevalidate:
    """A Janua outage must not take down authenticated traffic.

    Before this, PyJWKClient re-fetched the moment its 1 h cache expired and a
    failed fetch raised straight through `decode_token` — every bearer rejected
    over a signing key that had not changed.
    """

    @pytest.fixture(autouse=True)
    def _clean_cache(self):
        from middleware.auth import reset_jwks_cache

        reset_jwks_cache()
        yield
        reset_jwks_cache()

    @pytest.fixture
    def endpoint(self, rsa_key, monkeypatch):
        stub = _StubJwksEndpoint(_jwks_document(rsa_key, "k1"))
        monkeypatch.setattr("middleware.auth._get_jwk_client", lambda: stub)
        return stub

    def test_fresh_cache_is_served_without_refetching(self, endpoint, rsa_key):
        from middleware.auth import decode_token

        token = _sign(rsa_key, "k1")
        assert decode_token(token)["sub"] == "user123"
        assert decode_token(token)["sub"] == "user123"
        assert endpoint.calls == 1

    def test_warm_cache_still_validates_when_refresh_fails(
        self, endpoint, rsa_key, monkeypatch, caplog
    ):
        """The core of the fix: expired cache + dead IdP -> tokens still validate."""
        from jwt.exceptions import PyJWKClientConnectionError

        from config import Config
        from middleware.auth import _jwks_cache, decode_token

        token = _sign(rsa_key, "k1")
        assert decode_token(token)["sub"] == "user123"

        monkeypatch.setattr(Config, "JWKS_CACHE_LIFESPAN", 0)
        monkeypatch.setattr(Config, "JWKS_REFRESH_BACKOFF", 0)
        endpoint.result = PyJWKClientConnectionError("Janua is down")

        with caplog.at_level("WARNING"):
            assert decode_token(token)["sub"] == "user123"

        assert endpoint.calls == 2
        assert _jwks_cache.stale is True
        assert "Janua is down" in caplog.text
        assert "last-known-good" in caplog.text

    def test_cold_cache_failure_fails_closed(self, endpoint, rsa_key):
        """No key set was ever fetched, so there is nothing safe to fall back to."""
        from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

        from middleware.auth import decode_token

        endpoint.result = PyJWKClientConnectionError("Janua is down")

        with pytest.raises(PyJWKClientError, match="has ever been cached"):
            decode_token(_sign(rsa_key, "k1"))

    def test_cold_cache_failure_is_401_on_the_wire(self, endpoint, rsa_key, client):
        """Unchanged from before the SWR cache: the request 401s, it does not 500."""
        from jwt.exceptions import PyJWKClientConnectionError

        endpoint.result = PyJWKClientConnectionError("Janua is down")

        resp = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {_sign(rsa_key, 'k1')}"},
        )
        assert resp.status_code == 401

    def test_unknown_kid_triggers_a_refresh(self, endpoint, rsa_key, monkeypatch):
        """A kid missing from the cached set is what a key rotation looks like."""
        from config import Config
        from middleware.auth import decode_token

        monkeypatch.setattr(Config, "JWKS_REFRESH_BACKOFF", 0)
        assert decode_token(_sign(rsa_key, "k1"))["sub"] == "user123"

        endpoint.result = _jwks_document(rsa_key, "k2")
        assert decode_token(_sign(rsa_key, "k2"))["sub"] == "user123"
        assert endpoint.calls == 2

    def test_unknown_kid_refreshes_against_a_stale_set(
        self, endpoint, rsa_key, monkeypatch
    ):
        from jwt.exceptions import PyJWKClientConnectionError

        from config import Config
        from middleware.auth import _jwks_cache, decode_token

        monkeypatch.setattr(Config, "JWKS_CACHE_LIFESPAN", 0)
        monkeypatch.setattr(Config, "JWKS_REFRESH_BACKOFF", 0)

        token_k1 = _sign(rsa_key, "k1")
        assert decode_token(token_k1)["sub"] == "user123"

        endpoint.result = PyJWKClientConnectionError("Janua is down")
        assert decode_token(token_k1)["sub"] == "user123"
        assert _jwks_cache.stale is True

        calls_before = endpoint.calls
        endpoint.result = _jwks_document(rsa_key, "k2")
        assert decode_token(_sign(rsa_key, "k2"))["sub"] == "user123"
        assert endpoint.calls > calls_before
        assert _jwks_cache.stale is False

    def test_backoff_stops_a_flapping_idp_being_hammered(
        self, endpoint, rsa_key, monkeypatch
    ):
        from jwt.exceptions import PyJWKClientConnectionError

        from config import Config
        from middleware.auth import decode_token

        token = _sign(rsa_key, "k1")
        assert decode_token(token)["sub"] == "user123"

        monkeypatch.setattr(Config, "JWKS_CACHE_LIFESPAN", 0)
        monkeypatch.setattr(Config, "JWKS_REFRESH_BACKOFF", 3600)
        endpoint.result = PyJWKClientConnectionError("Janua is down")

        for _ in range(5):
            assert decode_token(token)["sub"] == "user123"
        assert endpoint.calls == 2

    def test_stale_ceiling_eventually_fails_closed(self, endpoint, rsa_key, monkeypatch):
        """Keys nobody has re-confirmed for a day stop being trusted."""
        from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

        from config import Config
        from middleware.auth import decode_token

        token = _sign(rsa_key, "k1")
        assert decode_token(token)["sub"] == "user123"

        monkeypatch.setattr(Config, "JWKS_CACHE_LIFESPAN", 0)
        monkeypatch.setattr(Config, "JWKS_REFRESH_BACKOFF", 0)
        monkeypatch.setattr(Config, "JWKS_STALE_MAX_AGE", -1)
        endpoint.result = PyJWKClientConnectionError("Janua is down")

        with pytest.raises(PyJWKClientError, match="stale ceiling"):
            decode_token(token)

    def test_recovered_refresh_clears_the_stale_flag(self, endpoint, rsa_key, monkeypatch):
        from jwt.exceptions import PyJWKClientConnectionError

        from config import Config
        from middleware.auth import _jwks_cache, decode_token

        token = _sign(rsa_key, "k1")
        assert decode_token(token)["sub"] == "user123"

        monkeypatch.setattr(Config, "JWKS_CACHE_LIFESPAN", 0)
        monkeypatch.setattr(Config, "JWKS_REFRESH_BACKOFF", 0)
        endpoint.result = PyJWKClientConnectionError("Janua is down")
        assert decode_token(token)["sub"] == "user123"
        assert _jwks_cache.stale is True

        endpoint.result = _jwks_document(rsa_key, "k1")
        assert decode_token(token)["sub"] == "user123"
        assert _jwks_cache.stale is False
        assert _jwks_cache.last_error is None
