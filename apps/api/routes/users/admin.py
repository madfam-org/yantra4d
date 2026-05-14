"""
Admin Blueprint
Provides /api/admin/* endpoints for project management and monitoring.
"""
import json
import logging
import os
import time
from pathlib import Path

from flask import Blueprint, jsonify, request, Response
from sqlalchemy import desc, func

from config import Config
from extensions import db
from manifest import discover_projects, get_manifest
from middleware.auth import require_role, optional_auth
from services.engine.render_orchestrator import (
    ACTIVE_RENDER_JOBS_KEY,
    ACTIVE_RENDER_META_PREFIX,
    RENDER_QUEUE,
    r,
)
from models.analytics import AnalyticsEvent
from utils.route_helpers import error_response
from utils.validators import require_valid_slug

admin_bp = Blueprint('admin', __name__)
logger = logging.getLogger(__name__)

# Flags that the admin UI is allowed to toggle
_ALLOWED_FLAGS = {"is_demo", "is_hyperobject", "unlisted"}


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_json(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _collect_active_render_state() -> dict:
    """Return best-effort active render metrics from Redis."""
    active_jobs = []

    try:
        queued_jobs = int(r.llen(RENDER_QUEUE) or 0)
        active_ids = r.smembers(ACTIVE_RENDER_JOBS_KEY) or []
    except Exception as exc:
        logger.warning("Render activity unavailable from Redis: %s", exc)
        return {
            "active_jobs": [],
            "active_count": 0,
            "queued_jobs": 0,
            "note": "Redis unavailable for render worker telemetry. Start Redis to enable live render status.",
        }

    for raw_job_id in active_ids:
        job_id = str(raw_job_id)
        if not job_id:
            continue

        meta = _safe_json(r.get(f"{ACTIVE_RENDER_META_PREFIX}{job_id}"))
        started_at = _safe_float(meta.get("started_at"))
        duration_ms = None
        if started_at is not None:
            duration_ms = max(0, int((time.time() - started_at) * 1000))

        part = meta.get("part") or ""
        project = meta.get("project_slug") or meta.get("project") or "unknown"
        mode = meta.get("mode") or meta.get("scad_filename") or "unknown"
        engine = meta.get("engine") or "unknown"
        scad_filename = meta.get("scad_filename") or "unknown"
        request_id = meta.get("request_id") or ""

        active_jobs.append({
            "job_id": job_id,
            "project": str(project),
            "mode": str(mode),
            "part": str(part),
            "engine": str(engine),
            "scad_filename": str(scad_filename),
            "request_id": str(request_id),
            "duration_ms": _safe_int(duration_ms) or 0,
            "started_at": started_at,
        })

    active_jobs.sort(key=lambda row: row["duration_ms"], reverse=True)
    return {
        "active_jobs": active_jobs,
        "active_count": len(active_jobs),
        "queued_jobs": queued_jobs,
        "note": None,
    }


def _collect_recent_render_events(limit: int = 10) -> list[dict]:
    try:
        rows = (
            db.session.query(AnalyticsEvent.project, AnalyticsEvent.event_data)
            .filter(AnalyticsEvent.event_type == "render")
            .order_by(desc(AnalyticsEvent.created_at))
            .limit(limit)
            .all()
        )
    except Exception as exc:
        logger.warning("Failed to read recent render analytics: %s", exc)
        return []

    recent = []
    for project, event_data in rows:
        parsed = _safe_json(event_data) if event_data else {}
        duration = parsed.get("duration_ms")
        duration_ms = _safe_int(duration)
        if duration_ms is None:
            duration_ms = 0

        mode = parsed.get("mode") or parsed.get("preset") or "unknown"
        if not mode:
            mode = "unknown"

        recent.append({
            "project": str(project or "unknown"),
            "mode": str(mode),
            "duration_ms": duration_ms,
        })

    return recent


def _load_raw_manifest(slug: str) -> dict | None:
    """Load raw project.json dict (not the parsed ManifestService object)."""
    p = Path(Config.PROJECTS_DIR) / slug / "project.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def _save_raw_manifest(slug: str, data: dict) -> None:
    p = Path(Config.PROJECTS_DIR) / slug / "project.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _enrich_project(proj):
    """Add computed metadata to a project dict."""
    project_dir = Config.PROJECTS_DIR / proj["slug"]
    manifest_path = project_dir / "project.json"

    proj["has_manifest"] = manifest_path.exists()
    proj["modified_at"] = (
        os.path.getmtime(manifest_path) if manifest_path.exists() else None
    )

    scad_files = list(project_dir.glob("*.scad"))
    proj["scad_file_count"] = len(scad_files)

    exports_dir = project_dir / "exports"
    proj["has_exports"] = (
        exports_dir.is_dir() and any(exports_dir.glob("*.stl"))
    )

    if proj["has_manifest"]:
        try:
            m = get_manifest(proj["slug"])
            proj["mode_count"] = len(m.modes)
            proj["parameter_count"] = len(m.parameters)
            proj["estimate_constants"] = m.estimate_constants
        except Exception:
            proj["mode_count"] = 0
            proj["parameter_count"] = 0
            proj["estimate_constants"] = None

        # Expose admin-managed flags from raw manifest
        raw = _load_raw_manifest(proj["slug"]) or {}
        project_obj = raw.get("project", {})
        proj["is_demo"] = project_obj.get("is_demo", False)
        proj["unlisted"] = project_obj.get("unlisted", False)
        ho = project_obj.get("hyperobject", {})
        proj["is_hyperobject"] = ho.get("is_hyperobject", False)
    else:
        proj["mode_count"] = 0
        proj["parameter_count"] = 0
        proj["estimate_constants"] = None
        proj["is_demo"] = False
        proj["unlisted"] = False
        proj["is_hyperobject"] = False

    return proj


@admin_bp.route('/api/admin/projects', methods=['GET'])
@optional_auth
def admin_list_projects() -> Response:
    """
    Return enriched list of projects.
    
    - Admins: See all projects.
    - Public/Anonymous: See only demos and hyperobjects (excluding unlisted).
    """
    projects = discover_projects()
    enriched = [_enrich_project(p) for p in projects]

    # Check if user is admin
    is_admin = not Config.AUTH_ENABLED
    if Config.AUTH_ENABLED:
        claims = getattr(request, "auth_claims", None)
        if claims:
            roles = claims.get("roles", [])
            if isinstance(roles, str):
                roles = [roles]
            if claims.get("role"):
                roles.append(claims.get("role"))
            is_admin = "admin" in roles

    # If not admin, filter the list
    if not is_admin and Config.AUTH_ENABLED:
         enriched = [
             p for p in enriched 
             if (p.get("is_demo") or p.get("is_hyperobject"))
             and not p.get("unlisted", False)
         ]
    
    return jsonify(enriched)


@admin_bp.route('/api/admin/projects/<slug>', methods=['GET'])
@require_valid_slug
@require_role("admin")
def admin_project_detail(slug: str) -> Response | tuple[Response, int]:
    """Return detailed info for a single project."""
    project_dir = Config.PROJECTS_DIR / slug
    manifest_path = project_dir / "project.json"

    if not project_dir.is_dir() or not manifest_path.exists():
        return error_response(f"Project '{slug}' not found", 404, error_code="project_not_found")

    projects = discover_projects()
    proj = next((p for p in projects if p["slug"] == slug), None)
    if not proj:
        return error_response(f"Project '{slug}' not found", 404, error_code="project_not_found")

    proj = _enrich_project(proj)

    # SCAD files with sizes
    scad_files = []
    for f in sorted(project_dir.glob("*.scad")):
        scad_files.append({"name": f.name, "size": f.stat().st_size})
    proj["scad_files"] = scad_files

    # Modes detail
    try:
        m = get_manifest(slug)
        proj["modes"] = [
            {"id": mode["id"], "label": mode.get("label", mode["id"]), "scad_file": mode["scad_file"]}
            for mode in m.modes
        ]
    except Exception:
        proj["modes"] = []

    # Exports with sizes
    exports = []
    exports_dir = project_dir / "exports"
    if exports_dir.is_dir():
        for f in sorted(exports_dir.glob("*.stl")):
            exports.append({"name": f.name, "size": f.stat().st_size})
    proj["exports"] = exports

    return jsonify(proj)


@admin_bp.route('/api/admin/projects/<slug>/flags', methods=['PATCH'])
@require_valid_slug
@require_role("admin")
def patch_project_flags(slug: str) -> Response | tuple[Response, int]:
    """
    Toggle is_demo and/or is_hyperobject flags for a project.

    Body (JSON):
      { "is_demo": true, "is_hyperobject": false }

    Only keys present in the body are updated; others are left unchanged.
    Writes directly to projects/<slug>/project.json.
    """
    raw = _load_raw_manifest(slug)
    if raw is None:
        return error_response(f"Project '{slug}' not found", 404)

    body = request.get_json(silent=True) or {}
    unknown = set(body.keys()) - _ALLOWED_FLAGS
    if unknown:
        return error_response(f"Unknown flags: {sorted(unknown)}", 400)

    project_obj = raw.setdefault("project", {})
    changed = {}

    if "is_demo" in body:
        val = bool(body["is_demo"])
        project_obj["is_demo"] = val
        changed["is_demo"] = val

    if "is_hyperobject" in body:
        val = bool(body["is_hyperobject"])
        ho = project_obj.setdefault("hyperobject", {})
        ho["is_hyperobject"] = val
        changed["is_hyperobject"] = val

    if "unlisted" in body:
        val = bool(body["unlisted"])
        project_obj["unlisted"] = val
        changed["unlisted"] = val

    if not changed:
        return error_response("No valid flags provided", 400)

    try:
        _save_raw_manifest(slug, raw)
    except OSError as exc:
        logger.exception("Failed to write project.json for %s", slug)
        return error_response(f"Failed to save: {exc}", 500)

    logger.info("Admin updated flags for %s: %s", slug, changed)
    return jsonify({"slug": slug, "updated": changed})


@admin_bp.route('/api/admin/projects/tablaco/public-link', methods=['GET'])
@require_role("admin")
def tablaco_public_link() -> Response:
    """
    Return the public storefront URL for the tablaco project.

    This is the ONLY endpoint that exposes the tablaco public link.
    Protected by admin role — not available in any public API.
    """
    from utils.studio_url import build_project_url, get_studio_base_url

    url = build_project_url("tablaco", mode="storefront")
    studio_url = f"{get_studio_base_url()}/project/tablaco"

    return jsonify({
        "slug": "tablaco",
        "public_url": url,
        "studio_url": studio_url,
        "note": "Share this URL to give customers access to the Tablaco storefront.",
    })


@admin_bp.route('/api/admin/analytics/global', methods=['GET'])
@require_role("admin")
def admin_global_analytics() -> Response:
    """
    Aggregate analytics across all projects for the last N days.

    Query params:
      ?days=30  (default 30)

    Returns:
      {
        total_renders, total_exports, total_events,
        daily_renders: [{date, count}],
        top_projects: [{slug, renders}]
      }
    """
    days = int(request.args.get("days", 30))
    since = time.time() - (days * 86400)

    # Total event counts by type
    count_rows = (
        db.session.query(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
        .filter(AnalyticsEvent.created_at > since)
        .group_by(AnalyticsEvent.event_type)
        .all()
    )
    counts = {row[0]: row[1] for row in count_rows}
    total_renders = counts.get("render", 0)
    total_exports = counts.get("export", 0)
    total_events = sum(counts.values())

    # Daily render counts (database-agnostic: fetch timestamps, bucket in Python)
    daily_rows = (
        db.session.query(AnalyticsEvent.created_at)
        .filter(
            AnalyticsEvent.event_type == "render",
            AnalyticsEvent.created_at > since,
        )
        .all()
    )
    daily_counts: dict[str, int] = {}
    for (ts,) in daily_rows:
        day = time.strftime("%Y-%m-%d", time.gmtime(ts))
        daily_counts[day] = daily_counts.get(day, 0) + 1
    daily_renders = sorted(
        [{"date": d, "count": c} for d, c in daily_counts.items()],
        key=lambda x: x["date"],
    )

    # Top projects by render count
    top_rows = (
        db.session.query(AnalyticsEvent.project, func.count(AnalyticsEvent.id))
        .filter(
            AnalyticsEvent.event_type == "render",
            AnalyticsEvent.created_at > since,
        )
        .group_by(AnalyticsEvent.project)
        .order_by(func.count(AnalyticsEvent.id).desc())
        .limit(10)
        .all()
    )
    top_projects = [{"slug": row[0], "renders": row[1]} for row in top_rows]

    return jsonify({
        "period_days": days,
        "total_renders": total_renders,
        "total_exports": total_exports,
        "total_events": total_events,
        "event_counts": counts,
        "daily_renders": daily_renders,
        "top_projects": top_projects,
    })


@admin_bp.route('/api/admin/renders/active', methods=['GET'])
@require_role("admin")
def admin_active_renders() -> Response:
    """Return active render information."""
    active_state = _collect_active_render_state()
    recent = _collect_recent_render_events(limit=10)

    note_parts = []
    if active_state.get("note"):
        note_parts.append(active_state["note"])

    if active_state["queued_jobs"] > 0:
        note_parts.append(f"{active_state['queued_jobs']} render task(s) waiting in queue")

    if not note_parts:
        note_parts.append("Live render state sourced from Redis worker tracking and analytics DB recency.")

    return jsonify({
        "active_renders": active_state["active_count"],
        "queued_renders": active_state["queued_jobs"],
        "active_jobs": active_state["active_jobs"],
        "recent": recent,
        "note": " | ".join(note_parts),
    })
