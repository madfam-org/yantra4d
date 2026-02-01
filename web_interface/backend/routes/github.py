"""
GitHub Import Blueprint — validate, import, and sync repos.
"""
import logging
import re

from flask import Blueprint, request, jsonify

from config import Config
from extensions import limiter
from middleware.auth import require_tier
from services.route_helpers import error_response, require_json_body
from services.github_import import validate_repo, import_repo, sync_repo

logger = logging.getLogger(__name__)

github_bp = Blueprint("github", __name__)


@github_bp.route("/api/github/validate", methods=["POST"])
@require_tier("pro")
@limiter.limit("30/hour")
@require_json_body
def validate_github_repo():
    """Validate a GitHub repo URL and return detected SCAD files."""
    if not Config.GITHUB_IMPORT_ENABLED:
        return error_response("GitHub import is disabled", 403)

    data = request.json
    repo_url = data.get("repo_url", "").strip()
    if not repo_url:
        return error_response("repo_url is required", 400)

    result = validate_repo(repo_url)
    if not result["valid"]:
        return error_response(result["error"], 400)

    return jsonify(result)


@github_bp.route("/api/github/import", methods=["POST"])
@require_tier("pro")
@limiter.limit("10/hour")
@require_json_body
def import_github_repo():
    """Import a GitHub repo as a new Qubic project."""
    if not Config.GITHUB_IMPORT_ENABLED:
        return error_response("GitHub import is disabled", 403)

    data = request.json
    repo_url = data.get("repo_url", "").strip()
    slug = data.get("slug", "").strip()
    manifest = data.get("manifest")

    if not repo_url:
        return error_response("repo_url is required", 400)
    if not slug:
        return error_response("slug is required", 400)
    if not re.match(r"^[a-z0-9][a-z0-9-_]*$", slug):
        return error_response("Invalid slug format", 400)
    if not manifest or not isinstance(manifest, dict):
        return error_response("manifest is required", 400)

    result = import_repo(repo_url, slug, manifest)
    if not result["success"]:
        return error_response(result["error"], 400)

    return jsonify(result), 201


@github_bp.route("/api/github/sync", methods=["POST"])
@require_tier("madfam")
@limiter.limit("20/hour")
@require_json_body
def sync_github_repo():
    """Sync an imported project with its GitHub source."""
    data = request.json
    slug = data.get("slug", "").strip()
    if not slug:
        return error_response("slug is required", 400)

    result = sync_repo(slug)
    if not result["success"]:
        return error_response(result["error"], 400)

    return jsonify(result)
