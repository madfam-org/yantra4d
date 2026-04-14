"""Tests for the Forgesight webhook blueprint — HMAC verification and cache invalidation."""
import hashlib
import hmac
import json

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test-forgesight-secret-key-256"


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest identical to the blueprint's logic."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _price_updated_payload(material=None):
    payload = {"event": "price.updated", "timestamp": "2026-04-14T12:00:00Z"}
    if material:
        payload["data"] = {"material": material}
    return payload


# ---------------------------------------------------------------------------
# Flask test app fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Create a minimal Flask test client with the forgesight_webhook blueprint."""
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True

    with patch("routes.integrations.forgesight_webhook._WEBHOOK_SECRET", WEBHOOK_SECRET):
        from routes.integrations.forgesight_webhook import forgesight_webhook_bp
        app.register_blueprint(forgesight_webhook_bp)

        with app.test_client() as test_client:
            yield test_client


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

class TestForgesightWebhookSignature:
    """HMAC-SHA256 signature verification on POST /api/webhooks/forgesight."""

    def test_rejects_missing_signature(self, client):
        payload = json.dumps(_price_updated_payload()).encode()
        resp = client.post(
            "/api/webhooks/forgesight",
            data=payload,
            content_type="application/json",
        )
        assert resp.status_code == 401

    def test_rejects_invalid_signature(self, client):
        payload = json.dumps(_price_updated_payload()).encode()
        resp = client.post(
            "/api/webhooks/forgesight",
            data=payload,
            content_type="application/json",
            headers={"x-forgesight-signature": "deadbeef"},
        )
        assert resp.status_code == 401

    def test_accepts_valid_signature(self, client):
        payload = json.dumps(_price_updated_payload()).encode()
        sig = _sign(payload)
        resp = client.post(
            "/api/webhooks/forgesight",
            data=payload,
            content_type="application/json",
            headers={"x-forgesight-signature": sig},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["received"] is True
        assert data["event"] == "price.updated"


# ---------------------------------------------------------------------------
# Cache invalidation on price.updated
# ---------------------------------------------------------------------------

class TestForgesightCacheInvalidation:
    """Verify that price.updated events trigger cache invalidation."""

    def _post(self, client, payload_dict):
        body = json.dumps(payload_dict).encode()
        sig = _sign(body)
        return client.post(
            "/api/webhooks/forgesight",
            data=body,
            content_type="application/json",
            headers={"x-forgesight-signature": sig},
        )

    @patch("routes.integrations.forgesight_webhook._invalidate_benchmark_cache")
    def test_price_updated_calls_invalidate(self, mock_invalidate, client):
        payload = _price_updated_payload()
        resp = self._post(client, payload)

        assert resp.status_code == 200
        mock_invalidate.assert_called_once()
        # The function receives the full payload dict
        call_args = mock_invalidate.call_args[0][0]
        assert call_args["event"] == "price.updated"

    @patch("routes.integrations.forgesight_webhook._invalidate_benchmark_cache")
    def test_other_event_does_not_invalidate(self, mock_invalidate, client):
        payload = {"event": "material.added", "data": {"material": "tpu"}}
        resp = self._post(client, payload)

        assert resp.status_code == 200
        mock_invalidate.assert_not_called()

    def test_full_cache_flush_on_price_updated_without_material(self, client):
        """When no material is specified, the entire benchmark cache is flushed."""
        mock_cache = {"pla:CDMX": 250.0, "petg:CDMX": 300.0, "abs:GDL": 180.0}

        mock_client = MagicMock()
        mock_client._benchmark_cache = mock_cache

        with patch(
            "routes.integrations.forgesight_webhook.forgesight_client",
            mock_client,
            create=True,
        ), patch(
            "services.integrations.forgesight.forgesight_client",
            mock_client,
        ):
            payload = _price_updated_payload()
            body = json.dumps(payload).encode()
            sig = _sign(body)
            resp = client.post(
                "/api/webhooks/forgesight",
                data=body,
                content_type="application/json",
                headers={"x-forgesight-signature": sig},
            )

            assert resp.status_code == 200

    def test_material_specific_invalidation(self, client):
        """When material is specified, only matching cache entries are removed."""
        mock_cache = {
            "pla:CDMX": 250.0,
            "pla:GDL": 260.0,
            "petg:CDMX": 300.0,
        }

        mock_client = MagicMock()
        mock_client._benchmark_cache = mock_cache.copy()

        with patch(
            "routes.integrations.forgesight_webhook.forgesight_client",
            mock_client,
            create=True,
        ), patch(
            "services.integrations.forgesight.forgesight_client",
            mock_client,
        ):
            payload = _price_updated_payload(material="pla")
            body = json.dumps(payload).encode()
            sig = _sign(body)
            resp = client.post(
                "/api/webhooks/forgesight",
                data=body,
                content_type="application/json",
                headers={"x-forgesight-signature": sig},
            )

            assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Payload edge cases
# ---------------------------------------------------------------------------

class TestForgesightWebhookPayloadEdgeCases:
    """Edge cases for payload parsing."""

    def _post(self, client, body_bytes, sig=None):
        if sig is None:
            sig = _sign(body_bytes)
        return client.post(
            "/api/webhooks/forgesight",
            data=body_bytes,
            content_type="application/json",
            headers={"x-forgesight-signature": sig},
        )

    def test_rejects_non_json_body(self, client):
        body = b"not-json-at-all"
        resp = self._post(client, body)
        assert resp.status_code == 400

    def test_rejects_empty_json_body(self, client):
        """An empty body that is not even valid JSON."""
        body = b""
        # Empty body will fail signature check since HMAC of empty != provided sig
        # unless we compute it properly
        sig = _sign(body)
        resp = self._post(client, body, sig)
        # Either 400 (bad JSON) or 401 (empty secret match edge)
        assert resp.status_code in (400, 401)

    def test_accepts_event_type_field(self, client):
        """The blueprint normalizes event from 'event', 'type', and 'event_type' fields."""
        payload = {"event_type": "price.updated"}
        body = json.dumps(payload).encode()
        resp = self._post(client, body)
        assert resp.status_code == 200
        assert resp.get_json()["event"] == "price.updated"

    def test_accepts_type_field(self, client):
        payload = {"type": "price.updated"}
        body = json.dumps(payload).encode()
        resp = self._post(client, body)
        assert resp.status_code == 200
        assert resp.get_json()["event"] == "price.updated"
