"""
Render source resolution: the ONE place that decides what a mode renders.

A mode names its script in ``scad_file`` (``.scad``, ``.py``/``.cq`` or a
``.graph.json``) and may also declare a node-graph twin in ``graph_file``. Which
of the two is the render source depends on who owns the cartridge:

* **User cartridges** — ``project.meta.json`` ``source.type`` is ``fork`` or
  ``github``. When the mode declares ``graph_file``, the graph is the render
  source: it is the file the Studio graph editor saves, and in a fork it is the
  only editable source the mode has (the editor accepts ``.scad`` and
  ``.graph.json`` only). It renders with the ``graph`` engine, which transpiles
  it to a CadQuery program and runs that through the render worker's sandboxed
  CadQuery runner, exactly like any other graph mode.
* **Curated cartridges** — the commons and the private cartridges, i.e. anything
  without a user source type. The script stays the render source; a graph twin
  is published alongside it and rendered only once its parity is established.

Every render path (``/api/render``, ``/api/render-stream``, the git HEAD
preview, animation frames) asks this module, so no path can render a different
source than another for the same mode.

A user cartridge that declares a ``graph_file`` it cannot render — not a plain
relative ``*.graph.json`` path, outside the cartridge, or missing — is an error
the caller reports. It never falls back to the script: that would render the
cartridge the user did not edit and look like success.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

#: ``project.meta.json`` ``source.type`` values that make a cartridge user-owned.
USER_SOURCE_TYPES = frozenset({"fork", "github"})

GRAPH_SUFFIX = ".graph.json"

#: ``RenderSource.kind``: the mode's ``scad_file`` …
KIND_SCRIPT = "script"
#: … or its declared ``graph_file``.
KIND_GRAPH = "graph"

# A plain relative path: path segments of a closed character set, separated by
# "/". No absolute paths, no "..", no whitespace or control characters.
_PLAIN_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]*$")


class RenderSourceError(ValueError):
    """The mode's render source cannot be resolved; the message is user-facing."""


@dataclass(frozen=True)
class RenderSource:
    """What one mode renders: the manifest file name, its path and the engine."""

    filename: str
    path: Path
    engine: str
    kind: str

    @property
    def is_graph(self) -> bool:
        return self.kind == KIND_GRAPH


def cartridge_source_type(project_dir: Path) -> str | None:
    """``source.type`` from ``project.meta.json``, or None when there is none.

    The same reading the editor's write guard applies: a missing, unreadable or
    malformed file means "not a user cartridge".
    """
    meta_path = Path(project_dir) / "project.meta.json"
    if not meta_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    source = meta.get("source") if isinstance(meta, dict) else None
    kind = source.get("type") if isinstance(source, dict) else None
    return kind if isinstance(kind, str) else None


def is_user_cartridge(project_dir: Path) -> bool:
    return cartridge_source_type(project_dir) in USER_SOURCE_TYPES


def _mode(manifest, mode_id: str) -> dict | None:
    return next((m for m in manifest.modes if isinstance(m, dict) and m.get("id") == mode_id), None)


def _is_plain_graph_name(name) -> bool:
    if not isinstance(name, str) or not name.endswith(GRAPH_SUFFIX) or len(name) > 255:
        return False
    return all(_PLAIN_SEGMENT_RE.match(segment) for segment in name.split("/"))


def _graph_path(project_dir: Path, name) -> Path:
    """The declared graph file, resolved inside the cartridge, or RenderSourceError."""
    if not _is_plain_graph_name(name):
        raise RenderSourceError(
            f"Invalid graph_file {name!r}: it must be a relative path to a {GRAPH_SUFFIX} "
            "file inside the project"
        )
    root = Path(project_dir).resolve()
    path = (root / name).resolve()
    if not path.is_relative_to(root):
        raise RenderSourceError(f"Invalid graph_file {name!r}: it must be inside the project")
    if not path.is_file():
        raise RenderSourceError(f"graph_file {name!r} does not exist in this project")
    return path


