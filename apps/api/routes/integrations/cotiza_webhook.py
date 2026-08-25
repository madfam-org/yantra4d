"""
Cotiza Webhook Blueprint

Receives quote lifecycle events from Cotiza (digifab-quoting).
Verifies HMAC-SHA256 signature and logs the event.

Endpoint: POST /api/webhooks/cotiza

Headers:
    x-cotiza-signature: HMAC-SHA256 hex digest of the raw request body

Environment:
    COTIZA_WEBHOOK_SECRET: Shared secret for signature verification

Event types:
    quote.completed  -- Quote has been paid and ordered
    quote.approved   -- Quote has been approved by the customer
    quote.cancelled  -- Quote has been cancelled

Payload:
    {
        "event_type": "quote.completed",
        "quote_id": "cuid...",
        "quote_number": "Q-2026-04-0012",
        "project_slug": "my-project",
        "status": "ordered",
        "total_amount": 1234.56,
        "currency": "MXN",
        "timestamp": "2026-04-14T12:00:00.000Z"
    }
"""
import hashlib
import hmac
import json
import logging
import os
import time
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request

from extensions import db
from models.analytics import AnalyticsEvent
from models.quote import CotizaQuote, CotizaQuoteEvent

logger = logging.getLogger(__name__)

cotiza_webhook_bp = Blueprint("cotiza_webhook", __name__)

_WEBHOOK_SECRET = os.getenv("COTIZA_WEBHOOK_SECRET", "")


