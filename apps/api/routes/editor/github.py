"""
GitHub Import Blueprint — validate, import, and sync repos.
"""
import logging
import shutil

from flask import Blueprint, jsonify, request

import rate_limits
from config import Config
from extensions import limiter
from middleware.auth import ensure_optional_auth, require_tier
from routes.editor.editor import check_writable_cartridge
from services.core.cartridge_ownership import forget_owner, record_owner
from services.core.tier_service import TOP_TIER
from services.editor.github_import import import_repo, sync_repo, validate_repo
from services.editor.github_token import get_github_token
from utils.project_resolver import project_write_root
from utils.route_helpers import error_response, require_json_body
from utils.validators import validate_project_slug

logger = logging.getLogger(__name__)

github_bp = Blueprint("github", __name__)


@github_bp.before_request
def _require_git_binary():
    """Validate (ls-remote), import (clone) and sync (pull/clone) all need git.

    Without it ls-remote and clone fail in ways that read as "repository not
    accessible" or "failed to clone"; say what is actually wrong instead.
    """
    from routes.editor.git_ops import git_unavailable_response
    from services.editor.git_operations import git_available
    if not git_available():
        return git_unavailable_response()
    return None


def _get_token():
    """Extract GitHub token from current request's auth claims."""
    claims = getattr(request, "auth_claims", None)
    return get_github_token(claims)


@github_bp.route("/api/github/validate", methods=["POST"])
@require_tier("pro")
@limiter.limit(rate_limits.GITHUB_VALIDATE)
@require_json_body
def validate_github_repo():
    """Validate a GitHub repo URL and return detected SCAD files."""
    if not Config.GITHUB_IMPORT_ENABLED:
        return error_response("GitHub import is disabled", 403)

    data = request.json
    repo_url = data.get("repo_url", "").strip()
    if not repo_url:
        return error_response("repo_url is required", 400)

    result = validate_repo(repo_url, github_token=_get_token())
    if not result["valid"]:
        return error_response(result["error"], 400)

    return jsonify(result)


@github_bp.route("/api/github/import", methods=["POST"])
@require_tier("pro")
@limiter.limit(rate_limits.GITHUB_IMPORT)
@require_json_body
def import_github_repo():
    """Import a GitHub repo as a new Yantra4D project."""
    if not Config.GITHUB_IMPORT_ENABLED:
        return error_response("GitHub import is disabled", 403)

    data = request.json
    repo_url = data.get("repo_url", "").strip()
    slug = data.get("slug", "").strip()
    manifest = data.get("manifest")

    if not repo_url:
        return error_response("repo_url is required", 400)
    slug_err = validate_project_slug(slug)
    if slug_err:
        return error_response(slug_err, 400)
    if not manifest or not isinstance(manifest, dict):
        return error_response("manifest is required", 400)

    result = import_repo(repo_url, slug, manifest, github_token=_get_token())
    if not result["success"]:
        if result.get("error_code") == "slug_in_use":
            return error_response(result["error"], 409, error_code="slug_in_use")
        return error_response(result["error"], 400)

    # The importing account becomes the only non-admin that may write it. A
    # cartridge whose record could not be written is not left behind.
    try:
        record_owner(slug, ensure_optional_auth())
    except OSError as e:
        logger.error("Import of %s: could not record its creator: %s", slug, e)
        forget_owner(slug)
        shutil.rmtree(project_write_root() / slug, ignore_errors=True)
        return error_response("Import failed: could not record the project's owner", 500)

    return jsonify(result), 201


@github_bp.route("/api/github/sync", methods=["POST"])
@require_tier(TOP_TIER)
@limiter.limit(rate_limits.GITHUB_SYNC)
@require_json_body
def sync_github_repo():
    """Sync an imported project with its GitHub source."""
    data = request.json
    slug = data.get("slug", "").strip()
    if not slug:
        return error_response("slug is required", 400)
    if validate_project_slug(slug) is None:
        refused = check_writable_cartridge(slug)
        if refused is not None:
            return refused

    result = sync_repo(slug, github_token=_get_token())
    if not result["success"]:
        return error_response(result["error"], 400)

    return jsonify(result)
