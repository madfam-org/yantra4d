"""Generator Output Contract v1 (GOC-1): the ``variables.json`` sidecar.

A generator instance is the geometry file(s) of one rendered part plus one
``variables.json`` document saying exactly which cartridge, mode and part
produced them, with which inputs, on which engine, and the digest of every
file. The document carries no material, process, slicer or printer settings.
The schema is owned by ``hyperobjects-spec``
(``hyperobjects_schemas/schemas/generator-output.schema.json``); this module
never keeps a copy of it.

Everything here is deterministic and shared by both sides of the render queue:

* The API resolves the effective parameters once
  (:func:`resolve_render_inputs`, called from ``extract_render_payload``) and
  ships the GOC-1 ``variables`` with the queued payload.
* The render worker digests the files it produced, writes
  ``<artifact>.variables.json`` next to them (:func:`prepare_part_output`) and
  publishes it through the same artifact store, under the same gates.

The digest algorithms (canonical JSON, ``variables_sha256``,
``hyperobjects-tree-v1``, ``instance_id``) must match the contract byte for
byte: every producer and the keystone checker recompute them independently.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import subprocess
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Any, NamedTuple

from config import Config
from services.engine.openscad import validate_params

logger = logging.getLogger(__name__)

FORMAT = "hyperobjects.generator-output"
FORMAT_VERSION = "1.0.0"
TREE_ALGORITHM = "hyperobjects-tree-v1"
PLATFORM = "yantra4d"
COMMONS_REPO = "solid-hyperobjects"

#: Sidecar suffix. The sidecar keeps the artifact's own extension
#: (``<slug>_preview_<hash>_<part>.stl.variables.json``): yantra4d's artifact
#: stem is format-independent, so a bare ``<stem>.variables.json`` would be
#: shared, and overwritten, by the STL, 3MF and STEP renders of one instance.
SIDECAR_SUFFIX = ".variables.json"

#: Keys that steer the engine rather than shape the design (GOC-1 §4 rule 3).
ENGINE_CONTROL_KEYS = frozenset({"render_mode", "target_part", "mode"})

#: Physical keys that never enter ``variables`` (the schema's denylist).
PHYSICAL_EXACT_IDS = frozenset({
    "target_material", "material_profile", "print_material", "filament_type", "infill",
    "infill_density", "infill_pattern", "layer_height", "first_layer_height", "nozzle_diameter",
    "nozzle_temperature", "nozzle_temp", "bed_temperature", "bed_temp", "print_speed",
    "wall_loops", "perimeters", "jerk", "acceleration", "fan_speed", "slicer_profile",
    "printer_profile",
})
PHYSICAL_PREFIXES = ("mat_shrinkage_", "mat_clear_", "thermo_", "slicer_", "printer_", "filament_")

#: Tree digest exclusions (GOC-1 §3.3).
_TREE_EXCLUDED_SEGMENTS = frozenset({".git", "__pycache__", "node_modules"})
_TREE_EXCLUDED_SUFFIXES = frozenset({".md", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf"})

#: Media types for geometry files. IANA-registered where one exists.
_MEDIA_TYPES = {
    ".stl": "model/stl",
    ".3mf": "model/3mf",
    ".glb": "model/gltf-binary",
    ".gltf": "model/gltf+json",
    ".step": "model/step",
    ".stp": "model/step",
    ".obj": "model/obj",
    ".wrl": "model/vrml",
    ".vrml": "model/vrml",
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMONS_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
_CARTRIDGE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


# ──────────────────────────────────────────────
# Digests (GOC-1 §3)
# ──────────────────────────────────────────────

def canonical_json(obj: Any) -> bytes:
    """GOC-1 §3.1 canonical JSON, UTF-8 encoded. Raises on NaN/Infinity."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bytewise(text: str) -> bytes:
    return text.encode("utf-8")


