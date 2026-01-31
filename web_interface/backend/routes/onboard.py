"""
Onboard Blueprint
Handles /api/projects/analyze and /api/projects/create for onboarding external SCAD projects.
"""
import json
import logging
import shutil
import tempfile
from pathlib import Path

from flask import Blueprint, request, jsonify

from config import Config
from extensions import limiter
from services.manifest_generator import generate_manifest
from services.route_helpers import error_response

logger = logging.getLogger(__name__)

onboard_bp = Blueprint('onboard', __name__)


@onboard_bp.route('/api/projects/analyze', methods=['POST'])
@limiter.limit("20/hour")
def analyze_scad_files():
    """Accept uploaded .scad files, analyze them, and return a draft manifest."""
    if 'files' not in request.files:
        return error_response("No files uploaded. Use multipart form with 'files' field.", 400)

    files = request.files.getlist('files')
    if not files:
        return error_response("No .scad files provided.", 400)

    slug = request.form.get('slug', 'new-project')

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for f in files:
            if not f.filename or not f.filename.endswith('.scad'):
                continue
            safe_name = Path(f.filename).name  # strip path components
            f.save(tmp_path / safe_name)

        scad_files = list(tmp_path.glob("*.scad"))
        if not scad_files:
            return error_response("No valid .scad files found in upload.", 400)

        result = generate_manifest(tmp_path, slug=slug)

    return jsonify(result)


@onboard_bp.route('/api/projects/create', methods=['POST'])
@limiter.limit("10/hour")
def create_project():
    """Accept a manifest and .scad files, write them to PROJECTS_DIR."""
    content_type = request.content_type or ''

    if 'multipart' in content_type:
        # Multipart: files + manifest as form field
        manifest_raw = request.form.get('manifest')
        if not manifest_raw:
            return error_response("Missing 'manifest' form field.", 400)
        try:
            manifest_data = json.loads(manifest_raw)
        except json.JSONDecodeError as e:
            return error_response(f"Invalid manifest JSON: {e}", 400)

        files = request.files.getlist('files')
    elif 'json' in content_type:
        # JSON-only: manifest with base64-encoded files (simpler for API use)
        data = request.json
        if not data:
            return error_response("Request body must be JSON.", 400)
        manifest_data = data.get('manifest')
        if not manifest_data:
            return error_response("Missing 'manifest' in JSON body.", 400)
        files = []
    else:
        return error_response("Unsupported content type.", 400)

    slug = manifest_data.get("project", {}).get("slug")
    if not slug:
        return error_response("Manifest must contain project.slug.", 400)

    # Validate slug (alphanumeric + hyphens only)
    if not all(c.isalnum() or c in ('-', '_') for c in slug):
        return error_response("Project slug must be alphanumeric (hyphens/underscores allowed).", 400)

    project_dir = Config.PROJECTS_DIR / slug
    if project_dir.exists():
        return error_response(f"Project '{slug}' already exists.", 409)

    try:
        project_dir.mkdir(parents=True, exist_ok=False)

        # Write manifest
        manifest_path = project_dir / "project.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f, indent=2)

        # Write uploaded SCAD files
        for uploaded in files:
            if not uploaded.filename or not uploaded.filename.endswith('.scad'):
                continue
            safe_name = Path(uploaded.filename).name
            uploaded.save(project_dir / safe_name)

        logger.info(f"Created new project: {slug} at {project_dir}")

        return jsonify({
            "status": "success",
            "slug": slug,
            "path": str(project_dir),
        }), 201

    except Exception as e:
        # Cleanup on failure
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)
        logger.error(f"Failed to create project {slug}: {e}")
        return error_response(f"Failed to create project: {e}")
