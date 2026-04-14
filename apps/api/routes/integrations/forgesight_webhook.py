"""
Forgesight Webhook Blueprint

Receives price.updated events from Forgesight's webhook feed.
Verifies HMAC-SHA256 signature and invalidates the local benchmark cache
so that the next pricing request fetches fresh data.

Endpoint: POST /api/webhooks/forgesight

Headers:
    x-forgesight-signature: HMAC-SHA256 hex digest of the raw request body

Environment:
    FORGESIGHT_WEBHOOK_SECRET: Shared secret for signature verification
"""
import hashlib
import hmac
import logging
import os

from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

forgesight_webhook_bp = Blueprint("forgesight_webhook", __name__)

_WEBHOOK_SECRET = os.getenv("FORGESIGHT_WEBHOOK_SECRET", "")


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


@forgesight_webhook_bp.route("/api/webhooks/forgesight", methods=["POST"])
def handle_forgesight_webhook():
    """Receive and process Forgesight price update webhooks.

    On a valid ``price.updated`` event, clears the in-memory benchmark
    cache in the global ``forgesight_client`` singleton so the next call
    to ``get_material_benchmark()`` fetches live data from the API.

    Returns 200 on success, 401 on signature failure, 400 on bad payload.
    """
    signature = request.headers.get("x-forgesight-signature")
    raw_body = request.get_data()

    if not _verify_signature(raw_body, signature):
        logger.warning("Forgesight webhook signature verification failed")
        return jsonify({"error": "Invalid webhook signature"}), 401

    try:
        payload = request.get_json(silent=True)
    except Exception:
        payload = None

    if not payload or not isinstance(payload, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    event_type = payload.get("event") or payload.get("type") or payload.get("event_type")

    logger.info("Forgesight webhook received: event=%s", event_type)

    if event_type == "price.updated":
        _invalidate_benchmark_cache(payload)

    return jsonify({"received": True, "event": event_type}), 200


def _invalidate_benchmark_cache(payload: dict) -> None:
    """Clear cached ForgeSight benchmark data.

    If the payload includes a ``material`` field, only that specific
    cache entry is removed.  Otherwise the entire benchmark cache is
    flushed so all materials pick up fresh prices on next request.
    """
    from services.integrations.forgesight import forgesight_client

    material = (payload.get("data") or {}).get("material")

    if material:
        # Invalidate specific material across all regions
        keys_to_remove = [
            key for key in forgesight_client._benchmark_cache
            if key.startswith(f"{material}:")
        ]
        for key in keys_to_remove:
            del forgesight_client._benchmark_cache[key]
        logger.info(
            "Forgesight cache invalidated for material=%s (%d entries removed)",
            material,
            len(keys_to_remove),
        )
    else:
        count = len(forgesight_client._benchmark_cache)
        forgesight_client._benchmark_cache.clear()
        logger.info("Forgesight cache fully invalidated (%d entries removed)", count)
