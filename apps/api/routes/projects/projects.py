"""
Projects Blueprint
Handles /api/projects endpoints for multi-project support.
"""
import hashlib
import json
import logging
import os
import sqlite3
import time

import re
import shutil

from flask import Blueprint, jsonify, send_from_directory, abort, request, make_response

from config import Config
from extensions import limiter
import rate_limits
from manifest import discover_projects, get_manifest, invalidate_cache
from middleware.auth import optional_auth, require_tier
from utils.route_helpers import error_response

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
    resp.headers["Cache-Control"] = "public, max-age=300"
    return resp


@projects_bp.route('/api/projects/<slug>/manifest', methods=['GET'])
def get_project_manifest(slug):
    """Return full manifest for a specific project."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError as e:
        return jsonify({"status": "error", "error": str(e)}), 404

    try:
        body = json.dumps(manifest.as_json(), sort_keys=True)
        body = json.dumps(manifest.as_json(), sort_keys=True)
        etag = hashlib.md5(body.encode()).hexdigest()

        if request.if_none_match and etag in request.if_none_match:
            return make_response("", 304)

        resp = make_response(body)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Cache-Control"] = "public, max-age=300"
        resp.headers["ETag"] = etag
        return resp
    except RuntimeError as e:
        return jsonify({"status": "error", "error": str(e)}), 404


@projects_bp.route('/api/projects/<slug>/meta', methods=['GET'])
def get_project_meta(slug):
    """Return project.meta.json if it exists."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        return jsonify(None)
    
    meta_path = manifest.project_dir / "project.meta.json"
    if not meta_path.is_file():
        return jsonify(None)
    try:
        with open(meta_path) as f:
            return jsonify(json.load(f))
    except (json.JSONDecodeError, OSError):
        return jsonify(None)


@projects_bp.route('/api/projects/<slug>/parts/<path:filename>', methods=['GET'])
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
    resp.headers["Cache-Control"] = "public, max-age=86400"
    return resp


@projects_bp.route('/api/projects/<slug>/fork', methods=['POST'])
@require_tier("pro")
@limiter.limit(rate_limits.PROJECT_FORK)
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

    dest_dir = Config.PROJECTS_DIR / new_slug
    if dest_dir.exists():
        return error_response(f"Project '{new_slug}' already exists", 409)

    try:
        shutil.copytree(
            src_dir, dest_dir,
            ignore=shutil.ignore_patterns(".git", ".analytics.db", "__pycache__"),
        )
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
    except Exception as e:
        # Clean up partial copy
        if dest_dir.exists():
            shutil.rmtree(dest_dir, ignore_errors=True)
        logger.error("Fork failed %s -> %s: %s", slug, new_slug, e)
        return error_response(f"Fork failed: {e}", 500)

    return jsonify({"success": True, "slug": new_slug})


@projects_bp.route('/api/projects/<slug>/manifest/assembly-steps', methods=['PUT'])
@optional_auth
def update_assembly_steps(slug):
    """Update assembly_steps in a project's project.json."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        return jsonify({"status": "error", "error": f"Project '{slug}' not found"}), 404

    manifest_path = manifest.project_dir / "project.json"

    data = request.get_json(silent=True)
    if not data or "assembly_steps" not in data:
        return jsonify({"status": "error", "error": "Missing assembly_steps"}), 400

    try:
        with open(manifest_path, "r") as f:
            manifest_data = json.load(f)

        manifest_data["assembly_steps"] = data["assembly_steps"]

        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Invalidate manifest cache
        invalidate_cache(slug)

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Failed to save assembly steps for {slug}: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500