def variables_sha256(variables: list[dict]) -> str:
    """GOC-1 §3.2: sha256 of the canonical ``[[id, value], ...]`` list, sorted by id."""
    pairs = sorted(([v["id"], v["value"]] for v in variables), key=lambda pair: _bytewise(pair[0]))
    return sha256_hex(canonical_json(pairs))


def instance_id(cartridge: str, mode: str, part: str | None, tree_sha256: str, variables_sha: str) -> str:
    """GOC-1 §3.4: deploy-independent identity of one generator instance."""
    return sha256_hex(canonical_json({
        "cartridge": cartridge,
        "mode": mode,
        "part": part,
        "tree_sha256": tree_sha256,
        "variables_sha256": variables_sha,
    }))


def file_digest(path: str | os.PathLike) -> tuple[str, int]:
    """(sha256 hex, size in bytes) of a file, streamed."""
    digest = hashlib.sha256()
    size = 0
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _tree_included(rel_parts: tuple[str, ...]) -> bool:
    if any(segment in _TREE_EXCLUDED_SEGMENTS for segment in rel_parts):
        return False
    if rel_parts and rel_parts[0] == "docs" and len(rel_parts) > 1:
        return False
    return Path(rel_parts[-1]).suffix.lower() not in _TREE_EXCLUDED_SUFFIXES


