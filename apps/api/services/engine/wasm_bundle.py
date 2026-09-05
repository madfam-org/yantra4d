"""
WASM bundle builder — everything a browser render of an OpenSCAD cartridge needs.

The Studio's OpenSCAD WASM worker runs against an in-memory Emscripten
filesystem: nothing is on disk, nothing is fetchable, and OpenSCAD's own
`include <…>` resolution runs entirely inside that virtual FS. Until now the
worker fetched `${origin}/scad/<file>` — a path nothing serves — and mounted no
libraries and no fonts, so any cartridge that pulled in BOSL2 or called `text()`
could never render in the browser. That, far more than geometry cost, is why
~490 manifests carry `force_backend: true`.

This module resolves a cartridge's whole source closure the way OpenSCAD would,
then hands it over in one response so the worker can populate its FS in a single
write pass.

Virtual filesystem layout
-------------------------
Every path in a bundle is POSIX and relative to a virtual root that mirrors the
server's own directory shape::

    /projects/<slug>/…      <cartridge root>/<slug>     (the cartridge)
    /libs/…                 Config.LIBS_DIR             (BOSL2, dotSCAD, …)
    /fonts/…                Config.FONTS_DIR            (shared typefaces)

Mirroring the server is the whole point: a cartridge that says
``include <../../libs/BOSL2/std.scad>`` from ``/projects/rugged-box/rugged_core.scad``
resolves to ``/libs/BOSL2/std.scad`` in the worker exactly as it does on disk,
with no rewriting of anyone's source. For includes that resolve through
OPENSCADPATH rather than relatively, the worker sets the search path to the
virtual equivalent of what the server composes — see :data:`VIRTUAL_OPENSCADPATH`.

Confinement
-----------
A resolved file is only ever admitted when it lands inside the cartridge's own
directory or inside ``Config.LIBS_DIR``. Everything else — another cartridge,
``/etc/passwd`` reached by a stack of ``../``, a dangling symlink — is dropped
and recorded in ``unresolved`` rather than silently omitted, because a missing
include changes what OpenSCAD renders and the Studio needs to know the browser
copy is not the same model the server would build.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from config import Config
from services.core.scad_analyzer import extract_dependencies
from utils.route_helpers import safe_join_path

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Virtual filesystem constants
# ──────────────────────────────────────────────

#: Virtual root of the cartridge tree.
PROJECTS_ROOT = "projects"

#: Virtual root of the shared OpenSCAD libraries.
LIBS_ROOT = "libs"

#: Virtual root of the shared font directory.
FONTS_ROOT = "fonts"

#: The search path the worker must set for OPENSCADPATH-style includes — the
#: virtual mirror of what ``config.py`` composes for the native binary
#: (LIBS_DIR, dotSCAD/src, PROJECTS_DIR). Constant by construction: the virtual
#: layout does not depend on where those directories happen to live on a host.
VIRTUAL_OPENSCADPATH = f"/{LIBS_ROOT}:/{LIBS_ROOT}/dotSCAD/src:/{PROJECTS_ROOT}"

#: Name of the fontconfig file the worker writes next to the fonts.
FONTS_CONF_NAME = "fonts.conf"

#: The `engine` a bundle reports. Constant by construction: a bundle is only
#: ever issued for OpenSCAD, and a dual-engine cartridge gets one covering the
#: modes it renders with OpenSCAD (`entry_files` says which). CadQuery, graph
#: and implicit have no browser kernel and are refused before this point.
BUNDLE_ENGINE = "openscad"

# ──────────────────────────────────────────────
# Limits
# ──────────────────────────────────────────────
#
# A bundle is a single JSON response the browser holds in memory, so it needs a
# ceiling. These are generous against reality — the largest cartridge in the
# commons pulls the whole of BOSL2 and lands around 3 MiB over ~60 files — and
# are here to stop a pathological include graph, not to ration normal work.

MAX_BUNDLE_BYTES = 24 * 1024 * 1024
MAX_BUNDLE_FILES = 600

#: Font file extensions the worker's fontconfig build can read.
FONT_SUFFIXES = (".ttf", ".otf")

# ──────────────────────────────────────────────
# Feature detection
# ──────────────────────────────────────────────
#
# Honest and small: each entry means "this build of OpenSCAD-WASM cannot do what
# the source asks", and the Studio reads a non-empty list as "server required".
# Anything merely *slow* in the browser belongs in the manifest's
# `render.browser_max_estimate_seconds`, not here.

#: `import(…)` pulls an external STL/DXF/SVG/AMF that is not part of the source
#: closure and is not served to the worker.
UNSUPPORTED_IMPORT = "import"

#: `surface(…)` reads a heightmap file, same problem as `import`.
UNSUPPORTED_SURFACE = "surface"

#: At least one `include`/`use` could not be resolved, so the browser would
#: render a different model than the server does — see ``unresolved``.
UNSUPPORTED_MISSING_INCLUDE = "unresolved_includes"

_IMPORT_RE = re.compile(r"(?<![A-Za-z0-9_$])import\s*\(")
_SURFACE_RE = re.compile(r"(?<![A-Za-z0-9_$])surface\s*\(")
_TEXT_RE = re.compile(r"(?<![A-Za-z0-9_$])text\s*\(")


class BundleTooLarge(Exception):
    """The source closure exceeded :data:`MAX_BUNDLE_BYTES` / :data:`MAX_BUNDLE_FILES`."""

    def __init__(self, files: int, total_bytes: int):
        super().__init__(
            f"bundle exceeds limits: {files} files, {total_bytes} bytes "
            f"(max {MAX_BUNDLE_FILES} files, {MAX_BUNDLE_BYTES} bytes)"
        )
        self.files = files
        self.bytes = total_bytes
        self.max_files = MAX_BUNDLE_FILES
        self.max_bytes = MAX_BUNDLE_BYTES


@dataclass
class Bundle:
    """A resolved bundle, ready to serialise."""

    slug: str
    engine: str
    entry_files: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    fonts: dict[str, str] = field(default_factory=dict)
    unsupported: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    bytes: int = 0
    etag: str = ""

    #: Real paths every entry came from, with the mtime they were read at. Not
    #: serialised — it is what the in-process cache re-checks.
    sources: dict[str, int] = field(default_factory=dict, repr=False)

    def as_json(self) -> dict:
        return {
            "slug": self.slug,
            "engine": self.engine,
            "entry_files": self.entry_files,
            "files": self.files,
            "fonts": self.fonts,
            "unsupported": self.unsupported,
            "unresolved": self.unresolved,
            "bytes": self.bytes,
            "etag": self.etag,
        }


# ──────────────────────────────────────────────
# Path resolution
# ──────────────────────────────────────────────


def openscadpath_entries() -> list[Path]:
    """The OPENSCADPATH the server composes, as directories, in search order."""
    raw = Config.OPENSCADPATH or ""
    entries: list[Path] = []
    for chunk in raw.split(os.pathsep):
        chunk = chunk.strip()
        if chunk:
            entries.append(Path(chunk))
    return entries


def _roots(project_dir: Path) -> list[tuple[str, Path]]:
    """``(virtual prefix, real root)`` pairs a resolved file may live under.

    Order matters only for reporting: a cartridge nested inside LIBS_DIR would
    otherwise be announced as a library.
    """
    return [
        (f"{PROJECTS_ROOT}/{project_dir.name}", project_dir),
        (LIBS_ROOT, Config.LIBS_DIR),
    ]


def confine(real: Path, roots: list[tuple[str, Path]]) -> tuple[str, Path] | None:
    """Map a candidate path to its virtual path, or None if it escapes every root.

    ``safe_join_path`` is the guard: it resolves the join and refuses anything
    that lands outside the root, so traversal, an absolute path and a symlink
    pointing out of the tree all fail the same way.

    The *directory* a candidate sits in is resolved before the relative path is
    computed, so a symlink anywhere above the cartridge (``/tmp`` on more than
    one platform) cannot turn a perfectly ordinary file into a virtual path full
    of ``..``. The file's own name is left alone: a symlink *inside* the tree
    keeps the name its include site actually writes, which is the name the
    worker will look for.
    """
    normalized = Path(os.path.realpath(real.parent)) / real.name
    for prefix, root in roots:
        try:
            rel = os.path.relpath(normalized, os.path.realpath(root))
        except ValueError:  # different drive on Windows
            continue
        if rel == os.pardir or rel.startswith(os.pardir + os.sep) or os.path.isabs(rel):
            continue
        safe = safe_join_path(str(root), rel)
        if safe is None:
            continue
        return f"{prefix}/{PurePosixPath(rel.replace(os.sep, '/'))}", safe
    return None


def _candidates(target: str, including_dir: Path, search_path: list[Path]) -> list[Path]:
    """Every place OpenSCAD would look for ``target``, in its own order.

    Relative to the including file's directory first, then each OPENSCADPATH
    entry. An absolute target is taken at face value and then has to survive
    confinement like everything else.
    """
    path = Path(target)
    if path.is_absolute():
        return [path]
    return [including_dir / target] + [entry / target for entry in search_path]


# ──────────────────────────────────────────────
# Traversal
# ──────────────────────────────────────────────


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.debug("wasm_bundle: unreadable source %s (%s)", path, e)
        return None


def resolve_sources(
    entry_paths: list[Path],
    project_dir: Path,
    search_path: list[Path] | None = None,
) -> tuple[dict[str, str], list[str], dict[str, int]]:
    """Resolve the full ``include``/``use`` closure of ``entry_paths``.

    Returns ``(files, unresolved, sources)`` where *files* maps virtual path to
    text, *unresolved* lists the include targets that could not be resolved (as
    ``"<including virtual path>: <target>"``, so an operator can find them), and
    *sources* maps virtual path to the ``st_mtime_ns`` the file was read at.

    A visited set keyed on the resolved real path makes cycles terminate and
    keeps the diamond dependencies BOSL2 is full of from being read twice.

    Raises :class:`BundleTooLarge` as soon as the running totals cross a limit,
    so a runaway graph is abandoned rather than fully walked.
    """
    if search_path is None:
        search_path = openscadpath_entries()
    roots = _roots(project_dir)

    files: dict[str, str] = {}
    sources: dict[str, int] = {}
    unresolved: list[str] = []
    seen: set[Path] = set()
    total_bytes = 0

    # (real path, virtual path) — a queue rather than recursion so a deep or
    # cyclic graph cannot blow the Python stack.
    queue: list[tuple[Path, str]] = []
    for entry in entry_paths:
        placed = confine(entry, roots)
        if placed is None:
            unresolved.append(f"{PROJECTS_ROOT}/{project_dir.name}: {entry.name}")
            continue
        queue.append((placed[1], placed[0]))

    while queue:
        real, virtual = queue.pop(0)
        if real in seen:
            continue
        seen.add(real)

        # Size first, content second: a single pathological file must trip the
        # cap before it is pulled into memory, not after.
        try:
            stat = real.stat()
        except OSError:
            unresolved.append(virtual)
            continue
        if total_bytes + stat.st_size > MAX_BUNDLE_BYTES:
            raise BundleTooLarge(len(files) + 1, total_bytes + stat.st_size)

        text = _read_text(real)
        if text is None:
            unresolved.append(virtual)
            continue

        files[virtual] = text
        sources[virtual] = stat.st_mtime_ns
        total_bytes += len(text.encode("utf-8"))
        if len(files) > MAX_BUNDLE_FILES or total_bytes > MAX_BUNDLE_BYTES:
            raise BundleTooLarge(len(files), total_bytes)

        for target in extract_dependencies(text):
            resolved = _resolve_one(target, real.parent, search_path, roots)
            if resolved is None:
                unresolved.append(f"{virtual}: {target}")
                continue
            child_virtual, child_real = resolved
            if child_real not in seen:
                queue.append((child_real, child_virtual))

    return files, unresolved, sources


def _resolve_one(
    target: str,
    including_dir: Path,
    search_path: list[Path],
    roots: list[tuple[str, Path]],
) -> tuple[str, Path] | None:
    """First candidate for ``target`` that exists *and* stays inside a root."""
    for candidate in _candidates(target, including_dir, search_path):
        placed = confine(candidate, roots)
        if placed is None:
            continue
        virtual, real = placed
        if real.is_file():
            return virtual, real
    return None


# ──────────────────────────────────────────────
# Fonts
# ──────────────────────────────────────────────


def _font_files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in FONT_SUFFIXES
    )


def uses_text(files: dict[str, str]) -> bool:
    """Whether any resolved source calls ``text(…)`` and so needs a typeface."""
    return any(_TEXT_RE.search(text) for text in files.values())


def collect_fonts(project_dir: Path, files: dict[str, str]) -> tuple[dict[str, str], int, dict[str, int]]:
    """Base64 font payloads plus a ``fonts.conf`` pointing at where they land.

    The cartridge's own ``fonts/`` always travels with it — it is part of the
    cartridge, and a cartridge that ships a typeface means to use it. The shared
    directory only travels when some source actually calls ``text(``, because it
    is the single largest thing a bundle can carry for nothing.

    Returns ``(fonts, raw_bytes, sources)``: *raw_bytes* is the pre-base64 size
    that counts against the bundle limit, and *sources* carries mtimes for the
    cache in the same shape as the source map.
    """
    fonts: dict[str, str] = {}
    sources: dict[str, int] = {}
    raw_bytes = 0
    font_dirs: list[str] = []

    def _add(directory: Path, virtual_dir: str) -> None:
        nonlocal raw_bytes
        found = _font_files(directory)
        if not found:
            return
        font_dirs.append(f"/{virtual_dir}")
        for path in found:
            try:
                blob = path.read_bytes()
            except OSError as e:
                logger.debug("wasm_bundle: unreadable font %s (%s)", path, e)
                continue
            virtual = f"{virtual_dir}/{path.name}"
            fonts[virtual] = base64.b64encode(blob).decode("ascii")
            raw_bytes += len(blob)
            try:
                sources[virtual] = path.stat().st_mtime_ns
            except OSError:
                sources[virtual] = 0

    _add(project_dir / "fonts", f"{PROJECTS_ROOT}/{project_dir.name}/fonts")
    if uses_text(files) and Config.FONTS_DIR:
        _add(Path(Config.FONTS_DIR), FONTS_ROOT)

    if fonts:
        from services.engine.openscad import fontconfig_xml
        conf = fontconfig_xml(font_dirs)
        fonts[FONTS_CONF_NAME] = conf
        # `bytes` means "what the worker writes into its FS", and the worker
        # writes this file too.
        raw_bytes += len(conf.encode("utf-8"))

    return fonts, raw_bytes, sources


# ──────────────────────────────────────────────
# Unsupported features
# ──────────────────────────────────────────────


def strip_comments(text: str) -> str:
    """SCAD source with comments removed, string literals left intact.

    Feature detection runs on this so a commented-out ``import()`` or a note
    about ``surface()`` in a header block does not push a perfectly renderable
    cartridge onto the server.
    """
    out: list[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            j = i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"':
                    j += 1
                    break
                j += 1
            out.append(text[i:j])
            i = j
        elif text.startswith("//", i):
            nl = text.find("\n", i)
            if nl == -1:
                break
            out.append("\n")
            i = nl + 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            out.append(" ")
            i = n if end == -1 else end + 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def detect_unsupported(files: dict[str, str], unresolved: list[str]) -> list[str]:
    """Features of this source closure that the WASM build cannot honour."""
    found: list[str] = []
    stripped = [strip_comments(text) for text in files.values()]
    if any(_IMPORT_RE.search(text) for text in stripped):
        found.append(UNSUPPORTED_IMPORT)
    if any(_SURFACE_RE.search(text) for text in stripped):
        found.append(UNSUPPORTED_SURFACE)
    if unresolved:
        found.append(UNSUPPORTED_MISSING_INCLUDE)
    return found


# ──────────────────────────────────────────────
# Bundle assembly
# ──────────────────────────────────────────────


def compute_etag(bundle: Bundle) -> str:
    """SHA-256 over exactly the content the caller receives.

    Every field that can change what the worker renders feeds the hash — the
    sources, the fonts, the entry list, and both honesty lists — so a cartridge
    edit, a library bump, an added font or a newly-broken include all move the
    ETag. Nothing else does: two servers with the same content agree.
    """
    digest = hashlib.sha256()
    digest.update(bundle.slug.encode("utf-8"))
    digest.update(b"\0")
    digest.update(bundle.engine.encode("utf-8"))
    for name in bundle.entry_files:
        digest.update(b"\0entry\0")
        digest.update(name.encode("utf-8"))
    for path in sorted(bundle.files):
        digest.update(b"\0file\0")
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bundle.files[path].encode("utf-8"))
    for path in sorted(bundle.fonts):
        digest.update(b"\0font\0")
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(bundle.fonts[path].encode("utf-8"))
    for item in bundle.unsupported:
        digest.update(b"\0unsupported\0")
        digest.update(item.encode("utf-8"))
    for item in bundle.unresolved:
        digest.update(b"\0unresolved\0")
        digest.update(item.encode("utf-8"))
    return digest.hexdigest()


def openscad_entry_files(manifest) -> list[str]:
    """``scad_file`` of every mode this cartridge renders with OpenSCAD.

    A dual-engine cartridge keeps its OpenSCAD modes: the browser can render
    those, and the modes it cannot are the server's job. Deduplicated with order
    preserved — several modes commonly share one file.
    """
    allowed = manifest.get_allowed_files()
    entries: list[str] = []
    for mode in manifest.modes:
        name = mode.get("scad_file")
        if not name or name not in allowed or name in entries:
            continue
        if manifest.mode_engine(mode.get("id")) != "openscad":
            continue
        entries.append(name)
    return entries


def build_bundle(manifest, slug: str) -> Bundle:
    """Resolve, read and hash everything a browser render of ``slug`` needs."""
    project_dir = Path(manifest.project_dir)
    entry_names = openscad_entry_files(manifest)
    allowed = manifest.get_allowed_files()

    files, unresolved, sources = resolve_sources(
        [Path(allowed[name]) for name in entry_names], project_dir,
    )
    fonts, font_bytes, font_sources = collect_fonts(project_dir, files)

    total_bytes = sum(len(text.encode("utf-8")) for text in files.values()) + font_bytes
    if len(files) + len(fonts) > MAX_BUNDLE_FILES or total_bytes > MAX_BUNDLE_BYTES:
        raise BundleTooLarge(len(files) + len(fonts), total_bytes)

    prefix = f"{PROJECTS_ROOT}/{project_dir.name}/"
    bundle = Bundle(
        slug=slug,
        engine=BUNDLE_ENGINE,
        # Entry files stay bare names, the way the manifest writes them: the
        # worker chdirs into the cartridge, and every mode's file is by
        # definition at its root.
        entry_files=[name for name in entry_names if prefix + name in files],
        files=files,
        fonts=fonts,
        unsupported=detect_unsupported(files, unresolved),
        unresolved=unresolved,
        bytes=total_bytes,
        sources={**sources, **font_sources},
    )
    bundle.etag = compute_etag(bundle)
    return bundle


# ──────────────────────────────────────────────
# In-process cache
# ──────────────────────────────────────────────
#
# Resolving BOSL2 is ~60 file reads, which is cheap once and wasteful on every
# page load of a popular cartridge. The key is the manifest's mtime plus the
# newest mtime across everything the last build touched, so editing any resolved
# source — or the manifest that decides which sources those are — rebuilds. A
# vanished file rebuilds too, because its stat fails.

_MAX_CACHE_ENTRIES = 64
_cache: dict[str, tuple[tuple, Bundle]] = {}


def _cache_key(manifest, bundle: Bundle | None) -> tuple:
    """``(manifest mtime, file count, newest mtime)`` of the last resolved set."""
    try:
        manifest_mtime = (Path(manifest.project_dir) / "project.json").stat().st_mtime_ns
    except OSError:
        manifest_mtime = 0
    if bundle is None:
        return (manifest_mtime, -1, -1)

    newest = 0
    project_dir = Path(manifest.project_dir)
    roots = _roots(project_dir)
    for virtual in bundle.sources:
        real = _real_path(virtual, roots)
        if real is None:
            return (manifest_mtime, -1, -1)
        try:
            newest = max(newest, real.stat().st_mtime_ns)
        except OSError:
            return (manifest_mtime, -1, -1)
    return (manifest_mtime, len(bundle.sources), newest)


def _real_path(virtual: str, roots: list[tuple[str, Path]]) -> Path | None:
    """Invert a virtual path back to disk, for the cache's freshness stat."""
    for prefix, root in roots:
        if virtual == prefix or virtual.startswith(prefix + "/"):
            return safe_join_path(str(root), virtual[len(prefix):].lstrip("/"))
    if virtual.startswith(FONTS_ROOT + "/") and Config.FONTS_DIR:
        return safe_join_path(str(Config.FONTS_DIR), virtual[len(FONTS_ROOT) + 1:])
    return None


def get_bundle(manifest, slug: str) -> Bundle:
    """Cached :func:`build_bundle`, rebuilt whenever any resolved file changed."""
    cached = _cache.get(slug)
    if cached is not None:
        key, bundle = cached
        if key == _cache_key(manifest, bundle):
            return bundle

    bundle = build_bundle(manifest, slug)
    if len(_cache) >= _MAX_CACHE_ENTRIES and slug not in _cache:
        _cache.pop(next(iter(_cache)))
    _cache[slug] = (_cache_key(manifest, bundle), bundle)
    return bundle


def invalidate_cache(slug: str | None = None) -> None:
    """Drop one cartridge's cached bundle, or all of them."""
    if slug is None:
        _cache.clear()
    else:
        _cache.pop(slug, None)
