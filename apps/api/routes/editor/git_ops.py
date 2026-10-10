"""
Git Operations API — status, diff, commit, push, pull for GitHub-imported projects.
"""
import json
import logging
import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request

import rate_limits
from extensions import limiter
from middleware.auth import require_tier
from routes.editor.editor import require_writable_cartridge
from services.core.project_access import require_project_access
from services.core.tier_service import resolve_tier
from services.editor.git_operations import (
    GitUnavailableError,
    git_available,
    git_commit,
    git_diff,
    git_log,
    git_pull,
    git_push,
    git_status,
)
from services.editor.github_token import get_github_token
from services.engine.render_artifacts import discard_render_artifacts
from services.engine.render_contract import RENDER_EVENT_PART_DONE
from services.engine.render_orchestrator import (
    STATIC_FOLDER,
    RenderPayloadError,
    clear_request_cancel,
    extract_render_payload,
    is_render_worker_available,
    resolve_engine_config,
)
from services.engine.worker_dispatch import (
    SOURCE_ERROR_GIT_UNAVAILABLE,
    SOURCE_ERROR_MISSING,
    SOURCE_ERROR_OUTSIDE,
    SOURCE_GIT_HEAD,
    WORKER_UNAVAILABLE,
    render_part_on_worker,
)
from utils.project_resolver import find_project_dir, resolve_project_dir
from utils.route_helpers import (
    error_response,
    handle_exceptions,
    require_json_body,
)
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

git_ops_bp = Blueprint("git_ops", __name__)

#: Machine-readable code for "this deployment has no git binary".
GIT_UNAVAILABLE_ERROR_CODE = "git_unavailable"


def git_unavailable_response():
    """503: the version-control features need a ``git`` binary this host lacks."""
    return error_response(
        "Version control is unavailable on this server (git is not installed)",
        503, error_code=GIT_UNAVAILABLE_ERROR_CODE,
    )


@git_ops_bp.before_request
def _require_git_binary():
    """Every route here shells out to git; answer 503 up front without it."""
    if not git_available():
        return git_unavailable_response()
    return None


@git_ops_bp.errorhandler(GitUnavailableError)
def _git_vanished(_exc):
    """Backstop for git disappearing between the check above and the call."""
    return git_unavailable_response()


# HTTP status for a HEAD checkout the worker could not produce. Every part of a
# request renders from the same commit, so a source failure answers the whole
# request, with the status this route has always used for it.
_SOURCE_ERROR_STATUS = {SOURCE_ERROR_MISSING: 404, SOURCE_ERROR_OUTSIDE: 400}


def _get_github_project(slug: str) -> tuple[Path | None, str | None]:
    """Resolve project dir and verify it's a GitHub-imported project with .git.

    Returns (project_dir, error_message). error_message is None on success.
    """
    project_dir = find_project_dir(slug)
    if project_dir is None:
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
    project_dir, err = resolve_project_dir(slug, require_git=True)
    if err:
        return None, err
    return project_dir, None


GITHUB_URL_PATTERN = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+(\.git)?$")


@git_ops_bp.route("/api/projects/<slug>/git/connect-remote", methods=["POST"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_CONNECT)
@require_json_body
@require_project_access
@require_writable_cartridge
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
    from services.editor.git_operations import _get_remote_url, _run_git
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
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_STATUS)
@require_project_access
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
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_DIFF)
@require_project_access
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


