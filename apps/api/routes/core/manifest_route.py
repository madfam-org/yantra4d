"""
Manifest Blueprint
Serves GET /api/manifest — the project manifest as JSON.
"""
import hashlib
import json

from flask import Blueprint, make_response, request
from manifest import get_manifest

manifest_bp = Blueprint('manifest', __name__)


@manifest_bp.route('/api/manifest', methods=['GET'])
def serve_manifest():
    """Return the full project manifest."""
    body = json.dumps(get_manifest().as_json(), sort_keys=True)
    etag = hashlib.md5(body.encode()).hexdigest()

    if request.if_none_match and etag in request.if_none_match:
        return make_response("", 304)

    resp = make_response(body)
    resp.headers["Content-Type"] = "application/json"
    resp.headers["Cache-Control"] = "public, max-age=300"
    resp.headers["ETag"] = etag
    return resp
