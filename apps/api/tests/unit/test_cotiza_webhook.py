"""Tests for the Cotiza webhook blueprint — HMAC verification and event handling."""
import hashlib
import hmac
import json
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test-cotiza-secret-key-256"


def _sign(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 hex digest identical to the blueprint's logic."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def _sample_payload(event_type="quote.completed", project_slug="rugged-box"):
    return {
        "event_type": event_type,
        "quote_id": "cuid_abc123",
        "quote_number": "Q-2026-04-0012",
        "project_slug": project_slug,
        "status": "ordered",
        "total_amount": 1234.56,
        "currency": "MXN",
        "timestamp": "2026-04-14T12:00:00.000Z",
    }


# ---------------------------------------------------------------------------
# Flask test app fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Create a minimal Flask test client with the cotiza_webhook blueprint."""
    from flask import Flask

    app = Flask(__name__)
    app.config["TESTING"] = True

    # Patch the module-level secret before importing the blueprint
    with patch("routes.integrations.cotiza_webhook._WEBHOOK_SECRET", WEBHOOK_SECRET):
        from routes.integrations.cotiza_webhook import cotiza_webhook_bp
        app.register_blueprint(cotiza_webhook_bp)

        with app.test_client() as test_client:
            yield test_client


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

class TestCotizaWebhookSignature:
    """HMAC-SHA256 signature verification on POST /api/webhooks/cotiza."""

    def test_rejects_missing_signature(self, client):
        payload = json.dumps(_sample_payload()).encode()
        resp = client.post(
            "/api/webhooks/cotiza",
            data=payload,
            content_type="application/json",
        )
        assert resp.status_code == 401
        data = resp.get_json()
        assert "Invalid webhook signature" in data["error"]

    def test_rejects_bad_signature(self, client):
        payload = json.dumps(_sample_payload()).encode()
        resp = client.post(
            "/api/webhooks/cotiza",
            data=payload,
            content_type="application/json",
            headers={"x-cotiza-signature": "bad_signature_value"},
        )
        assert resp.status_code == 401

    def test_rejects_wrong_secret_signature(self, client):
        payload = json.dumps(_sample_payload()).encode()
        wrong_sig = _sign(payload, secret="wrong-secret-entirely")
        resp = client.post(
            "/api/webhooks/cotiza",
            data=payload,
            content_type="application/json",
            headers={"x-cotiza-signature": wrong_sig},
        )
        assert resp.status_code == 401

    def test_accepts_valid_signature(self, client):
        payload = json.dumps(_sample_payload()).encode()
        sig = _sign(payload)
        with patch("routes.integrations.cotiza_webhook._persist_audit_event") as mock_audit:
            mock_audit.return_value = {"persisted": True, "store": "analytics_events"}
            resp = client.post(
                "/api/webhooks/cotiza",
                data=payload,
                content_type="application/json",
                headers={"x-cotiza-signature": sig},
            )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["received"] is True
        assert data["event"] == "quote.completed"
        assert data["market_verified"] is False
        assert data["provenance"]["source"] == "cotiza"
        assert data["audit"]["persisted"] is True

    def test_signature_is_body_sensitive(self, client):
        """Changing the body must invalidate the original signature."""
        original_payload = json.dumps(_sample_payload()).encode()
        sig = _sign(original_payload)

        # Send different body with the same signature
        tampered = json.dumps({**_sample_payload(), "total_amount": 0}).encode()
        resp = client.post(
            "/api/webhooks/cotiza",
            data=tampered,
            content_type="application/json",
            headers={"x-cotiza-signature": sig},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------

class TestCotizaWebhookPayload:
    """Request body validation after signature passes."""

    def _post(self, client, payload_dict):
        body = json.dumps(payload_dict).encode()
        sig = _sign(body)
        return client.post(
            "/api/webhooks/cotiza",
            data=body,
            content_type="application/json",
            headers={"x-cotiza-signature": sig},
        )

    def test_rejects_non_json_body(self, client):
        body = b"not json"
        sig = _sign(body)
        resp = client.post(
            "/api/webhooks/cotiza",
            data=body,
            content_type="application/json",
            headers={"x-cotiza-signature": sig},
        )
        assert resp.status_code == 400

    def test_rejects_missing_event_type(self, client):
        payload = _sample_payload()
        del payload["event_type"]
        resp = self._post(client, payload)
        assert resp.status_code == 400

    def test_rejects_missing_project_slug(self, client):
        payload = _sample_payload()
        del payload["project_slug"]
        resp = self._post(client, payload)
        assert resp.status_code == 400

    def test_accepts_quote_completed(self, client):
        resp = self._post(client, _sample_payload("quote.completed"))
        assert resp.status_code == 200
        assert resp.get_json()["event"] == "quote.completed"

    def test_accepts_quote_approved(self, client):
        resp = self._post(client, _sample_payload("quote.approved"))
        assert resp.status_code == 200
        assert resp.get_json()["event"] == "quote.approved"

    def test_accepts_quote_cancelled(self, client):
        resp = self._post(client, _sample_payload("quote.cancelled"))
        assert resp.status_code == 200
        assert resp.get_json()["event"] == "quote.cancelled"

    def test_accepts_unrecognized_event_type(self, client):
        """Unknown events should not 400 — they are logged and acked."""
        resp = self._post(client, _sample_payload("quote.unknown_future_event"))
        assert resp.status_code == 200
        assert resp.get_json()["received"] is True

    def test_response_echoes_project_slug(self, client):
        resp = self._post(client, _sample_payload(project_slug="my-project"))
        data = resp.get_json()
        assert data["project_slug"] == "my-project"

    @patch("routes.integrations.cotiza_webhook._persist_audit_event")
    def test_attempts_audit_persistence(self, mock_audit, client):
        mock_audit.return_value = {"persisted": True, "store": "analytics_events"}
        resp = self._post(client, _sample_payload("quote.approved"))
        assert resp.status_code == 200
        mock_audit.assert_called_once()
        assert resp.get_json()["audit"]["store"] == "analytics_events"


# ---------------------------------------------------------------------------
# Quote projection (idempotency + order state)
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_client():
    """Flask client with a real in-memory DB so the projection actually writes."""
    from flask import Flask

    from extensions import db

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    with patch("routes.integrations.cotiza_webhook._WEBHOOK_SECRET", WEBHOOK_SECRET):
        from routes.integrations.cotiza_webhook import cotiza_webhook_bp
        app.register_blueprint(cotiza_webhook_bp)

        with app.app_context():
            import models  # noqa: F401 — register all models
            db.create_all()
            with app.test_client() as test_client:
                yield test_client
            db.session.remove()


def _post(client, payload_dict):
    body = json.dumps(payload_dict).encode()
    return client.post(
        "/api/webhooks/cotiza",
        data=body,
        content_type="application/json",
        headers={"x-cotiza-signature": _sign(body)},
    )


class TestCotizaQuoteProjection:
    """quote.completed used to be handled by a log line. These pin the ledger."""

    def test_completed_event_creates_ledger_row_and_projection(self, db_client):
        from decimal import Decimal

        from models.quote import CotizaQuote, CotizaQuoteEvent

        resp = _post(db_client, _sample_payload())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["projection"]["projected"] is True
        assert data["duplicate"] is False

        events = CotizaQuoteEvent.query.all()
        assert len(events) == 1
        assert events[0].quote_id == "cuid_abc123"
        # Money survives as an exact decimal, not a float.
        assert events[0].total_amount == Decimal("1234.56")

        from extensions import db as _db
        quote = _db.session.get(CotizaQuote, "cuid_abc123")
        assert quote is not None
        assert quote.status == "ordered"
        assert quote.total_amount == Decimal("1234.56")
        assert quote.currency == "MXN"

    def test_identical_redelivery_is_a_noop_ack(self, db_client):
        from models.quote import CotizaQuoteEvent

        payload = _sample_payload()
        first = _post(db_client, payload)
        second = _post(db_client, payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.get_json()["duplicate"] is True
        # One delivery, one ledger row — a provider retry cannot double-count.
        assert CotizaQuoteEvent.query.count() == 1

    def test_later_event_updates_the_projection(self, db_client):
        from models.quote import CotizaQuote, CotizaQuoteEvent

        _post(db_client, _sample_payload(event_type="quote.approved"))
        cancelled = _sample_payload(event_type="quote.cancelled")
        cancelled["status"] = "cancelled"
        cancelled["timestamp"] = "2026-04-15T09:00:00.000Z"
        _post(db_client, cancelled)

        assert CotizaQuoteEvent.query.count() == 2
        from extensions import db as _db
        quote = _db.session.get(CotizaQuote, "cuid_abc123")
        assert quote.status == "cancelled"
        assert quote.last_event_type == "quote.cancelled"

    def test_missing_quote_id_is_acked_but_not_projected(self, db_client):
        from models.quote import CotizaQuoteEvent

        payload = _sample_payload()
        payload.pop("quote_id")
        resp = _post(db_client, payload)

        assert resp.status_code == 200
        assert resp.get_json()["projection"]["projected"] is False
        assert CotizaQuoteEvent.query.count() == 0

    def test_garbage_amount_projects_with_null_amount(self, db_client):
        from models.quote import CotizaQuote

        payload = _sample_payload()
        payload["total_amount"] = "not-a-number"
        resp = _post(db_client, payload)

        assert resp.status_code == 200
        from extensions import db as _db
        quote = _db.session.get(CotizaQuote, "cuid_abc123")
        assert quote is not None
        assert quote.total_amount is None