def _tree_files(root: Path) -> list[tuple[str, Path]]:
    """(relative POSIX path, absolute path) of every file the tree digest covers.

    ``os.walk`` with ``followlinks=False`` never descends into a directory
    symlink; a file symlink is followed by ``isfile`` and by the read. Anything
    that is not a regular file once followed (a dangling link, a socket) is
    skipped.
    """
    files: list[tuple[str, Path]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        rel_dir = Path(dirpath).relative_to(root)
        dirnames[:] = [d for d in dirnames if d not in _TREE_EXCLUDED_SEGMENTS]
        for name in filenames:
            rel_parts = (*rel_dir.parts, name)
            full = Path(dirpath, name)
            if _tree_included(rel_parts) and full.is_file():
                files.append(("/".join(rel_parts), full))
    files.sort(key=lambda item: _bytewise(item[0]))
    return files


def compute_tree_sha256(directory: str | os.PathLike) -> str:
    """GOC-1 §3.3 ``hyperobjects-tree-v1`` digest of a cartridge directory, uncached."""
    lines = "".join(f"{file_digest(full)[0]}  {rel}\n" for rel, full in _tree_files(Path(directory)))
    return sha256_hex(lines.encode("utf-8"))


_tree_cache: dict[str, tuple[tuple, str]] = {}
_tree_cache_lock = threading.Lock()


def tree_sha256(directory: str | os.PathLike) -> str:
    """Cached :func:`compute_tree_sha256`, keyed per cartridge directory.

    The cache is invalidated by a stat fingerprint (path, size, mtime of every
    covered file), so a cartridge edited through the editor routes is digested
    again on its next render. A stat walk is cheap; re-hashing every source on
    every part render is not.
    """
    root = Path(directory).resolve()
    fingerprint = tuple(
        (rel, stat.st_size, stat.st_mtime_ns)
        for rel, full in _tree_files(root)
        for stat in (full.stat(),)
    )
    key = str(root)
    with _tree_cache_lock:
        cached = _tree_cache.get(key)
        if cached is not None and cached[0] == fingerprint:
            return cached[1]
    digest = compute_tree_sha256(root)
    with _tree_cache_lock:
        _tree_cache[key] = (fingerprint, digest)
    return digest


def media_type_for(path: str) -> str:
    return _MEDIA_TYPES.get(Path(path).suffix.lower(), "application/octet-stream")


def is_physical_key(key: str) -> bool:
    return key in PHYSICAL_EXACT_IDS or key.startswith(PHYSICAL_PREFIXES)


def sidecar_name(artifact_name: str) -> str:
    return f"{artifact_name}{SIDECAR_SUFFIX}"


def is_sidecar_name(name: str) -> bool:
    return name.lower().endswith(SIDECAR_SUFFIX)


def described_artifact_name(sidecar: str) -> str:
    """The artifact a sidecar describes: ``x_body.stl.variables.json`` → ``x_body.stl``."""
    return sidecar[: -len(SIDECAR_SUFFIX)] if is_sidecar_name(sidecar) else sidecar


# ──────────────────────────────────────────────
# Parameter resolution (GOC-1 §4 rules 1-4)
# ──────────────────────────────────────────────

class ResolvedParameters(NamedTuple):
    """What the engine receives, and what ``variables.json`` says it received."""

    engine_params: dict
    variables: list[dict]
    legacy_physical_inputs: dict


def parameter_applies_to_mode(defn: dict, mode_id: str | None) -> bool:
    """Whether a manifest parameter is scoped to *mode_id*.

    ``modes`` and ``visible_in_modes`` both scope a parameter; when a manifest
    declares both, the parameter applies only where both agree. A parameter
    with neither applies everywhere, and so does every parameter of a legacy
    ``scad_file`` render, which has no mode to scope by.
    """
    if not mode_id or mode_id == "legacy":
        return True
    for key in ("modes", "visible_in_modes"):
        scope = defn.get(key)
        if isinstance(scope, list) and mode_id not in scope:
            return False
    return True


def _variable_value(defn: dict, engine_value: Any) -> tuple[Any, str]:
    """Manifest-typed value and GOC-1 ``type`` for an injected engine value.

    The engine receives a checkbox as 0/1 (OpenSCAD has no other boolean
    spelling on the command line); the document records the boolean. A select
    keeps the declared option's own type, which is what the engine received.
    """
    param_type = defn.get("type", "slider")
    if param_type == "checkbox":
        return bool(engine_value), "boolean"
    if isinstance(engine_value, bool):
        return engine_value, "boolean"
    if isinstance(engine_value, (int, float)):
        return engine_value, "number"
    return str(engine_value), "string"


def _measurement_code(defn: dict) -> str | None:
    measurement = defn.get("measurement")
    if isinstance(measurement, dict) and isinstance(measurement.get("code"), str):
        return measurement["code"]
    if isinstance(measurement, str):
        return measurement
    return None


def _drop_non_finite(params: dict) -> None:
    """Refuse NaN and Infinity, which ``float()`` accepts from a string.

    Neither is a value a kernel can be given meaningfully, and neither can be
    written to a JSON document, so the parameter is treated as not sent.
    """
    for key in [k for k, v in params.items() if isinstance(v, float) and not math.isfinite(v)]:
        logger.warning("Rejecting non-finite value for %s", key)
        params.pop(key)


def resolve_effective_parameters(manifest, mode_id: str | None, raw_params: dict, *,
                                 inject_full: bool, validate=None) -> ResolvedParameters:
    """Resolve the engine parameters and their GOC-1 ``variables`` entries.

    Validation is ``validate_params`` itself (clamping, select membership,
    checkbox → 0/1, text sanitisation), so the document records exactly what
    the engine is given. With ``inject_full`` every in-scope manifest default
    is injected too (``source: manifest_default``) and the instance is
    complete; without it a parameter the caller did not send is recorded as
    ``source_default`` with value ``null`` — the kernel falls back to its own
    source literal, which this platform does not guess at.

    A declared parameter outside the mode's scope that the caller sent anyway
    still reaches the engine, so it is recorded as well: ``variables`` lists
    what was injected, never less.

    *validate* defaults to ``validate_params`` for this manifest; the
    orchestrator passes its own binding so the slug it resolves is the one
    validated against.
    """
    if validate is None:
        def validate(params):
            return validate_params(params, manifest.slug)
    raw = raw_params if isinstance(raw_params, dict) else {}
    defs = {p["id"]: p for p in (getattr(manifest, "parameters", None) or []) if isinstance(p, dict) and "id" in p}
    in_scope = {pid for pid, defn in defs.items() if parameter_applies_to_mode(defn, mode_id)}

    requested = validate(raw)
    _drop_non_finite(requested)
    engine_params = dict(requested)
    sources = {key: "request" for key in requested}

    if inject_full:
        defaults = {pid: defs[pid]["default"] for pid in in_scope
                    if pid not in requested and "default" in defs[pid]}
        resolved_defaults = validate(defaults)
        _drop_non_finite(resolved_defaults)
        for key, value in resolved_defaults.items():
            engine_params[key] = value
            sources[key] = "manifest_default"

    variables: list[dict] = []
    physical: dict = {}
    for pid in sorted(in_scope | set(engine_params), key=_bytewise):
        if pid in ENGINE_CONTROL_KEYS or pid not in defs:
            continue
        injected = pid in engine_params
        if is_physical_key(pid):
            if injected:
                physical[pid] = engine_params[pid]
            continue
        defn = defs[pid]
        if injected:
            value, value_type = _variable_value(defn, engine_params[pid])
            entry = {"id": pid, "value": value, "type": value_type, "source": sources[pid]}
        else:
            _, value_type = _variable_value(defn, defn.get("default", ""))
            entry = {"id": pid, "value": None, "type": value_type, "source": "source_default"}
        code = _measurement_code(defn)
        if code:
            entry["measurement"] = code
        variables.append(entry)

    return ResolvedParameters(engine_params, variables, physical)


def _scalar(value: Any) -> Any:
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def resolve_render_inputs(manifest, mode_id: str | None, raw_params: dict, *, material_injector,
                          validate=None) -> tuple[dict, dict | None]:
    """Engine params plus the payload's ``generator_inputs`` (``None`` when disabled).

    This is the whole ``extract_render_payload`` hook. It honours the three
    flags in ``config.py``:

    * ``RENDER_INJECT_FULL_PARAMS`` — see :func:`resolve_effective_parameters`.
    * ``RENDER_MATERIAL_INJECTION`` (default on, today's behaviour) — a request
      naming ``target_material`` still gets the material card's ``mat_*`` /
      ``thermo_*`` values injected, and they are recorded in
      ``legacy_physical_inputs``, never in ``variables``. Off: nothing is
      injected and ``target_material`` itself is stripped from the engine.
    * ``RENDER_GENERATOR_OUTPUT`` — off: the engine params are unchanged but
      no generator inputs travel with the payload, so no sidecar is written.
    """
    raw = raw_params if isinstance(raw_params, dict) else {}
    resolved = resolve_effective_parameters(
        manifest, mode_id, raw, inject_full=bool(Config.RENDER_INJECT_FULL_PARAMS), validate=validate,
    )
    params = resolved.engine_params
    physical = dict(resolved.legacy_physical_inputs)

    target_material = raw.get("target_material")
    if Config.RENDER_MATERIAL_INJECTION:
        if target_material:
            before = set(params)
            material_injector(params, target_material)
            physical.update({key: params[key] for key in set(params) - before})
            physical["target_material"] = _scalar(target_material)
    else:
        params.pop("target_material", None)
        physical.pop("target_material", None)

    if not Config.RENDER_GENERATOR_OUTPUT:
        return params, None

    inputs = {
        "variables": resolved.variables,
        "variables_sha256": variables_sha256(resolved.variables),
        "complete": all(v["source"] != "source_default" for v in resolved.variables),
    }
    physical = {key: _scalar(value) for key, value in physical.items()}
    if physical:
        inputs["legacy_physical_inputs"] = physical
    return params, inputs


def output_summary(generator_inputs: dict | None) -> dict | None:
    """The envelope's top-level ``generator_output`` object."""
    if not generator_inputs:
        return None
    return {
        "format_version": FORMAT_VERSION,
        "complete": bool(generator_inputs.get("complete")),
        "variables_sha256": generator_inputs.get("variables_sha256"),
    }


# ──────────────────────────────────────────────
# Document (GOC-1 §2)
# ──────────────────────────────────────────────

def _commons_root() -> Path | None:
    try:
        return Path(Config.PROJECTS_DIR).resolve()
    except OSError:
        return None


@lru_cache(maxsize=1)
def commons_sha() -> str | None:
    """The solid commons commit this process serves, when it can be known.

    ``COMMONS_SHA`` (a build argument) wins. A checkout with the submodule's
    git metadata answers for itself; a container without either records only
    the repository.
    """
    configured = (Config.COMMONS_SHA or "").strip().lower()
    if configured:
        return configured if _COMMONS_SHA_RE.match(configured) else None
    root = _commons_root()
    if root is None or not (root / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        ).stdout.strip().lower()
    except (OSError, subprocess.SubprocessError):
        return None
    return out if _COMMONS_SHA_RE.match(out) else None


def _commons_block(cartridge_dir: Path) -> dict | None:
    """``generator.commons``, only for a cartridge served from the public commons."""
    root = _commons_root()
    try:
        if root is None or root not in cartridge_dir.resolve().parents:
            return None
    except OSError:
        return None
    block = {"repo": COMMONS_REPO}
    sha = commons_sha()
    if sha:
        block["sha"] = sha
    return block


def engine_kernel(engine: str) -> str | None:
    """Human-readable kernel identity; provenance only, never part of an id."""
    try:
        if engine == "openscad":
            from services.engine.openscad import backend_cache_signature
            return f"openscad {backend_cache_signature()}"[:200]
        if engine in ("cadquery", "graph"):
            return f"cadquery {metadata.version('cadquery')}"
        if engine == "implicit":
            return f"yantra4d-implicit numpy {metadata.version('numpy')}"
    except Exception:
        logger.debug("Kernel identity unavailable for %s", engine, exc_info=True)
    return None


def geometry_entry(path: str, name: str, role: str) -> dict:
    sha, size = file_digest(path)
    return {"path": name, "media_type": media_type_for(name), "sha256": sha,
            "bytes": size, "units": "mm", "role": role}


def build_generator_output(manifest, generator_inputs: dict, *, mode: str, part: str | None,
                           engine: str, entry_path: str | None, geometry: list[dict],
                           platform_build: str | None = None, kernel: str | None = None) -> dict:
    """Assemble one GOC-1 document. ``created_at`` is omitted: the surface is cached."""
    cartridge_dir = Path(manifest.project_dir)
    tree = tree_sha256(cartridge_dir)
    variables = generator_inputs["variables"]
    var_sha = variables_sha256(variables)
    cartridge = manifest.slug

    source: dict = {"tree_sha256": tree, "tree_algorithm": TREE_ALGORITHM}
    if entry_path and os.path.isfile(entry_path):
        try:
            source["entry"] = Path(entry_path).resolve().relative_to(cartridge_dir.resolve()).as_posix()
        except ValueError:
            source["entry"] = Path(entry_path).name
        source["entry_sha256"] = file_digest(entry_path)[0]

    generator: dict = {"platform": PLATFORM, "cartridge": cartridge, "mode": mode,
                       "part": part, "engine": engine, "source": source}
    if platform_build:
        generator["platform_build"] = platform_build[:128]
    version = manifest.project.get("version")
    if isinstance(version, str) and version:
        generator["cartridge_version"] = version[:64]
    commons = _commons_block(cartridge_dir)
    if commons:
        generator["commons"] = commons
    if kernel:
        generator["kernel"] = kernel[:200]

    doc = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "kind": "solid",
        "generator": generator,
        "variables": variables,
        "variables_sha256": var_sha,
        "complete": all(v["source"] != "source_default" for v in variables),
        "geometry": geometry,
        "instance_id": instance_id(cartridge, mode, part, tree, var_sha),
    }
    legacy = generator_inputs.get("legacy_physical_inputs")
    if legacy:
        doc["legacy_physical_inputs"] = legacy
    if not _CARTRIDGE_RE.match(cartridge):
        raise ValueError(f"Cartridge slug {cartridge!r} is not a GOC-1 cartridge id")
    return doc


