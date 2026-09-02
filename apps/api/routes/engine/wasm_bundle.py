"""
WASM Bundle Blueprint

``GET /api/projects/<slug>/wasm-bundle`` — every source file, library and font a
browser render of an OpenSCAD cartridge needs, in one response.

Thin route layer: resolution, confinement, font selection, feature detection and
caching all live in ``services/engine/wasm_bundle.py``. What is decided here is
who may ask, what a refusal looks like, and how the answer is cached.

Deliberately not rate-limited beyond the app-wide default. The browser path is
the free one — it costs the server one read of an already-cached bundle and no
CPU at all — so throttling it by tier would push traffic onto the render
endpoints, which are the expensive thing the tiers exist to ration.
"""
import json
import logging

from flask import Blueprint, jsonify, make_response, request

from manifest import get_manifest
from middleware.auth import optional_auth
from services.core.project_access import is_private_project, require_project_access
from services.engine.wasm_bundle import (
    BundleTooLarge,
    get_bundle,
    openscad_entry_files,
)
from utils.route_helpers import error_response, handle_exceptions
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

wasm_bundle_bp = Blueprint('wasm_bundle', __name__)

#: Refusal for a cartridge with no OpenSCAD mode. CadQuery and the graph
#: transpiler are Python, the implicit engine is native SDF code — none of them
#: has a WASM build the Studio can load, so a bundle for them would be a promise
#: nothing can keep. Stable API surface: the Studio branches on this code.
NON_WASM_ERROR_CODE = "engine_not_wasm"


@wasm_bundle_bp.route('/api/projects/<slug>/wasm-bundle', methods=['GET'])
@require_valid_slug
@optional_auth
@require_project_access
@handle_exceptions
def get_wasm_bundle(slug):
    """Return the browser-render bundle for one OpenSCAD cartridge."""
    try:
        manifest = get_manifest(slug)
    except RuntimeError:
        return error_response("Project not found", 404, error_code="project_not_found")

    # An unresolvable slug falls back to the single-project directory, which
    # would otherwise hand out a different cartridge's sources under the name
    # that was asked for.
    if manifest.project.get("slug") != slug and manifest.project_dir.name != slug:
        return error_response("Project not found", 404, error_code="project_not_found")

    # Settled before any file is read: a CadQuery cartridge's modes point at
    # `.py` files, and walking those as if they were SCAD would be nonsense
    # dressed up as an answer.
    if not openscad_entry_files(manifest):
        return error_response(
            f"Project renders with the '{manifest.engine}' engine, which has no browser kernel",
            400, error_code=NON_WASM_ERROR_CODE,
        )

    try:
        bundle = get_bundle(manifest, slug)
    except BundleTooLarge as e:
        response, status = error_response(
            "Project sources exceed the browser bundle limit", 413,
            error_code="bundle_too_large",
        )
        payload = response.get_json()
        payload.update({
            "files": e.files, "bytes": e.bytes,
            "max_files": e.max_files, "max_bytes": e.max_bytes,
        })
        return jsonify(payload), status

    body = json.dumps(bundle.as_json(), sort_keys=True)

    if is_private_project(slug, manifest):
        # Same reasoning as the private manifest route: an ETag is a stable,
        # guessable handle to the content being withheld, and a 304 would let an
        # intermediary keep serving a body it should never have stored.
        resp = make_response(body)
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Cache-Control"] = "private, no-store"
        return resp

    if request.if_none_match and bundle.etag in request.if_none_match:
        resp = make_response("", 304)
        resp.headers["ETag"] = bundle.etag
        resp.headers["Cache-Control"] = "public, max-age=300"
        return resp

    resp = make_response(body)
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Cache-Control"] = "public, max-age=300"
    resp.headers["ETag"] = bundle.etag
    return resp
