"""
Manifest Blueprint
Serves GET /api/manifest — the project manifest as JSON.

Legacy query-string shape (``?project=<slug>``); the per-project route is
``GET /api/projects/<slug>/manifest`` in routes/projects/projects.py. Both
answer the same private-project gate: a slug that is private by its manifest or
by ``PRIVATE_PROJECTS`` is withheld from callers who may not view it.
"""
import hashlib
import json

from flask import Blueprint, make_response, request

from manifest import get_manifest
from services.core.project_access import check_project_access, is_private_project

manifest_bp = Blueprint('manifest', __name__)


@manifest_bp.route('/api/manifest', methods=['GET'])
def serve_manifest():
    """Return the full project manifest."""
    slug = request.args.get("project")
    if not slug:
        from config import Config
        if Config.MULTI_PROJECT:
            return make_response(json.dumps({"error": "project query param required"}), 400)

    # Same gate as /api/projects/<slug>/manifest: privacy is settled before the
    # manifest is serialised. An unknown slug is not the gate's business and
    # still 404s below.
    denied = check_project_access(slug)
    if denied is not None:
        return denied

    try:
        manifest = get_manifest(slug)
        body = json.dumps(manifest.as_json(), sort_keys=True)
    except RuntimeError as e:
        return make_response(json.dumps({"error": str(e)}), 404)

    if is_private_project(slug, manifest):
        # No shared cache and no ETag for a private manifest: the ETag is a
        # stable, guessable handle to the very content being withheld, and a
        # 304 to an entitled caller would let an intermediary keep serving it.
        resp = make_response(body)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    etag = hashlib.md5(body.encode()).hexdigest()

    if request.if_none_match and etag in request.if_none_match:
        return make_response("", 304)

    resp = make_response(body)
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Cache-Control"] = "public, max-age=300"
    resp.headers["ETag"] = etag
    return resp
