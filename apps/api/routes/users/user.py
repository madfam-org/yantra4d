"""
User Blueprint — tier info, current user, and preference endpoints.
"""
import logging

from flask import Blueprint, jsonify, request

from config import Config
from extensions import db
from middleware.auth import optional_auth, require_auth
from services.core.tier_service import load_tiers, resolve_tier, get_tier_limits
from services.core.user_service import get_user_projects
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/tiers", methods=["GET"])
def get_tiers():
    """Public endpoint returning tier definitions."""
    return jsonify(load_tiers())


@user_bp.route("/api/me", methods=["GET"])
@optional_auth
def get_me():
    """Return current user info, tier, and associated projects.

    Anonymous users get guest tier. Authenticated users get their persistent
    user record (upserted from JWT claims) plus associated projects.
    When AUTH_ENABLED=false, returns madfam (all features unlocked).
    """
    if not Config.AUTH_ENABLED:
        return jsonify({
            "tier": "madfam",
            "user": None,
            "projects": [],
            "limits": get_tier_limits("madfam"),
        })

    claims = getattr(request, "auth_claims", None)
    tier = resolve_tier(claims)

    # Use the persistent user record if available (set by auth middleware upsert)
    current_user = getattr(request, "current_user", None)

    user_data = None
    projects = []

    if current_user is not None:
        user_data = current_user.to_dict()
        projects = get_user_projects(current_user)
    elif claims:
        # Fallback: return JWT claims directly if upsert failed
        user_data = {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "display_name": claims.get("name"),
            "tier": tier,
        }

    return jsonify({
        "tier": tier,
        "user": user_data,
        "projects": projects,
        "limits": get_tier_limits(tier),
    })


@user_bp.route("/api/me/preferences", methods=["PATCH"])
@require_auth
def update_preferences():
    """Update the current user's preferences (partial merge).

    Body (JSON): arbitrary key-value pairs to merge into preferences.
    """
    current_user = getattr(request, "current_user", None)
    if current_user is None:
        return error_response("User record not found", 404)

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return error_response("Request body must be a JSON object", 400)

    # Merge into existing preferences
    existing = current_user.preferences or {}
    existing.update(data)
    current_user.preferences = existing

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Failed to update preferences for user=%s", current_user.id)
        return error_response("Failed to save preferences", 500)

    return jsonify({
        "status": "ok",
        "preferences": current_user.preferences,
    })
