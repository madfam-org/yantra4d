"""
Git Operations API — status, diff, commit, push, pull for GitHub-imported projects.
"""
import json
import logging
from pathlib import Path

from flask import Blueprint, request, jsonify

from config import Config
from extensions import limiter
import rate_limits
from middleware.auth import require_tier
from utils.route_helpers import error_response, require_json_body
from services.editor.git_operations import git_status, git_diff, git_commit, git_push, git_pull
from services.editor.github_token import get_github_token

import re

logger = logging.getLogger(__name__)

git_ops_bp = Blueprint("git_ops", __name__)


def _get_github_project(slug: str) -> tuple[Path | None, str | None]:
    """Resolve project dir and verify it's a GitHub-imported project with .git.

    Returns (project_dir, error_message). error_message is None on success.
    """
    project_dir = (Config.PROJECTS_DIR / slug).resolve()
    if not project_dir.is_relative_to(Config.PROJECTS_DIR.resolve()):
        return None, "Project not found"
    if not project_dir.is_dir():
        return None, "Project not found"

    meta_path = project_dir / "project.meta.json"
    if not meta_path.exists():
        return None, "No source metadata — not a GitHub project"

    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None, "Invalid project.meta.json"

    if meta.get("source", {}).get("type") != "github":
        return None, "Project was not imported from GitHub"

    if not (project_dir / ".git").is_dir():
        return None, "Project does not have a git repository"

    return project_dir, None


def _get_git_project(slug: str) -> tuple[Path | None, str | None]:
    """Resolve project dir and verify it has .git (any source type).

    Returns (project_dir, error_message). error_message is None on success.
    """
    project_dir = (Config.PROJECTS_DIR / slug).resolve()
    if not project_dir.is_relative_to(Config.PROJECTS_DIR.resolve()):
        return None, "Project not found"
    if not project_dir.is_dir():
        return None, "Project not found"
    if not (project_dir / ".git").is_dir():
        return None, "Project does not have a git repository"
    return project_dir, None


GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+(\.git)?$")


@git_ops_bp.route("/api/projects/<slug>/git/connect-remote", methods=["POST"])
@require_tier("pro")
@limiter.limit(rate_limits.GIT_CONNECT)
@require_json_body
def connect_remote(slug):
    """Add or update origin remote URL and update project metadata."""
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    data = request.json
    remote_url = data.get("remote_url", "").strip()
    if not remote_url or not GITHUB_URL_PATTERN.match(remote_url):
        return error_response("Invalid GitHub repository URL", 400)

    # Add or set origin remote
    from services.editor.git_operations import _run_git, _get_remote_url
    existing = _get_remote_url(project_dir)
    if existing:
        result = _run_git(project_dir, ["remote", "set-url", "origin", remote_url], timeout=10)
    else:
        result = _run_git(project_dir, ["remote", "add", "origin", remote_url], timeout=10)

    if result.returncode != 0:
        return error_response(f"Failed to set remote: {result.stderr.strip()}", 500)

    # Update project.meta.json
    meta_path = project_dir / "project.meta.json"
    meta = {}
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    meta.setdefault("source", {})
    meta["source"]["type"] = "github"
    meta["source"]["repo_url"] = remote_url

    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
        f.write("\n")

    return jsonify({"success": True})


@git_ops_bp.route("/api/projects/<slug>/git/status", methods=["GET"])
@require_tier("pro")
@limiter.limit(rate_limits.GIT_STATUS)
def get_status(slug):
    """Get git working tree status."""
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    result = git_status(project_dir)
    if not result["success"]:
        return error_response(result["error"], 500)
    return jsonify(result)


@git_ops_bp.route("/api/projects/<slug>/git/diff", methods=["GET"])
@require_tier("pro")
@limiter.limit(rate_limits.GIT_DIFF)
def get_diff(slug):
    """Get unified diff for working tree or a specific file."""
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    filepath = request.args.get("file")
    result = git_diff(project_dir, filepath)
    if not result["success"]:
        return error_response(result["error"], 500)
    return jsonify(result)


@git_ops_bp.route("/api/projects/<slug>/git/commit", methods=["POST"])
@require_tier("pro")
@limiter.limit(rate_limits.GIT_COMMIT)
@require_json_body
def commit(slug):
    """Stage files and commit."""
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    data = request.json
    message = data.get("message", "").strip()
    files = data.get("files", [])

    if not message:
        return error_response("message is required", 400)
    if len(message) > 1000:
        return error_response("Commit message must be 1000 characters or less", 400)
    if not files:
        return error_response("files list is required", 400)

    # Derive author from JWT claims
    claims = getattr(request, "auth_claims", None) or {}
    author_name = claims.get("name") or claims.get("preferred_username")
    author_email = claims.get("email")

    result = git_commit(project_dir, message, files, author_name, author_email)
    if not result["success"]:
        return error_response(result["error"], 400)
    return jsonify(result)


@git_ops_bp.route("/api/projects/<slug>/git/push", methods=["POST"])
@require_tier("pro")
@limiter.limit(rate_limits.GIT_PUSH)
def push(slug):
    """Push commits to origin."""
    project_dir, err = _get_github_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    claims = getattr(request, "auth_claims", None)
    github_token = get_github_token(claims)
    if not github_token:
        return error_response("GitHub token not available — re-authenticate with GitHub", 401)

    result = git_push(project_dir, github_token)
    if not result["success"]:
        return error_response(result["error"], 500)
    return jsonify(result)


@git_ops_bp.route("/api/projects/<slug>/git/pull", methods=["POST"])
@require_tier("pro")
@limiter.limit(rate_limits.GIT_PULL)
def pull(slug):
    """Pull latest from origin."""
    project_dir, err = _get_github_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    claims = getattr(request, "auth_claims", None)
    github_token = get_github_token(claims)
    if not github_token:
        return error_response("GitHub token not available — re-authenticate with GitHub", 401)

    result = git_pull(project_dir, github_token)
    if not result["success"]:
        return error_response(result["error"], 500)
    return jsonify(result)
