import logging
from flask import Blueprint, jsonify
from config import Config
from middleware.auth import decode_token
from services.core.tier_service import resolve_tier, has_tier

logger = logging.getLogger(__name__)

client_config_bp = Blueprint("client_config", __name__)

@client_config_bp.route("/api/config/client", methods=["GET"])
def get_client_config():
    """
    Return runtime configuration for the frontend React app.
    Verifies YANTRA4D_LICENSE_KEY (JWT) to authorize custom platform branding.
    If license is missing or < Pro tier, falls back to "Yantra4D".
    """
    platform_name = "Yantra4D"
    platform_logo = "/logo.png"

    license_key = Config.YANTRA4D_LICENSE_KEY

    # 1. Attempt to resolve custom branding if license provided
    if license_key:
        try:
            # decode_token fetches the dynamic Janua JWKS and verifies the signature + expiry
            claims = decode_token(license_key)
            user_tier = resolve_tier(claims)
            
            # 2. Only allow white-label override for paying tiers (pro/madfam)
            if has_tier(user_tier, "pro"):
                platform_name = Config.PLATFORM_NAME
                platform_logo = Config.PLATFORM_LOGO
            else:
                logger.info("Provided license key is valid but tier is too low for white-labeling.")
        except Exception as e:
            logger.warning("License key JWT validation failed: %s", e)

    return jsonify({
        "platformName": platform_name,
        "platformLogo": platform_logo
    })
