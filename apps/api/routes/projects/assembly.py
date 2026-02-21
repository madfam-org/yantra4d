"""
Assembly Blueprint — auto-generate assembly steps from BOSL2 attach() graphs.

Endpoints:
  GET  /api/projects/<slug>/assembly-steps
       Returns auto-generated assembly steps (does NOT modify project.json).

  POST /api/projects/<slug>/assembly-steps/write
       Writes the generated steps back into project.json (merges with manual steps).
"""

import json
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from config import Config
from utils.route_helpers import error_response
from services.core.scad_analyzer import analyze_directory
from services.core.assembly_generator import generate_assembly_steps, merge_assembly_steps

assembly_bp = Blueprint("assembly", __name__)
logger = logging.getLogger(__name__)


def _project_dir(slug: str) -> Path | None:
    base = Path(Config.PROJECTS_DIR) / slug
    return base if base.is_dir() else None


def _load_manifest(slug: str) -> dict | None:
    d = _project_dir(slug)
    if not d:
        return None
    p = d / "project.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


@assembly_bp.route("/api/projects/<slug>/assembly-steps", methods=["GET"])
def get_assembly_steps(slug: str):
    """
    Auto-generate assembly steps from BOSL2 attach() calls in the project's SCAD files.
    Returns the generated steps without modifying project.json.
    """
    project_dir = _project_dir(slug)
    if not project_dir:
        return error_response(f"Project '{slug}' not found", 404)

    manifest = _load_manifest(slug)
    if not manifest:
        return error_response(f"No project.json found for '{slug}'", 404)

    try:
        analysis = analyze_directory(project_dir)
    except Exception as exc:
        logger.exception("SCAD analysis failed for %s", slug)
        return error_response(f"SCAD analysis failed: {exc}", 500)

    try:
        steps = generate_assembly_steps(manifest, analysis)
    except Exception as exc:
        logger.exception("Assembly generation failed for %s", slug)
        return error_response(f"Assembly generation failed: {exc}", 500)

    existing = manifest.get("assembly_steps", [])
    has_manual = any(not s.get("_auto_generated") for s in existing)

    return jsonify({
        "slug": slug,
        "source": "bosl2_attach_graph",
        "has_manual_steps": has_manual,
        "step_count": len(steps),
        "assembly_steps": steps,
    })


@assembly_bp.route("/api/projects/<slug>/assembly-steps/write", methods=["POST"])
def write_assembly_steps(slug: str):
    """
    Write auto-generated assembly steps back into project.json.
    Merges with any existing manually-authored steps (manual steps take precedence).

    Body (optional JSON):
      { "merge": true }   — merge with existing manual steps (default)
      { "merge": false }  — replace all steps with generated ones
    """
    project_dir = _project_dir(slug)
    if not project_dir:
        return error_response(f"Project '{slug}' not found", 404)

    manifest = _load_manifest(slug)
    if not manifest:
        return error_response(f"No project.json found for '{slug}'", 404)

    body = request.get_json(silent=True) or {}
    do_merge = body.get("merge", True)

    try:
        analysis = analyze_directory(project_dir)
        generated = generate_assembly_steps(manifest, analysis)
    except Exception as exc:
        logger.exception("Assembly generation failed for %s", slug)
        return error_response(f"Assembly generation failed: {exc}", 500)

    existing = manifest.get("assembly_steps", [])
    final_steps = merge_assembly_steps(existing, generated) if do_merge else generated

    manifest["assembly_steps"] = final_steps

    manifest_path = project_dir / "project.json"
    try:
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    except OSError as exc:
        return error_response(f"Failed to write project.json: {exc}", 500)

    logger.info("Wrote %d assembly steps to %s/project.json", len(final_steps), slug)
    return jsonify({
        "slug": slug,
        "written": len(final_steps),
        "merged": do_merge,
        "assembly_steps": final_steps,
    })