def _verify_signature(payload: bytes, signature: str | None) -> bool:
    """Verify HMAC-SHA256 signature using timing-safe comparison."""
    if not _WEBHOOK_SECRET or not signature:
        return False

    expected = hmac.new(
        _WEBHOOK_SECRET.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(signature, expected)


def _parse_amount(value) -> Decimal | None:
    """Coerce a webhook amount into Decimal, or None when absent/garbage.

    Money goes through str() first so a float like 1234.56 doesn't drag its
    binary representation error into the Decimal.
    """
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _project_quote_event(raw_body: bytes, payload: dict) -> dict:
    """Idempotently record the event and update the per-quote projection.

    Deduplication key is a hash of the raw body: a provider retry or a
    replayed request carries identical bytes and becomes a no-op ACK instead
    of a double-counted order. A changed body (e.g. a later event for the
    same quote) is a new ledger row, and the projection takes its values —
    last received wins, with Cotiza's own timestamp preserved for audit.

    Returns a dict describing what happened; never raises. When the DB is
    unavailable the webhook still ACKs (Cotiza should not retry forever
    because our analytics store is down) and the outcome says so.
    """
    event_key = hashlib.sha256(raw_body).hexdigest()
    quote_id = str(payload.get("quote_id") or "")
    if not quote_id:
        return {"projected": False, "reason": "missing_quote_id"}

    try:
        existing = CotizaQuoteEvent.query.filter_by(event_key=event_key).first()
        if existing is not None:
            return {"projected": False, "duplicate": True, "event_id": existing.id}

        amount = _parse_amount(payload.get("total_amount"))
        event = CotizaQuoteEvent(
            event_key=event_key,
            event_type=payload.get("event_type", "unknown"),
            quote_id=quote_id,
            quote_number=payload.get("quote_number"),
            project_slug=payload.get("project_slug"),
            status=payload.get("status"),
            total_amount=amount,
            currency=payload.get("currency"),
            event_timestamp=payload.get("timestamp"),
            raw=raw_body.decode("utf-8", errors="replace"),
        )
        db.session.add(event)

        quote = db.session.get(CotizaQuote, quote_id)
        if quote is None:
            quote = CotizaQuote(quote_id=quote_id)
            db.session.add(quote)
        quote.quote_number = payload.get("quote_number") or quote.quote_number
        quote.project_slug = payload.get("project_slug") or quote.project_slug
        quote.status = payload.get("status") or quote.status
        if amount is not None:
            quote.total_amount = amount
        quote.currency = payload.get("currency") or quote.currency
        quote.last_event_type = payload.get("event_type")
        quote.updated_at = db.func.current_timestamp()

        db.session.commit()
        return {"projected": True, "duplicate": False, "quote_id": quote_id}
    except Exception as exc:
        logger.warning("Cotiza quote projection skipped: %s", exc)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {"projected": False, "reason": "quote_store_unavailable"}


def _persist_audit_event(payload: dict) -> dict:
    """Persist a lightweight Cotiza lifecycle audit event when DB is available."""
    event_type = payload.get("event_type", "unknown")
    project_slug = payload.get("project_slug", "unknown")
    audit_data = {
        "provider": "cotiza",
        "quote_id": payload.get("quote_id", ""),
        "quote_number": payload.get("quote_number", ""),
        "status": payload.get("status", ""),
        "total_amount": payload.get("total_amount", 0),
        "currency": payload.get("currency", "MXN"),
        "timestamp": payload.get("timestamp", ""),
        "source": payload.get("source", "cotiza"),
        "market_verified": bool(payload.get("market_verified", False)),
        "fallback_reason": payload.get(
            "fallback_reason",
            "Lifecycle webhook only; Yantra4D did not independently verify market pricing.",
        ),
    }

    try:
        event = AnalyticsEvent(
            project=project_slug,
            event_type=f"cotiza.{event_type}",
            event_data=json.dumps(audit_data),
            created_at=time.time(),
        )
        db.session.add(event)
        db.session.commit()
        return {
            "persisted": True,
            "store": "analytics_events",
            "event_type": event.event_type,
        }
    except Exception as exc:
        logger.warning("Cotiza webhook audit persistence skipped: %s", exc)
        try:
            db.session.rollback()
        except Exception:
            pass
        return {
            "persisted": False,
            "store": "analytics_events",
            "reason": "audit_store_unavailable",
        }


@cotiza_webhook_bp.route("/api/webhooks/cotiza", methods=["POST"])
def handle_cotiza_webhook():
    """Receive and process Cotiza quote lifecycle webhooks.

    On a valid event, logs the quote result associated with the project and
    attempts a lightweight local audit write using the analytics events table.

    Returns 200 on success, 401 on signature failure, 400 on bad payload.
    """
    signature = request.headers.get("x-cotiza-signature")
    raw_body = request.get_data()

    if not _verify_signature(raw_body, signature):
        logger.warning("Cotiza webhook signature verification failed")
        return jsonify({"error": "Invalid webhook signature"}), 401

    try:
        payload = request.get_json(silent=True)
    except Exception:
        payload = None

    if not payload or not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    event_type = payload.get("event_type", "")
    project_slug = payload.get("project_slug", "")
    quote_id = payload.get("quote_id", "")
    quote_number = payload.get("quote_number", "")
    status = payload.get("status", "")
    total_amount = payload.get("total_amount", 0)
    currency = payload.get("currency", "MXN")
    timestamp = payload.get("timestamp", "")

    if not event_type or not project_slug:
        return jsonify({"error": "Missing required fields: event_type, project_slug"}), 400

    logger.info(
        "Cotiza webhook received: event=%s project=%s quote=%s number=%s "
        "status=%s amount=%s %s timestamp=%s",
        event_type,
        project_slug,
        quote_id,
        quote_number,
        status,
        total_amount,
        currency,
        timestamp,
    )

    if event_type == "quote.completed":
        _handle_quote_completed(payload)
    elif event_type == "quote.approved":
        _handle_quote_approved(payload)
    elif event_type == "quote.cancelled":
        _handle_quote_cancelled(payload)
    else:
        logger.debug("Cotiza webhook: unrecognized event_type=%s", event_type)

    projection = _project_quote_event(raw_body, payload)
    audit = _persist_audit_event(payload)

    return jsonify({
        "received": True,
        "event": event_type,
        "project_slug": project_slug,
        "source": "cotiza",
        "provenance": {
            "source": "cotiza",
            "market_verified": bool(payload.get("market_verified", False)),
            "fallback_reason": payload.get(
                "fallback_reason",
                "Lifecycle webhook only; Yantra4D did not independently verify market pricing.",
            ),
        },
        "market_verified": bool(payload.get("market_verified", False)),
        "fallback_reason": payload.get(
            "fallback_reason",
            "Lifecycle webhook only; Yantra4D did not independently verify market pricing.",
        ),
        "audit": audit,
        "projection": projection,
        "duplicate": bool(projection.get("duplicate", False)),
    }), 200


def _handle_quote_completed(payload: dict) -> None:
    """Handle a completed quote from Cotiza.

    The generic webhook handler persists a lightweight audit event after
    lifecycle-specific logging. A dedicated quote table can later project
    these events into queryable quote/order state.
    """
    logger.info(
        "Cotiza quote completed for project '%s': quote_number=%s total=%s %s",
        payload.get("project_slug"),
        payload.get("quote_number"),
        payload.get("total_amount"),
        payload.get("currency"),
    )


def _handle_quote_approved(payload: dict) -> None:
    """Handle an approved (but not yet paid) quote."""
    logger.info(
        "Cotiza quote approved for project '%s': quote_number=%s",
        payload.get("project_slug"),
        payload.get("quote_number"),
    )


def _handle_quote_cancelled(payload: dict) -> None:
    """Handle a cancelled quote."""
    logger.info(
        "Cotiza quote cancelled for project '%s': quote_number=%s",
        payload.get("project_slug"),
        payload.get("quote_number"),
    )