def render_source_for_mode(manifest, mode_id: str) -> RenderSource | None:
    """The render source of ``mode_id``, or None when the manifest has no such mode.

    Raises RenderSourceError when a user cartridge declares a graph it cannot
    render (see the module docstring: no silent fallback to the script).
    """
    mode = _mode(manifest, mode_id)
    if mode is None:
        return None
    project_dir = getattr(manifest, "project_dir", None)

    graph_name = mode.get("graph_file")
    if graph_name is not None and project_dir is not None and is_user_cartridge(Path(project_dir)):
        path = _graph_path(Path(project_dir), graph_name)
        return RenderSource(filename=graph_name, path=path, engine="graph", kind=KIND_GRAPH)

    filename = mode["scad_file"]
    return RenderSource(
        filename=filename,
        path=Path(project_dir) / filename if project_dir is not None else Path(filename),
        engine=manifest.mode_engine(mode_id),
        kind=KIND_SCRIPT,
    )


def render_engine_for_mode(manifest, mode_id: str | None) -> str:
    """The engine ``mode_id`` renders with; the manifest's own answer for an unknown mode.

    Never raises: an unrenderable graph is reported by the source lookup that
    precedes every render, not by this engine lookup.
    """
    if mode_id:
        try:
            source = render_source_for_mode(manifest, mode_id)
        except RenderSourceError:
            source = None
        if source is not None:
            return source.engine
    return manifest.mode_engine(mode_id)


def source_content_hash(source_path, manifest=None) -> str | None:
    """Cache identity of a render source's content.

    The file's bytes, and for a graph document also the manifest's binding map:
    a graph's output depends on which manifest parameters drive which node
    params, so a binding-only edit is a new render too. None when the file
    cannot be read (the render then fails on its own, visibly).
    """
    try:
        raw = Path(source_path).read_bytes()
    except OSError:
        return None
    # MD5, as compute_scad_hash: a script source keeps its existing cache identity.
    digest = hashlib.md5(raw)
    if str(source_path).endswith(GRAPH_SUFFIX) and manifest is not None:
        bindings = {
            str(p.get("id")): p.get("binding")
            for p in (getattr(manifest, "parameters", None) or [])
            if isinstance(p, dict) and p.get("binding")
        }
        if bindings:
            digest.update(b"\0bindings\0")
            digest.update(json.dumps(bindings, sort_keys=True).encode())
    return digest.hexdigest()


def graph_sources(project_dir: Path, manifest_data: dict) -> list[Path]:
    """Every graph document the manifest's modes render or may render.

    Graph-engine modes (``scad_file`` ending ``.graph.json``) and, for a user
    cartridge, each mode's declared ``graph_file``. Path-guarded: a name that
    resolves outside the cartridge is skipped, and so is a ``graph_file`` that
    is not a plain path (the render reports that one).
    """
    root = Path(project_dir).resolve()
    user = is_user_cartridge(project_dir)
    sources: list[Path] = []

    def _add(name) -> None:
        path = (root / name).resolve()
        if path.is_relative_to(root) and path not in sources:
            sources.append(path)

    for mode in manifest_data.get("modes") or []:
        if not isinstance(mode, dict):
            continue
        primary = mode.get("scad_file")
        if isinstance(primary, str) and primary.endswith(GRAPH_SUFFIX):
            _add(primary)
        if user and _is_plain_graph_name(mode.get("graph_file")):
            _add(mode["graph_file"])
    return sources


def user_source_revision(manifest) -> str | None:
    """A digest of a user cartridge's render sources, or None for a curated one.

    Clients key persistent render caches on the API's render revision. A
    curated cartridge's sources change only with a release, which already moves
    that revision; a user cartridge's sources change whenever its owner saves,
    so the manifest route appends this digest for them (see
    routes/projects/projects.py) and a saved edit can never be answered from a
    cache entry made before it.
    """
    project_dir = getattr(manifest, "project_dir", None)
    if project_dir is None or not is_user_cartridge(Path(project_dir)):
        return None
    digest = hashlib.sha256()
    for mode in manifest.modes:
        mode_id = mode.get("id") if isinstance(mode, dict) else None
        if not mode_id:
            continue
        try:
            source = render_source_for_mode(manifest, mode_id)
        except RenderSourceError as exc:
            entry = f"{mode_id}:error:{exc}"
        else:
            content = source_content_hash(source.path, manifest) if source else None
            entry = f"{mode_id}:{source.filename if source else ''}:{content}"
        digest.update(entry.encode())
        digest.update(b"\n")
    return digest.hexdigest()[:16]