# ──────────────────────────────────────────────
# Worker and cache seams
# ──────────────────────────────────────────────

#: Part fields every generated part carries, on both cache paths.
PART_FIELDS = ("sha256", "media_type", "instance_id", "variables_url")
#: The same, as stored in a render-cache entry (the URL is rebuilt from the key).
CACHE_FIELDS = ("sha256", "media_type", "instance_id", "variables_key")


@dataclass
class PartOutput:
    """A written sidecar, waiting to be published with the geometry it describes."""

    sidecar_path: str
    sha256: str
    media_type: str
    instance_id: str
    summary: dict = field(default_factory=dict)

    def cache_fields(self, published: dict[str, str]) -> dict:
        return {"sha256": self.sha256, "media_type": self.media_type,
                "instance_id": self.instance_id, "variables_key": published[self.sidecar_path]}

    def part_fields(self, published: dict[str, str]) -> dict:
        return part_fields_from_cache(self.cache_fields(published))


def prepare_part_output(task: dict, manifest, serve_path: str, viewer_path: str | None) -> PartOutput | None:
    """Digest a finished part and write its sidecar next to the served file.

    Must run before the files are published: under an object store the local
    copies are scratch and are removed once stored. Returns ``None`` when the
    payload carries no generator inputs (flag off, or a task queued by an API
    that predates GOC-1). Any failure is logged at ERROR and also yields
    ``None``: the geometry is still good, the part is served without the
    GOC-1 fields, and its cache entry is a miss next time (see
    :func:`cache_entry_usable`), so it is regenerated rather than served
    without provenance for a day.
    """
    payload = task.get("payload") or {}
    generator_inputs = payload.get("generator_inputs")
    if not generator_inputs or not Config.RENDER_GENERATOR_OUTPUT:
        return None
    try:
        serve_name = os.path.basename(serve_path)
        geometry = [geometry_entry(serve_path, serve_name, "primary")]
        if viewer_path and os.path.isfile(viewer_path) and viewer_path != serve_path:
            geometry.append(geometry_entry(viewer_path, os.path.basename(viewer_path), "viewer"))
        engine = task.get("engine") or "openscad"
        doc = build_generator_output(
            manifest, generator_inputs,
            mode=str(payload.get("mode") or task.get("mode") or ""), part=task.get("part"),
            engine=engine, entry_path=task.get("scad_path"), geometry=geometry,
            platform_build=payload.get("render_revision") or None, kernel=engine_kernel(engine),
        )
        sidecar_path = os.path.join(os.path.dirname(serve_path), sidecar_name(serve_name))
        with open(sidecar_path, "wb") as fh:
            fh.write(canonical_json(doc))
        return PartOutput(sidecar_path, geometry[0]["sha256"], geometry[0]["media_type"],
                          doc["instance_id"], output_summary(generator_inputs) or {})
    except Exception:
        logger.exception("GOC-1 sidecar for %s part %s could not be written; serving the part without it",
                         payload.get("project_slug"), task.get("part"))
        return None


def part_fields_from_cache(entry: dict | None) -> dict:
    """``parts[i]`` GOC-1 fields from a render-cache entry ({} when it has none)."""
    if not isinstance(entry, dict) or not entry.get("variables_key"):
        return {}
    return {"sha256": entry.get("sha256"), "media_type": entry.get("media_type"),
            "instance_id": entry.get("instance_id"),
            "variables_url": f"/static/{entry['variables_key']}"}


def cache_entry_usable(entry: dict | None, payload: dict) -> bool:
    """Whether a cache hit can answer a render that must carry GOC-1 fields.

    An entry written while generator output was off (or by a failed sidecar
    write) has no sidecar. Serving it would return a part without the fields
    the MISS path returns, so it counts as a miss and the part is rendered
    again, once.
    """
    if not entry:
        return False
    if not payload.get("generator_inputs") or not Config.RENDER_GENERATOR_OUTPUT:
        return True
    return all(entry.get(key) for key in CACHE_FIELDS) and bool(_SHA256_RE.match(str(entry.get("sha256"))))
