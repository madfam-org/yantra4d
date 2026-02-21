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
from utils.route_helpers import error_response, require_json_body, cleanup_old_stl_files
from services.editor.git_operations import git_status, git_diff, git_commit, git_push, git_pull, git_archive_head
from services.editor.github_token import get_github_token
import tempfile
import os

from routes.engine.render import _extract_render_payload, STATIC_FOLDER
from services.engine.openscad import build_openscad_command, run_render as run_openscad_render
from services.engine.cadquery_engine import build_cadquery_command, run_render as run_cadquery_render
from manifest import get_manifest

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


@git_ops_bp.route("/api/projects/<slug>/git/render-head", methods=["POST"])
@require_tier("pro")
@require_json_body
def render_head(slug):
    """Render the HEAD version of the selected SCAD file's parts."""
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    data = request.json
    payload = _extract_render_payload(data)
    
    if payload is None:
        return error_response("Invalid SCAD file", 400)
    
    parts_to_render = payload['parts']
    stl_prefix = payload['stl_prefix'] + "head_"
    export_format = payload['export_format']
    params = payload['params']
    mode_map = payload['mode_map']
    
    generated_parts = []
    combined_log = ""
    
    cleanup_old_stl_files(parts_to_render, STATIC_FOLDER, stl_prefix, export_format)
    
    manifest = get_manifest(slug)
    engine = manifest.engine
    
    # Extract HEAD to a temp dir
    with tempfile.TemporaryDirectory(prefix="yantra_head_") as tmpdir_name:
        target_dir = Path(tmpdir_name)
        archive_res = git_archive_head(project_dir, target_dir)
        if not archive_res["success"]:
            return error_response(archive_res["error"], 500)
            
        head_scad_path = str(target_dir / payload['scad_filename'])
        if not os.path.exists(head_scad_path):
            return error_response("SCAD file does not exist in HEAD", 404)
            
        try:
            for part in parts_to_render:
                output_filename = f"{stl_prefix}{part}.{export_format}"
                output_path = os.path.join(STATIC_FOLDER, output_filename)
                
                if engine == "cadquery":
                    cmd = build_cadquery_command(output_path, head_scad_path, params, export_format)
                    success, stderr = run_cadquery_render(cmd, scad_path=head_scad_path)
                else:
                    render_mode = mode_map.get(part, 0)
                    cmd = build_openscad_command(output_path, head_scad_path, params, render_mode)
                    success, stderr = run_openscad_render(cmd, scad_path=head_scad_path)
                    
                if not success:
                    # Ignore failures if the part simply didn't exist in HEAD or failed to compile
                    combined_log += f"[{part}] HEAD render failed: {stderr}\n"
                    continue
                    
                combined_log += f"[{part}] {stderr}\n"
                generated_parts.append({
                    "type": part,
                    "url": f"/static/{output_filename}",
                    "size_bytes": os.path.getsize(output_path) if os.path.exists(output_path) else None
                })
                
            return jsonify({
                "status": "success",
                "parts": generated_parts,
                "log": combined_log
            })
        except Exception as e:
            logger.warning(f"Unexpected error during HEAD render: {e}")
            return error_response(str(e), 500)
