"""
User Blueprint — tier info and current user endpoints.
"""
from flask import Blueprint, jsonify, request

from config import Config
from middleware.auth import optional_auth
from services.core.tier_service import load_tiers, resolve_tier, get_tier_limits

user_bp = Blueprint("user", __name__)


@user_bp.route("/api/tiers", methods=["GET"])
def get_tiers():
    """Public endpoint returning tier definitions."""
    return jsonify(load_tiers())


@user_bp.route("/api/me", methods=["GET"])
@optional_auth
def get_me():
    """Return current user info and tier.

    Anonymous users get guest tier. Authenticated users get their JWT tier.
    When AUTH_ENABLED=false, returns madfam (all features unlocked).
    """
    if not Config.AUTH_ENABLED:
        return jsonify({
            "tier": "madfam",
            "user": None,
            "limits": get_tier_limits("madfam"),
        })

    claims = getattr(request, "auth_claims", None)
    tier = resolve_tier(claims)
    user = None
    if claims:
        user = {
            "sub": claims.get("sub"),
            "email": claims.get("email"),
            "name": claims.get("name"),
        }

    return jsonify({
        "tier": tier,
        "user": user,
        "limits": get_tier_limits(tier),
    })
