"""
GitHub token extraction from Janua JWT claims or user-info API fallback.
"""
import logging

import requests

from config import Config

logger = logging.getLogger(__name__)


def get_github_token(auth_claims: dict | None) -> str | None:
    """Extract GitHub access token from JWT custom claims.

    Janua must be configured to include 'github_token' in JWT claims when
    GitHub is the social provider with 'repo' scope requested.

    Falls back to Janua user-info API if the claim is not present.
    """
    if not auth_claims:
        return None

    # Primary: check JWT custom claims
    token = auth_claims.get("github_token")
    if token:
        return token

    # Fallback: call Janua user-info API server-to-server
    if Config.JANUA_API_KEY:
        sub = auth_claims.get("sub")
        if sub:
            return _fetch_github_token_from_janua(sub)

    return None


def _fetch_github_token_from_janua(user_id: str) -> str | None:
    """Fetch GitHub provider token from Janua user metadata API."""
    try:
        resp = requests.get(
            f"{Config.JANUA_API_URL}/users/{user_id}/provider-tokens/github",
            headers={"Authorization": f"Bearer {Config.JANUA_API_KEY}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("access_token")
        logger.debug("Janua provider-token lookup returned %d", resp.status_code)
    except Exception as e:
        logger.warning("Failed to fetch GitHub token from Janua: %s", e)
    return None


def validate_github_token(token: str) -> dict | None:
    """Verify a GitHub token by calling the GitHub user API.

    Returns the GitHub user dict on success, None on failure.
    """
    try:
        resp = requests.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        logger.debug("GitHub token validation returned %d", resp.status_code)
    except Exception as e:
        logger.warning("GitHub token validation failed: %s", e)
    return None
