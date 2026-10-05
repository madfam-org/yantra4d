"""
Projects Blueprint
Handles /api/projects endpoints for multi-project support.
"""
import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import stat
import time

from flask import Blueprint, abort, jsonify, make_response, request, send_from_directory

import rate_limits
from config import Config
from extensions import limiter
from manifest import discover_projects, get_manifest, invalidate_cache
from middleware.auth import ensure_optional_auth, require_tier
from routes.editor.editor import cartridge_write_refusal, require_writable_cartridge
from services.core.cartridge_ownership import claims_sub, forget_owner, owner_sub, record_owner
from services.core.project_access import (
    filter_visible_projects,
    is_private_project,
    require_project_access,
)
from services.core.tier_service import has_tier, resolve_tier
from services.engine.render_revision import render_revision
from utils.project_resolver import project_write_root, slug_in_use
from utils.route_helpers import error_response, handle_exceptions
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

projects_bp = Blueprint('projects', __name__)

ANALYTICS_DB = str(Config.ANALYTICS_DB_PATH)

SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{1,48}[a-z0-9]$")


def _get_project_stats():
    """Fetch aggregate event counts per project from analytics DB."""
    if not os.path.exists(ANALYTICS_DB):
        return {}
    try:
        conn = sqlite3.connect(ANALYTICS_DB)
        conn.row_factory = sqlite3.Row
        since = time.time() - 30 * 86400  # last 30 days
        rows = conn.execute(
            "SELECT project, event_type, COUNT(*) as count "
            "FROM events WHERE created_at > ? GROUP BY project, event_type",
            (since,),
        ).fetchall()
        conn.close()
        stats = {}
        for row in rows:
            slug = row["project"]
            if slug not in stats:
                stats[slug] = {}
            stats[slug][row["event_type"]] = row["count"]
        return stats
    except Exception as e:
        logger.debug(f"Analytics stats unavailable: {e}")
        return {}


@projects_bp.route('/api/projects', methods=['GET'])
def list_projects():
    """Return list of available projects with optional analytics counts."""
    projects = discover_projects()
    # Privacy first, listing second: `unlisted` hides a project someone may
    # still fetch directly, `private` withholds it entirely. Filtering in this
    # order keeps the two independent.
    projects, any_private = filter_visible_projects(projects)
    projects = [p for p in projects if not p.get("unlisted", False)]
    include_stats = request.args.get("stats") == "1"
    if include_stats:
        stats = _get_project_stats()
        for p in projects:
            slug = p.get("slug", "")
            project_stats = stats.get(slug, {})
            p["stats"] = {
                "renders": project_stats.get("render", 0),
                "exports": project_stats.get("export", 0),
                "preset_applies": project_stats.get("preset_apply", 0),
            }
    resp = jsonify(projects)
    # Once any project in the catalogue is private the list depends on who is
    # asking, and a shared cache would hand one caller's view to the next.
    resp.headers["Cache-Control"] = (
        "private, no-store" if any_private else "public, max-age=300"
    )
    return resp


@projects_bp.route('/api/projects/<slug>/manifest', methods=['GET'])
@require_valid_slug
@require_project_access
def get_project_manifest(slug):
    """Return full manifest for a specific project."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError as e:
        return error_response(str(e), 404, error_code="project_not_found")

    try:
        body = json.dumps(manifest.as_json(), sort_keys=True)
        revision = render_revision()

        if is_private_project(slug, manifest):
            # A private manifest gets neither a shared cache nor an ETag: the
            # ETag is a stable, guessable handle to the very content being
            # withheld, and a 304 to an entitled caller would let an
            # intermediary keep serving the body.
            resp = make_response(body)
            resp.headers["Content-Type"] = "application/json"
            resp.headers["Cache-Control"] = "private, no-store"
            if revision:
                resp.headers["X-Render-Revision"] = revision
            return resp

        # Geometry-only releases leave the authored manifest unchanged. Include
        # the renderer identity in validators and revalidate on project load.
        etag = hashlib.sha256(f"{revision}\n{body}".encode()).hexdigest()
        unchanged = request.if_none_match and etag in request.if_none_match
        resp = make_response("" if unchanged else body, 304 if unchanged else 200)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Cache-Control"] = "public, no-cache"
        resp.set_etag(etag)
        if revision:
            resp.headers["X-Render-Revision"] = revision
        return resp
    except RuntimeError as e:
        return error_response(str(e), 404, error_code="manifest_serialization_error")


@projects_bp.route('/api/projects/<slug>/meta', methods=['GET'])
@require_valid_slug
@require_project_access
def get_project_meta(slug):
    """Return project.meta.json if it exists, plus what THIS caller may do with it.

    ``can_write`` answers whether the write routes (editor, assembly steps, git)
    would accept this caller for this cartridge: the same decision the write
    guard makes, plus the ``pro`` tier those routes require. ``is_owner`` is
    whether the caller created it. Neither reveals who else did, and the answer
    depends on the caller, so it is never shared-cached.
    """
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        return error_response("Project not found", 404)

    meta_path = manifest.project_dir / "project.meta.json"
    body = {}
    if meta_path.is_file():
        try:
            with open(meta_path) as f:
                loaded = json.load(f)
            body = loaded if isinstance(loaded, dict) else {}
        except (json.JSONDecodeError, OSError):
            body = {}

    claims = ensure_optional_auth()
    tier_ok = (not Config.AUTH_ENABLED) or has_tier(resolve_tier(claims), "pro")
    refusal = cartridge_write_refusal(slug, manifest.project_dir, claims)
    sub = claims_sub(claims)
    body["can_write"] = bool(tier_ok and refusal is None)
    body["is_owner"] = bool(sub and sub == owner_sub(slug, manifest.project_dir))

    resp = jsonify(body)
    resp.headers["Cache-Control"] = "private, no-store"
    return resp


@projects_bp.route('/api/projects/<slug>/parts/<path:filename>', methods=['GET'])
@require_valid_slug
@require_project_access
def serve_static_part(slug, filename):
    """Serve a pre-existing STL file from a project's parts/ directory."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        abort(404)
        
    parts_dir = manifest.project_dir / "parts"
    if not parts_dir.is_dir():
        abort(404)
    requested = (parts_dir / filename).resolve()
    if not requested.is_relative_to(parts_dir.resolve()):
        abort(403)
    if not requested.is_file():
        abort(404)
    resp = send_from_directory(str(parts_dir), filename)
    resp.headers["Cache-Control"] = (
        "private, no-store" if is_private_project(slug, manifest)
        else "public, max-age=86400"
    )
    return resp


