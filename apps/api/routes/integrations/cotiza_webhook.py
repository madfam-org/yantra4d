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
import logging
import os

from flask import Blueprint, request, jsonify

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


@cotiza_webhook_bp.route("/api/webhooks/cotiza", methods=["POST"])
def handle_cotiza_webhook():
    """Receive and process Cotiza quote lifecycle webhooks.

    On a valid event, logs the quote result associated with the project.
    Persistence is deferred to a future release -- for now, logging
    provides an audit trail and confirms the integration works.

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

    return jsonify({
        "received": True,
        "event": event_type,
        "project_slug": project_slug,
    }), 200


def _handle_quote_completed(payload: dict) -> None:
    """Handle a completed quote from Cotiza.

    Future: persist the quote result to the project's metadata or a
    dedicated quotes table so the Yantra4D studio can display pricing
    history and order status.
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
