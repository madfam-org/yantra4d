"""
Project source CRUD API — read/write/create/delete editable files in a project.

Handles OpenSCAD scripts and node-graph documents. A graph document is
validated against the transpiler's own rules before it is written, so the
editor cannot leave a cartridge in a state that fails at render time.
"""
import functools
import json
import logging
import os
import re
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request

import rate_limits
from extensions import limiter
from manifest import invalidate_cache
from middleware.auth import claim_roles, ensure_optional_auth, require_tier
from services.core.cartridge_ownership import claims_sub, owner_sub
from services.core.project_access import dev_unlock_active, require_project_access
from services.engine.render_source import graph_sources
from utils.project_resolver import find_project_dir, require_project
from utils.route_helpers import error_response, safe_join_path
from utils.validators import require_valid_slug

logger = logging.getLogger(__name__)

editor_bp = Blueprint("editor", __name__)

MAX_FILE_SIZE = 512 * 1024  # 512KB
# ``.graph.json`` is matched on the full suffix chain, not ``Path.suffix``
# (which would see only ``.json``), so an arbitrary ``.json`` stays rejected.
ALLOWED_EXTENSIONS = {".scad"}
GRAPH_SUFFIX = ".graph.json"


def _validate_filepath(project_dir: Path, filepath: str) -> Path | None:
    """Validate file path: must be .scad, within project dir, no traversal."""
    resolved = safe_join_path(str(project_dir), filepath)
    if resolved is None:
        return None
    if resolved.suffix not in ALLOWED_EXTENSIONS and not resolved.name.endswith(GRAPH_SUFFIX):
        return None
    return resolved


def _graph_rejection(resolved: Path, content: str) -> str | None:
    """Return why this graph document must not be saved, or None if it is fine.

    The transpiler is the authority: validating here means the editor reports a
    dangling input or a cycle immediately, instead of the author discovering it
    when a render fails.
    """
    if not resolved.name.endswith(GRAPH_SUFFIX):
        return None
    from services.engine.graph_engine import GraphError, transpile

    try:
        document = json.loads(content)
    except json.JSONDecodeError as exc:
        return f"That is not valid JSON: {exc}"
    try:
        transpile(document, {}, resolved.name)
    except GraphError as exc:
        return str(exc)
    return None


# ── Who may write a cartridge ─────────────────────────────────────────────────
#
# The API writes only into a cartridge it created for someone: a fork
# (POST /api/projects/<slug>/fork) or an imported repository
# (POST /api/github/import). Both record that in project.meta.json
# `source.type`. A built-in commons cartridge has no project.meta.json; it, and
# any cartridge whose source type is missing, unreadable or unknown, is
# read-only through the API — fork it to edit a copy.
#
# A fork or import is writable only by the account that created it (its `sub`
# is recorded at creation, see services/core/cartridge_ownership.py) or by an
# admin (the `admin` app role, the same one require_role("admin") checks). A
# fork or import with no recorded creator is writable by admins only. With auth
# disabled, the local-development unlock that opens private projects
# (auth off AND the Flask debugger on) opens these too; nothing else does.

#: `source.type` values whose cartridges the API may write.
WRITABLE_SOURCE_TYPES = frozenset({"fork", "github"})

#: Error codes the Studio branches on. Stable API surface — do not rename.
READ_ONLY_ERROR_CODE = "read_only_cartridge"
NOT_OWNER_ERROR_CODE = "not_cartridge_owner"

_REFUSAL_MESSAGES = {
    READ_ONLY_ERROR_CODE: "This is a built-in cartridge and is read-only. Fork it to edit your own copy.",
    NOT_OWNER_ERROR_CODE: "This cartridge belongs to another account. Fork it to edit your own copy.",
}


def _project_source_type(project_dir: Path) -> str | None:
    """`source.type` from project.meta.json, or None when there is none."""
    meta_path = project_dir / "project.meta.json"
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    source = meta.get("source") if isinstance(meta, dict) else None
    kind = source.get("type") if isinstance(source, dict) else None
    return kind if isinstance(kind, str) else None


def cartridge_write_refusal(slug: str, project_dir: Path, claims: dict | None) -> str | None:
    """Why this caller may not write this cartridge (an error code), or None if they may.

    The one decision behind the write guard and the `can_write` flag the API
    reports, so the two cannot disagree.
    """
    if _project_source_type(project_dir) not in WRITABLE_SOURCE_TYPES:
        return READ_ONLY_ERROR_CODE
    if dev_unlock_active():
        return None
    if "admin" in claim_roles(claims):
        return None
    sub = claims_sub(claims)
    owner = owner_sub(slug, project_dir)
    if sub is not None and owner is not None and sub == owner:
        return None
    return NOT_OWNER_ERROR_CODE


def cartridge_write_refusal_response(code: str):
    """The 403 for a refusal code from :func:`cartridge_write_refusal`."""
    return error_response(_REFUSAL_MESSAGES[code], 403, error_code=code)