def _make_owner_writable(root) -> None:
    """Give the owner write permission on a freshly copied tree.

    ``copytree`` copies permission bits along with the content, so a fork of a
    cartridge whose files are read-only (a read-only commons, an image built
    with restrictive modes) would itself be read-only, and the very next write
    -- ``project.meta.json`` below, then every save -- would fail. The fork is
    the user's own copy: it must be writable whatever its source was.
    """
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in (dirpath, *(os.path.join(dirpath, n) for n in filenames)):
            if os.path.islink(name):
                continue
            mode = os.stat(name).st_mode
            if not mode & stat.S_IWUSR:
                os.chmod(name, mode | stat.S_IWUSR)


@projects_bp.route('/api/projects/<slug>/fork', methods=['POST'])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.PROJECT_FORK)
@require_project_access
def fork_project(slug):
    """Fork a project: copy files to a new slug owned by the user."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        return error_response(f"Project '{slug}' not found", 404)

    src_dir = manifest.project_dir

    data = request.get_json(silent=True) or {}
    new_slug = data.get("new_slug", "").strip()
    if not new_slug or not SLUG_PATTERN.match(new_slug):
        return error_response("Invalid slug (lowercase alphanumeric, hyphens, 3-50 chars)", 400)

    # A fork is a new public cartridge even when its source is private.
    # The new slug must be free in every root; the fork itself is written
    # into the user-projects root, never next to its source.
    if slug_in_use(new_slug) is not None:
        return error_response(f"Project '{new_slug}' already exists", 409, error_code="slug_in_use")
    dest_dir = project_write_root() / new_slug

    # Reserve the slug atomically: an exclusive mkdir. Of two concurrent forks
    # to the same slug only one creates the directory; the other answers 409
    # and never touches it — so the cleanup below only ever removes a
    # directory this request created.
    try:
        dest_dir.parent.mkdir(parents=True, exist_ok=True)
        dest_dir.mkdir()
    except FileExistsError:
        return error_response(f"Project '{new_slug}' already exists", 409, error_code="slug_in_use")
    except OSError as e:
        logger.error("Fork failed %s -> %s: %s", slug, new_slug, e)
        return error_response(f"Fork failed: {e}", 500)

    try:
        shutil.copytree(
            src_dir, dest_dir,
            ignore=shutil.ignore_patterns(".git", ".analytics.db", "__pycache__"),
            dirs_exist_ok=True,
        )
        _make_owner_writable(dest_dir)
        # Write fork metadata
        meta = {
            "source": {
                "type": "fork",
                "forked_from": slug,
            }
        }
        with open(dest_dir / "project.meta.json", "w") as f:
            json.dump(meta, f, indent=2)
            f.write("\n")
        # The forking account becomes the only non-admin that may write it.
        record_owner(new_slug, ensure_optional_auth())
    except Exception as e:
        # Clean up partial copy
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        forget_owner(new_slug)
        logger.error("Fork failed %s -> %s: %s", slug, new_slug, e)
        return error_response(f"Fork failed: {e}", 500)

    return jsonify({"success": True, "slug": new_slug})


@projects_bp.route('/api/projects/<slug>/manifest/assembly-steps', methods=['PUT'])
@require_valid_slug
@require_tier("pro")
@handle_exceptions
@require_project_access
@require_writable_cartridge
def update_assembly_steps(slug):
    """Update assembly_steps in a project's project.json."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        return error_response(f"Project '{slug}' not found", 404, error_code="project_not_found")

    manifest_path = manifest.project_dir / "project.json"

    data = request.get_json(silent=True)
    if not data or "assembly_steps" not in data:
        return error_response("Missing assembly_steps", 400, error_code="missing_assembly_steps")

    with open(manifest_path) as f:
        manifest_data = json.load(f)

    manifest_data["assembly_steps"] = data["assembly_steps"]

    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Invalidate manifest cache
    invalidate_cache(slug)

    return jsonify({"status": "success"})
