import json
import logging
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify

from config import Config
from middleware.auth import decode_token
from services.core.tier_service import has_tier, resolve_tier
from utils.route_helpers import handle_exceptions

logger = logging.getLogger(__name__)

client_config_bp = Blueprint("client_config", __name__)

# Offline license cache — persists validated license to disk so JWKS
# outages don't break branding for up to 24 hours.
LICENSE_CACHE_PATH = Path(os.getenv(
    "LICENSE_CACHE_PATH",
    str(Config.DATA_DIR / "license_cache.json"),
))
LICENSE_CACHE_MAX_AGE = 86400  # 24 hours

# Strict mode — when true, return 403 instead of defaults on validation failure
LICENSE_REQUIRED = os.getenv("YANTRA4D_LICENSE_REQUIRED", "false").lower() == "true"


def _read_cache() -> dict | None:
    """Read cached license validation result if fresh enough."""
    try:
        if not LICENSE_CACHE_PATH.exists():
            return None
        data = json.loads(LICENSE_CACHE_PATH.read_text())
        validated_at = data.get("validated_at", 0)
        if time.time() - validated_at > LICENSE_CACHE_MAX_AGE:
            return None
        return data
    except Exception:
        return None


def _write_cache(claims: dict, tier: str, tenant_id: str | None) -> None:
    """Write validated license result to disk cache."""
    try:
        LICENSE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LICENSE_CACHE_PATH.write_text(json.dumps({
            "validated_at": time.time(),
            "tier": tier,
            "tenant_id": tenant_id,
            "platform_name": Config.PLATFORM_NAME,
            "platform_logo": Config.PLATFORM_LOGO,
        }))
    except Exception as e:
        logger.debug("Failed to write license cache: %s", e)


@client_config_bp.route("/api/config/client", methods=["GET"])
@handle_exceptions
def get_client_config():
    """
    Return runtime configuration for the frontend React app.
    Verifies YANTRA4D_LICENSE_KEY (JWT) to authorize custom platform branding.
    If license is missing or < Pro tier, falls back to "Yantra4D".

    Features:
    - Offline cache: uses cached validation when JWKS is unreachable (24h TTL)
    - Strict mode: returns 403 when LICENSE_REQUIRED=true and validation fails
    - Tenant namespace: extracts tenant_id from JWT for localStorage namespacing
    """
    platform_name = "Yantra4D"
    platform_logo = "/logo.png"
    tenant_id = None

    license_key = Config.YANTRA4D_LICENSE_KEY

    if license_key:
        try:
            # decode_token fetches the dynamic Janua JWKS and verifies the signature + expiry
            claims = decode_token(license_key)
            user_tier = resolve_tier(claims)
            tenant_id = claims.get("tenant_id") or claims.get("org_id")

            # Only allow white-label override for paying tiers (pro/madfam)
            if has_tier(user_tier, "pro"):
                platform_name = Config.PLATFORM_NAME
                platform_logo = Config.PLATFORM_LOGO
                # Cache successful validation
                _write_cache(claims, user_tier, tenant_id)
            else:
                logger.info("License key valid but tier too low for white-labeling.")
        except Exception as e:
            logger.warning("License key JWT validation failed: %s", e)

            # Try offline cache if JWKS validation failed
            cached = _read_cache()
            if cached and has_tier(cached.get("tier", "guest"), "pro"):
                logger.info("Using cached license validation (age: %ds)",
                            int(time.time() - cached.get("validated_at", 0)))
                platform_name = cached.get("platform_name", platform_name)
                platform_logo = cached.get("platform_logo", platform_logo)
                tenant_id = cached.get("tenant_id")
            elif LICENSE_REQUIRED:
                return jsonify({
                    "error": "License validation failed and is required",
                }), 403

    elif LICENSE_REQUIRED:
        return jsonify({
            "error": "YANTRA4D_LICENSE_KEY is required but not set",
        }), 403

    response = {
        "platformName": platform_name,
        "platformLogo": platform_logo,
    }
    if tenant_id:
        response["tenantId"] = tenant_id

    return jsonify(response)