@git_ops_bp.route("/api/projects/<slug>/git/log", methods=["GET"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_LOG)
@require_project_access
def get_log(slug):
    """Get recent commit log for the project."""
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    limit = request.args.get("limit", 20, type=int)
    if limit < 1 or limit > 50:
        return error_response("limit must be between 1 and 50", 400)

    result = git_log(project_dir, limit)
    if not result["success"]:
        return error_response(result["error"], 500)
    return jsonify(result)


@git_ops_bp.route("/api/projects/<slug>/git/commit", methods=["POST"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_COMMIT)
@require_json_body
@require_project_access
@require_writable_cartridge
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
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_PUSH)
@require_project_access
@require_writable_cartridge
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
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.GIT_PULL)
@require_project_access
@require_writable_cartridge
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
@require_valid_slug
@require_tier("pro")
@require_json_body
@handle_exceptions
@require_project_access
def render_head(slug):
    """Render the HEAD version of the selected SCAD file's parts.

    Each part is a job on the render worker. The worker checks out the
    committed tree into a private temporary directory, renders from it, and
    removes it when the job ends; this handler queues the parts and collects
    their results into the same response shape as before.
    """
    project_dir, err = _get_git_project(slug)
    if err:
        return error_response(err, 404 if "not found" in err.lower() else 400)

    # The URL slug is the cartridge that passed the access check; render that
    # one, whatever the body says.
    data = {**request.json, "project": slug}
    payload = extract_render_payload(data)

    if isinstance(payload, RenderPayloadError):
        return error_response(payload.message, 400)

    # The tier @require_tier already admitted this caller at (the top tier
    # when auth is off), so the engine gate agrees with the route gate.
    tier = getattr(request, "user_tier", None) or resolve_tier(getattr(request, "auth_claims", None))
    engine, scad_path, actual_format, engine_error = resolve_engine_config(data, payload, tier)
    if engine_error:
        return error_response(engine_error[0], engine_error[1])

    # The worker renders this path inside its own HEAD checkout, so it travels
    # relative to the cartridge, never as an absolute working-tree path.
    try:
        entry = Path(scad_path).resolve().relative_to(Path(project_dir).resolve()).as_posix()
    except ValueError:
        return error_response("Render file is outside the project", 400)

    if not is_render_worker_available():
        return error_response(WORKER_UNAVAILABLE, 503, error_code="render_worker_unavailable")

    parts_to_render = payload['parts']
    export_format = payload['export_format']
    stl_prefix = payload['stl_prefix'] + "head_"
    head_payload = {
        **payload,
        "stl_prefix": stl_prefix,
        # A HEAD render must never answer a later /api/render for the working
        # tree's file of the same name, and its provenance is not the working
        # tree's, so it is neither cached nor given a generator-output sidecar.
        "cache_write": False,
        "generator_inputs": None,
    }

    generated_parts = []
    combined_log = ""

    discard_render_artifacts(parts_to_render, stl_prefix, export_format)
    clear_request_cancel(payload.get("request_id"))

    for part in parts_to_render:
        if not is_render_worker_available():
            combined_log += f"[{part}] HEAD render failed: {WORKER_UNAVAILABLE}\n"
            break
        result = render_part_on_worker(
            head_payload,
            engine=engine,
            part=part,
            scad_path=entry,
            output_path=os.path.join(STATIC_FOLDER, f"{stl_prefix}{part}.{actual_format}"),
            export_format=export_format,
            source={"kind": SOURCE_GIT_HEAD, "entry": entry},
        )
        if result.get("source_error") == SOURCE_ERROR_GIT_UNAVAILABLE:
            # The worker checks HEAD out, so it needs git as much as this route does.
            return git_unavailable_response()
        if result.get("source_error"):
            return error_response(
                result.get("error") or "Failed to extract HEAD archive",
                _SOURCE_ERROR_STATUS.get(result["source_error"], 500),
            )
        if result.get("event") != RENDER_EVENT_PART_DONE:
            # A part that does not exist in HEAD, or does not compile there,
            # is reported in the log and skipped, as before.
            error = result.get("error") or result.get("message") or "Render failed"
            combined_log += f"[{part}] HEAD render failed: {error}\n"
            continue

        log = result.get("log") or f"[{part}] \n"
        combined_log += log
        part_entry = {
            "type": result.get("type") or part,
            "url": result.get("url"),
            "size_bytes": result.get("size_bytes"),
        }
        if result.get("viewer_url"):
            part_entry["viewer_url"] = result["viewer_url"]
        generated_parts.append(part_entry)

    return jsonify({
        "status": "success",
        "parts": generated_parts,
        "log": combined_log,
        "request_id": payload.get("request_id"),
    })
