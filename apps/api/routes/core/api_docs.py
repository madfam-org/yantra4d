"""
API description endpoints: ``/api/openapi.json`` and ``/api/llms.txt``.

``/api/openapi.json`` serves ``docs/reference/openapi.yaml`` — the document the
``openapi-validation`` CI job validates — as JSON, so agents and SDK
generators read the same contract the repository checks. The image carries the
file at ``/app/docs/reference/openapi.yaml`` (apps/api/Dockerfile); in a
checkout it is found by walking up from this file. ``OPENAPI_SPEC_PATH``
overrides both. A missing or unreadable document answers 503, never an empty
or invented one.

``/api/llms.txt`` is a short plain-text guide for language-model agents: where
the contract is, which routes are public, and the error shape.
"""
import json
import logging
import os
from functools import lru_cache
from pathlib import Path

from flask import Blueprint, Response

from utils.route_helpers import error_response

logger = logging.getLogger(__name__)

api_docs_bp = Blueprint("api_docs", __name__)

SPEC_RELATIVE = Path("docs") / "reference" / "openapi.yaml"
CACHE_CONTROL = "public, max-age=300"

LLMS_TXT = """# Yantra4D API

> Parametric 3D design API: browse the open-hardware cartridge commons, render
> a cartridge mode to STL/3MF/GLB with your parameters, and estimate a print.

The full contract is the OpenAPI 3.1 document at /api/openapi.json (the same
file the repository validates in CI: docs/reference/openapi.yaml).

## Public routes (no account needed)

- GET  /api/health — service status
- GET  /api/projects — the cartridge catalog (slug, name, modes)
- GET  /api/projects/{slug}/manifest — one cartridge: modes, parts, parameters
- POST /api/estimate — {project, mode, parameters} -> time/weight/cost heuristic
- POST /api/render — {project, mode, parameters, export_format?} -> parts[] with
  artifact URLs. Guests are rate-limited; some engines and formats need a tier
  (403 names the reason).
- POST /api/render-stream — the same payload, progress as Server-Sent Events
- GET  /api/openapi.json, /api/llms.txt — this description

Send parameters NESTED under "parameters", using the ids and ranges from the
manifest. A numeric parameter must be a finite number.

## Errors

Every error is JSON: {"status": "error", "error": "<message>",
"error_code": "<machine_code>", "request_id": "<id>"}. Examples:
404 project_not_found (unknown project slug), 400 invalid_parameter (adds
"parameter": "<id>"), 400 invalid_mode_id_<id>, 429 rate limited.

## More

- Studio (interactive configurator): https://app.yantra4d.com
- Project site: https://yantra4d.com (llms.txt there describes the platform)
- Source (AGPL-3.0): https://github.com/madfam-org/yantra4d
"""


def _spec_path() -> Path | None:
    override = os.getenv("OPENAPI_SPEC_PATH", "").strip()
    if override:
        return Path(override)
    for parent in Path(__file__).resolve().parents:
        candidate = parent / SPEC_RELATIVE
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=4)
def _load_spec_json(path: str, mtime_ns: int) -> str:
    """The spec at *path* serialised as JSON; keyed on mtime so an edit is picked up."""
    import yaml

    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or "openapi" not in document:
        raise ValueError(f"{path} is not an OpenAPI document")
    return json.dumps(document, separators=(",", ":"), default=str)


@api_docs_bp.route("/api/openapi.json", methods=["GET"])
def openapi_json():
    """The validated OpenAPI document, as JSON."""
    path = _spec_path()
    if path is None or not path.is_file():
        logger.error("OpenAPI document not found (looked for %s; OPENAPI_SPEC_PATH=%r)",
                     SPEC_RELATIVE, os.getenv("OPENAPI_SPEC_PATH"))
        return error_response("OpenAPI document unavailable", 503, error_code="openapi_unavailable")
    try:
        body = _load_spec_json(str(path), path.stat().st_mtime_ns)
    except Exception:
        logger.exception("OpenAPI document at %s could not be loaded", path)
        return error_response("OpenAPI document unavailable", 503, error_code="openapi_unavailable")
    resp = Response(body, mimetype="application/json")
    resp.headers["Cache-Control"] = CACHE_CONTROL
    return resp


@api_docs_bp.route("/api/llms.txt", methods=["GET"])
def llms_txt():
    """Plain-text API guide for language-model agents."""
    resp = Response(LLMS_TXT, mimetype="text/plain")
    resp.headers["Cache-Control"] = CACHE_CONTROL
    return resp