def check_writable_cartridge(slug: str):
    """The 403 when the caller may not write ``slug``, else None (unknown slug → None).

    For routes that take the slug in the request body; path-parameter routes
    use :func:`require_writable_cartridge`.
    """
    project_dir = find_project_dir(slug)
    if project_dir is None:
        return None
    code = cartridge_write_refusal(slug, project_dir, ensure_optional_auth())
    return cartridge_write_refusal_response(code) if code else None


def require_writable_cartridge(fn):
    """Decorator for every route that writes into an existing ``<slug>`` cartridge.

    Place it below ``require_project_access`` (privacy is settled first, so a
    private project still answers ``project_locked``) and above
    ``require_project(auto_git=True)`` (so nothing — not even the ``.git`` that
    auto_git creates — is written into a cartridge the caller may not write).
    An unknown slug passes through to the route's own 404.
    """
    @functools.wraps(fn)
    def wrapper(*args, slug: str, **kwargs):
        refused = check_writable_cartridge(slug)
        if refused is not None:
            return refused
        return fn(*args, slug=slug, **kwargs)
    return wrapper


@editor_bp.route("/api/projects/<slug>/files", methods=["GET"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
@require_project()
@require_project_access
def list_files(slug, project_dir):

    files = []
    for p in sorted([*project_dir.rglob("*.scad"), *project_dir.rglob(f"*{GRAPH_SUFFIX}")]):
        rel = p.relative_to(project_dir)
        # Skip hidden dirs, node_modules, .git
        if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
            continue
        files.append({
            "path": str(rel),
            "name": p.name,
            "size": p.stat().st_size,
        })

    return jsonify(sorted(files, key=lambda f: f["path"]))


@editor_bp.route("/api/projects/<slug>/files/<path:filepath>", methods=["GET"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_READ)
@require_project()
@require_project_access
def read_file(slug, filepath, project_dir):

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path", 400)
    if not resolved.is_file():
        return error_response("File not found", 404)

    try:
        content = resolved.read_text(encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to read file: {e}", 500)

    return jsonify({"path": filepath, "content": content, "size": len(content)})


@editor_bp.route("/api/projects/<slug>/files/<path:filepath>", methods=["PUT"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_WRITE)
@require_project_access
@require_writable_cartridge
@require_project(auto_git=True)
def write_file(slug, filepath, project_dir):

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path", 400)
    if not resolved.is_file():
        return error_response("File not found", 404)

    data = request.json
    if not data or "content" not in data:
        return error_response("content is required", 400)

    content = data["content"]
    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        return error_response(f"File exceeds maximum size of {MAX_FILE_SIZE // 1024}KB", 400)

    rejection = _graph_rejection(resolved, content)
    if rejection:
        return error_response(rejection, 400)

    try:
        resolved.write_text(content, encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to write file: {e}", 500)

    return jsonify({"path": filepath, "size": len(content)})


@editor_bp.route("/api/projects/<slug>/files", methods=["POST"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_CREATE)
@require_project_access
@require_writable_cartridge
@require_project(auto_git=True)
def create_file(slug, project_dir):

    data = request.json
    if not data or "path" not in data:
        return error_response("path is required", 400)

    filepath = data["path"]
    content = data.get("content", "")

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path (must be .scad or .graph.json)", 400)
    if resolved.exists():
        return error_response("File already exists", 409)

    if len(content.encode("utf-8")) > MAX_FILE_SIZE:
        return error_response(f"File exceeds maximum size of {MAX_FILE_SIZE // 1024}KB", 400)

    rejection = _graph_rejection(resolved, content)
    if rejection:
        return error_response(rejection, 400)

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
    except OSError as e:
        return error_response(f"Failed to create file: {e}", 500)

    return jsonify({"path": filepath, "size": len(content)}), 201


@editor_bp.route("/api/projects/<slug>/files/<path:filepath>", methods=["DELETE"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_DELETE)
@require_project_access
@require_writable_cartridge
@require_project(auto_git=True)
def delete_file(slug, filepath, project_dir):

    resolved = _validate_filepath(project_dir, filepath)
    if not resolved:
        return error_response("Invalid file path", 400)
    if not resolved.is_file():
        return error_response("File not found", 404)

    try:
        resolved.unlink()
    except OSError as e:
        return error_response(f"Failed to delete file: {e}", 500)

    return jsonify({"deleted": filepath})


# ── Graph bindings (fork-only manifest write) ─────────────────────────────────
#
# A graph node param is driven by a manifest parameter through that parameter's
# `binding` ("nodeId.param", or a list of them). The Studio graph editor binds
# and unbinds params, so it needs to change `binding` — and nothing else — in
# the manifest. This route is deliberately narrow:
#
#   * it only writes a FORK (project.meta.json source.type == "fork"): a commons
#     cartridge is refused by `require_writable_cartridge` (403
#     `read_only_cartridge`) before `auto_git` runs, and an imported repo is
#     refused by the route itself (403 `not_a_fork`);
#   * it can only set or clear `binding` on parameters that already exist;
#   * the merged binding map must transpile against every graph source of the
#     project, so a binding can never point at a node or param that is not there;
#   * the write is atomic (temp file + rename), so a crash cannot truncate the
#     manifest.

MAX_BINDINGS_BODY = 16 * 1024  # bytes
MAX_TARGETS_PER_PARAMETER = 50
_BINDING_TARGET_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*$")


def _parse_bindings_body(raw: bytes) -> tuple[dict | None, str | None]:
    """Strictly parse {"bindings": {param_id: target | [targets] | null}}."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Body must be JSON"
    if not isinstance(data, dict) or set(data) != {"bindings"}:
        return None, 'Body must be exactly {"bindings": {...}}'
    changes = data["bindings"]
    if not isinstance(changes, dict) or not changes:
        return None, "bindings must be a non-empty object of parameter id to binding"
    for pid, value in changes.items():
        if value is None:
            continue
        targets = value if isinstance(value, list) else [value]
        if not targets or len(targets) > MAX_TARGETS_PER_PARAMETER:
            return None, f"parameter '{pid}': a binding needs 1 to {MAX_TARGETS_PER_PARAMETER} targets"
        for target in targets:
            if not isinstance(target, str) or not _BINDING_TARGET_RE.match(target):
                return None, f"parameter '{pid}': invalid binding {target!r} (want 'nodeId.param')"
        if len(set(targets)) != len(targets):
            return None, f"parameter '{pid}': duplicate binding target"
    return changes, None


def _graph_sources(project_dir: Path, manifest_data: dict) -> list[Path]:
    """Every graph document the manifest's modes render, path-guarded.

    Graph-engine modes and, in a user cartridge, each mode's declared
    ``graph_file`` (its render source): services/engine/render_source.py.
    """
    return graph_sources(project_dir, manifest_data)


def _write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON to `path` through a temp file in the same directory + rename."""
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


@editor_bp.route("/api/projects/<slug>/manifest/bindings", methods=["PUT"])
@require_valid_slug
@require_tier("pro")
@limiter.limit(rate_limits.EDITOR_WRITE)
@require_project_access
@require_writable_cartridge
@require_project(auto_git=True)
def update_graph_bindings(slug, project_dir):
    """Set or clear `binding` on existing manifest parameters of a forked graph project.

    A commons cartridge is refused by `require_writable_cartridge` (403
    `read_only_cartridge`) before `auto_git` can touch it. An imported repository
    passes that guard but is still refused here: binding edits are fork-only.
    """
    if _project_source_type(project_dir) != "fork":
        return error_response(
            "Bindings can only be edited on your fork of a project. Fork it first.",
            403, error_code="not_a_fork",
        )

    if (request.content_length or 0) > MAX_BINDINGS_BODY:
        return error_response(f"Body exceeds {MAX_BINDINGS_BODY // 1024}KB", 413, error_code="body_too_large")
    raw = request.get_data(cache=False)
    if len(raw) > MAX_BINDINGS_BODY:
        return error_response(f"Body exceeds {MAX_BINDINGS_BODY // 1024}KB", 413, error_code="body_too_large")
    changes, err = _parse_bindings_body(raw)
    if err:
        return error_response(err, 400, error_code="invalid_bindings")

    manifest_path = project_dir / "project.json"
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return error_response(f"Cannot read the project manifest: {exc}", 500)
    parameters = manifest_data.get("parameters")
    if not isinstance(parameters, list):
        return error_response("The manifest has no parameters to bind", 400, error_code="invalid_bindings")

    by_id = {p.get("id"): p for p in parameters if isinstance(p, dict)}
    unknown = sorted(pid for pid in changes if pid not in by_id)
    if unknown:
        return error_response(
            f"Unknown parameter(s): {', '.join(unknown)}. Only existing parameters can be bound.",
            400, error_code="unknown_parameter",
        )

    sources = _graph_sources(project_dir, manifest_data)
    if not sources:
        return error_response("This project has no graph source to bind", 400, error_code="no_graph_source")

    for pid, value in changes.items():
        if value is None:
            by_id[pid].pop("binding", None)
        else:
            by_id[pid]["binding"] = value

    from services.engine.graph_engine import GraphError, extract_bindings, load_graph_document, transpile

    try:
        bindings = extract_bindings(parameters)
        for source in sources:
            document, _raw = load_graph_document(str(source))
            transpile(document, bindings, source.name)
    except GraphError as exc:
        return error_response(str(exc), 400, error_code="invalid_bindings")

    try:
        _write_json_atomic(manifest_path, manifest_data)
    except OSError as exc:
        return error_response(f"Failed to write the manifest: {exc}", 500)
    invalidate_cache(slug)

    current = {p["id"]: p["binding"] for p in parameters if isinstance(p, dict) and p.get("binding")}
    return jsonify({"bindings": current})
