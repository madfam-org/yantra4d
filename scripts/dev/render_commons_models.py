#!/usr/bin/env python3
"""Render the raw GLBs the landing's model pipeline optimizes.

Drives a LOCAL Yantra4D API (``python app.py`` + Redis + the render worker — the
API never renders inline) through ``POST /api/render`` and writes one
uncompressed GLB per public cartridge, plus one per keyframe of every manifest
that declares ``animations``, into ``apps/landing/public/models/raw/``::

    <slug>.glb                       default mode, parameters {}
    <slug>.<animation>.<index>.glb   keyframe <index> of <animation>

``scripts/dev/optimize-commons-models.mjs`` turns that directory into the LOD
files and ``manifest.json`` the page streams. This script is the render half of
``.github/workflows/prerender-commons.yml``; ``scripts/prerender-carousel.sh``
was the 2026-03 prior art (21 cartridges, first part only, no keyframes).

Incremental by construction: every cartridge gets a hash of its directory plus
the render engine fingerprint, recorded in ``raw/.render-index.json``. A slug
whose hash and files are already there is skipped, so a cached ``raw/`` from a
previous run only re-renders what changed. ``--hash-only`` prints the combined
digest the workflow keys its cache on.

Keyframes follow the API's own flipbook route
(``apps/api/routes/projects/animations.py::_interpolate_params``): numeric
parameters are interpolated from ``from_state`` to ``to_state``, rounded when
both ends are integers; booleans and strings switch at the midpoint. Unlike that
route, ``t`` here is LINEAR over the frames (the manifest's ``easing`` is for
the player's timing, not for which states get rendered).

Multi-part modes are merged into one GLB with trimesh (already a backend
dependency); single-part renders are written as the API produced them.

Usage:
    render_commons_models.py [--api http://localhost:5000] [--out apps/landing/public/models/raw]
                             [--slugs a,b,c] [--jobs 4] [--force] [--engine-fingerprint TEXT]
                             [--timeout 900]
    render_commons_models.py --hash-only [--engine-fingerprint TEXT]

Exit codes:
    0  every requested render is on disk
    2  usage / setup error (API unreachable, catalog missing, production host)
    3  at least one render failed (the others were written; failures are listed)

Never point this at api.yantra4d.com: it refuses the production host outright.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = REPO / "docs" / "commons-catalog.json"
DEFAULT_PROJECTS = REPO / "projects"
DEFAULT_OUT = REPO / "apps" / "landing" / "public" / "models" / "raw"
INDEX_NAME = ".render-index.json"
REPORT_NAME = ".render-report.json"
INDEX_VERSION = 2

PRODUCTION_HOSTS = {"api.yantra4d.com", "yantra4d.com", "app.yantra4d.com"}

# Files whose change does not change geometry, so they do not invalidate a render.
HASH_SKIP_DIRS = {"docs", "__pycache__", ".git", "exports"}
HASH_SKIP_SUFFIXES = {".md", ".png", ".webp", ".jpg", ".jpeg", ".svg", ".gif", ".pyc"}

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAILED = 3


class SetupError(Exception):
    """A precondition the operator has to fix; not a render failure."""


# ──────────────────────────────────────────────
# Keyframe interpolation
# ──────────────────────────────────────────────


def interpolate_params(from_state: dict, to_state: dict, t: float) -> dict:
    """Mirror of the API's ``_interpolate_params`` — numeric lerp, ints stay ints, else snap at t >= 0.5."""
    result: dict = {}
    for key in sorted(set(from_state) | set(to_state)):
        from_val = from_state.get(key)
        to_val = to_state.get(key)
        if from_val is None:
            result[key] = to_val
        elif to_val is None:
            result[key] = from_val
        elif (
            isinstance(from_val, (int, float))
            and isinstance(to_val, (int, float))
            and not isinstance(from_val, bool)
            and not isinstance(to_val, bool)
        ):
            value = from_val + (to_val - from_val) * t
            result[key] = round(value) if isinstance(from_val, int) and isinstance(to_val, int) else value
        else:
            result[key] = to_val if t >= 0.5 else from_val
    return result


def frame_items(slug: str, manifest: dict) -> list[dict]:
    """One render item per keyframe of every animation the manifest declares."""
    animations = manifest.get("animations")
    if not isinstance(animations, list):
        return []
    default_mode = manifest["modes"][0]["id"]
    items = []
    for anim in animations:
        if not isinstance(anim, dict) or not anim.get("id"):
            continue
        frames = int(anim.get("frames", 5))
        if frames < 2:
            continue
        mode = anim.get("mode") or default_mode
        for index in range(frames):
            t = index / (frames - 1)
            items.append(
                {
                    "file": f"{slug}.{anim['id']}.{index}.glb",
                    "slug": slug,
                    "mode": mode,
                    "parameters": interpolate_params(anim.get("from_state") or {}, anim.get("to_state") or {}, t),
                    "label": f"{anim['id']}#{index}",
                }
            )
    return items


def render_items(slug: str, manifest: dict) -> list[dict]:
    """The base render (default mode, manifest defaults) followed by the keyframes."""
    base = {
        "file": f"{slug}.glb",
        "slug": slug,
        "mode": manifest["modes"][0]["id"],
        "parameters": {},
        "label": "base",
    }
    return [base, *frame_items(slug, manifest)]


# ──────────────────────────────────────────────
# Cartridge hashing
# ──────────────────────────────────────────────


def cartridge_hash(cartridge_dir: Path, engine_fingerprint: str) -> str:
    """sha256 over the cartridge's geometry-relevant files plus the engine fingerprint."""
    digest = hashlib.sha256()
    digest.update(engine_fingerprint.encode("utf-8"))
    digest.update(b"\0")
    for root, dirs, files in sorted(os.walk(cartridge_dir)):
        dirs[:] = sorted(d for d in dirs if d not in HASH_SKIP_DIRS)
        for name in sorted(files):
            if Path(name).suffix.lower() in HASH_SKIP_SUFFIXES:
                continue
            path = Path(root) / name
            digest.update(str(path.relative_to(cartridge_dir)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def combined_digest(slug_hashes: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for slug in sorted(slug_hashes):
        digest.update(f"{slug}={slug_hashes[slug]}\n".encode())
    return digest.hexdigest()


# ──────────────────────────────────────────────
# Catalog and manifests
# ──────────────────────────────────────────────


def is_private(manifest: dict) -> bool:
    """Same two signals ``generate-landing-projects.mjs`` reads."""
    blocks = [manifest.get("access_control"), (manifest.get("project") or {}).get("access_control")]
    return any(isinstance(b, dict) and b.get("view") == "private" for b in blocks)


def load_worklist(catalog_path: Path, projects_dir: Path, only: set[str] | None) -> tuple[dict[str, dict], list[str]]:
    """slug → manifest for every public catalog cartridge with a manifest on disk; plus the skipped ones."""
    if not catalog_path.exists():
        raise SetupError(f"catalog not found: {catalog_path}")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    slugs = sorted(c["slug"] for c in catalog.get("cartridges", []) if c.get("slug"))
    if only is not None:
        unknown = sorted(only - set(slugs))
        if unknown:
            raise SetupError(f"--slugs names cartridges that are not in the catalog: {', '.join(unknown)}")
        slugs = [s for s in slugs if s in only]
    manifests: dict[str, dict] = {}
    skipped: list[str] = []
    for slug in slugs:
        path = projects_dir / slug / "project.json"
        if not path.exists():
            skipped.append(f"{slug}: no manifest at {path} (is the projects submodule initialised?)")
            continue
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if is_private(manifest):
            skipped.append(f"{slug}: private")
            continue
        if not manifest.get("modes"):
            skipped.append(f"{slug}: manifest declares no modes")
            continue
        manifests[slug] = manifest
    return manifests, skipped


# ──────────────────────────────────────────────
# API client
# ──────────────────────────────────────────────


def check_api_base(api: str) -> str:
    parsed = urllib.parse.urlsplit(api)
    host = (parsed.hostname or "").lower()
    if host in PRODUCTION_HOSTS or host.endswith(".yantra4d.com"):
        raise SetupError(f"refusing to render against production ({host}); run a local API instead")
    if not host:
        raise SetupError(f"--api must be a URL, got {api!r}")
    return api.rstrip("/")


def http_json(url: str, payload: dict | None = None, timeout: float = 30.0) -> tuple[int, dict | None, bytes]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    request.add_header("Accept", "application/json")
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            status = response.status
    except urllib.error.HTTPError as err:
        body = err.read()
        status = err.code
    try:
        parsed = json.loads(body.decode("utf-8")) if body else None
    except ValueError:
        parsed = None
    return status, parsed if isinstance(parsed, dict) else None, body


def http_bytes(url: str, timeout: float = 120.0) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def api_health(api: str) -> dict:
    status, payload, _ = http_json(f"{api}/api/health")
    if status != 200 or payload is None:
        raise SetupError(f"{api}/api/health answered {status}; start the backend first")
    return payload


def engine_fingerprint(api: str | None, extra: str) -> str:
    """What makes a rendered mesh change besides the cartridge: the kernels."""
    parts = [f"pipeline=raw-glb-v{INDEX_VERSION}"]
    if api:
        health = api_health(api)
        openscad = (health.get("checks") or {}).get("openscad") or {}
        parts.append(f"openscad={openscad.get('detail', 'unknown')}")
    try:
        from importlib.metadata import PackageNotFoundError, version

        parts.append(f"cadquery={version('cadquery')}")
    except (ImportError, PackageNotFoundError):  # cadquery is optional for --hash-only on a dev machine
        parts.append("cadquery=unknown")
    if extra:
        parts.append(f"extra={extra}")
    return "|".join(parts)


class RenderError(Exception):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def render_item(api: str, item: dict, timeout: float) -> bytes:
    """POST /api/render for one item and return the GLB bytes (parts merged when needed)."""
    # STL, not GLB, on purpose. Asking the API for glb makes it re-route an
    # OpenSCAD mode to its CadQuery twin (dual-engine cartridges such as
    # motor-mount and spiral-planter) and transcode through STEP + cascadio —
    # a path the 2026-09-19 smoke run showed failing for both with "Unknown
    # extensions, specify export type explicitly". STL is what every kernel
    # produces natively; trimesh turns it into the position-only GLB the
    # optimizer expects (merge_parts handles single- and multi-part alike).
    payload = {
        "project": item["slug"],
        "mode": item["mode"],
        "parameters": item["parameters"],
        "export_format": "stl",
    }
    status, body, raw = http_json(f"{api}/api/render", payload, timeout=timeout)
    if status == 503:
        raise RenderError("render worker unavailable (503)", retryable=True)
    if status == 429:
        raise RenderError("rate limited (429) — start the API with RATE_LIMIT_ENABLED=false", retryable=True)
    if status != 200 or body is None:
        detail = (body or {}).get("error") or (body or {}).get("message") or raw[:200].decode("utf-8", "replace")
        raise RenderError(f"HTTP {status}: {detail}", retryable=status >= 500)
    parts = body.get("parts") or []
    if not parts:
        raise RenderError(f"no parts in response: {(body.get('log') or '')[-300:]}")
    urls = [p.get("url") for p in parts if p.get("url")]
    if len(urls) != len(parts):
        raise RenderError("a part came back without a url")
    blobs = [(url, http_bytes(api + url if url.startswith("/") else url)) for url in urls]
    if len(blobs) == 1 and blobs[0][0].lower().endswith(".glb"):
        return blobs[0][1]  # a kernel that already produced GLB (not requested today)
    return merge_parts(blobs)


def merge_parts(blobs: list[tuple[str, bytes]]) -> bytes:
    """Concatenate every part (GLB or STL) into one world-space GLB with trimesh."""
    try:
        import trimesh
    except ImportError as err:  # pragma: no cover - the workflow installs the backend requirements
        raise RenderError("trimesh is required to merge multi-part renders (pip install -r apps/api/requirements.txt)") from err
    meshes = []
    try:
        for url, data in blobs:
            ext = Path(urllib.parse.urlsplit(url).path).suffix.lower().lstrip(".") or "glb"
            loaded = trimesh.load(io.BytesIO(data), file_type=ext, force="scene")
            dumped = loaded.dump(concatenate=True) if hasattr(loaded, "dump") else loaded
            if isinstance(dumped, list):
                meshes.extend(dumped)
            elif dumped is not None and not getattr(dumped, "is_empty", False):
                meshes.append(dumped)
        if not meshes:
            raise RenderError("parts contained no geometry")
        merged = trimesh.util.concatenate(meshes) if len(meshes) > 1 else meshes[0]
        return merged.export(file_type="glb")
    except (ValueError, TypeError, AttributeError, KeyError, IndexError) as err:
        raise RenderError(f"could not merge parts: {err}") from err


# ──────────────────────────────────────────────
# Index / report
# ──────────────────────────────────────────────


def load_index(out_dir: Path) -> dict:
    path = out_dir / INDEX_NAME
    if not path.exists():
        return {"version": INDEX_VERSION, "slugs": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {"version": INDEX_VERSION, "slugs": {}}
    if data.get("version") != INDEX_VERSION or not isinstance(data.get("slugs"), dict):
        return {"version": INDEX_VERSION, "slugs": {}}
    return data


def save_index(out_dir: Path, index: dict) -> None:
    ordered = {"version": INDEX_VERSION, "slugs": {k: index["slugs"][k] for k in sorted(index["slugs"])}}
    (out_dir / INDEX_NAME).write_text(json.dumps(ordered, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def up_to_date(out_dir: Path, index: dict, slug: str, digest: str, files: list[str]) -> bool:
    entry = index["slugs"].get(slug)
    return bool(entry) and entry.get("hash") == digest and entry.get("files") == files and all(
        (out_dir / f).exists() for f in files
    )


def write_summary(env: dict, lines: list[str]) -> None:
    path = env.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--api", default="http://localhost:5000", help="local API base URL (production is refused)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="raw output directory")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--projects", type=Path, default=DEFAULT_PROJECTS)
    parser.add_argument("--slugs", default="", help="comma-separated subset of catalog slugs")
    parser.add_argument("--jobs", type=int, default=4, help="concurrent renders in flight (default 4)")
    parser.add_argument("--force", action="store_true", help="re-render even when the index says up to date")
    parser.add_argument("--engine-fingerprint", default="", help="extra text folded into every cartridge hash")
    parser.add_argument("--timeout", type=float, default=900.0, help="seconds to wait for one /api/render call")
    parser.add_argument("--hash-only", action="store_true", help="print the combined cartridge digest and exit")
    parser.add_argument("--no-prune", action="store_true", help="keep raw files of cartridges no longer in the catalog")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, env: dict | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    env = dict(os.environ) if env is None else env
    only = {s.strip() for s in args.slugs.split(",") if s.strip()} or None

    try:
        manifests, skipped = load_worklist(args.catalog, args.projects, only)
        api = None if args.hash_only else check_api_base(args.api)
        fingerprint = engine_fingerprint(api, args.engine_fingerprint)
    except SetupError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        return EXIT_USAGE

    for line in skipped:
        print(f"skip {line}", file=sys.stderr)

    hashes = {slug: cartridge_hash(args.projects / slug, fingerprint) for slug in manifests}
    if args.hash_only:
        print(combined_digest(hashes))
        return EXIT_OK

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    index = load_index(out_dir)
    index_lock = threading.Lock()

    plan = {slug: render_items(slug, manifest) for slug, manifest in manifests.items()}
    todo = [
        slug
        for slug, items in plan.items()
        if args.force or not up_to_date(out_dir, index, slug, hashes[slug], [i["file"] for i in items])
    ]
    cached = len(plan) - len(todo)
    total_items = sum(len(plan[s]) for s in todo)
    print(f"{len(plan)} cartridge(s): {cached} up to date, {len(todo)} to render ({total_items} render(s)) with {args.jobs} in flight")

    # Raw files of cartridges that left the catalog (full runs only) go away with
    # their index entries, so the optimizer's --clean can retire their LODs.
    if only is None and not args.no_prune:
        current = set(plan)
        for stale in sorted(set(index["slugs"]) - current):
            for f in index["slugs"][stale].get("files", []):
                (out_dir / f).unlink(missing_ok=True)
            del index["slugs"][stale]
            print(f"pruned {stale} (no longer in the catalog)")

    failures: list[str] = []
    rendered: list[str] = []
    failures_lock = threading.Lock()
    started = time.monotonic()

    def render_with_retries(item: dict) -> bytes:
        delay = 5.0
        last: Exception | None = None
        for attempt in range(4):
            try:
                return render_item(api, item, args.timeout)
            except RenderError as err:
                last = err
                if not err.retryable:
                    raise
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                last = RenderError(f"transport error: {err}", retryable=True)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
        raise last if last else RenderError("unknown failure")

    def do_slug(slug: str) -> None:
        items = plan[slug]
        wanted = [i["file"] for i in items]
        ok = True
        for item in items:
            t0 = time.monotonic()
            try:
                data = render_with_retries(item)
            except (RenderError, OSError, ValueError) as err:
                ok = False
                with failures_lock:
                    failures.append(f"{item['file']}: {err}")
                print(f"FAIL {item['file']} ({err})", file=sys.stderr)
                continue
            # Written next to the target and renamed into place, so a cached raw/
            # never holds a half-written GLB.
            with tempfile.NamedTemporaryFile(dir=out_dir, prefix=".tmp-", suffix=".glb", delete=False) as tmp:
                tmp.write(data)
            os.replace(tmp.name, out_dir / item["file"])
            with failures_lock:
                rendered.append(item["file"])
            print(f"ok   {item['file']} {len(data):,} B in {time.monotonic() - t0:.1f}s")
        with index_lock:
            previous = set(index["slugs"].get(slug, {}).get("files", []))
            for old in sorted(previous - set(wanted)):
                (out_dir / old).unlink(missing_ok=True)
            if ok:
                index["slugs"][slug] = {"hash": hashes[slug], "files": wanted}
            else:
                # Leave no entry: the next run retries the whole cartridge.
                index["slugs"].pop(slug, None)
            save_index(out_dir, index)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        list(pool.map(do_slug, todo))

    save_index(out_dir, index)
    elapsed = time.monotonic() - started
    report = {
        "cartridges": len(plan),
        "cached": cached,
        "rendered": sorted(rendered),
        "failed": sorted(failures),
        "skipped": skipped,
        "engine_fingerprint": fingerprint,
        "elapsed_seconds": round(elapsed, 1),
    }
    (out_dir / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    summary = [
        "### Commons renders",
        "",
        (
            f"{len(plan)} cartridge(s), {cached} already rendered, {len(rendered)} render(s) written, "
            f"{len(failures)} failed, {len(skipped)} skipped, in {elapsed / 60:.1f} min."
        ),
        "",
    ]
    if failures:
        summary += ["Failed (their previous raw files, if any, were kept; a cartridge with no raw file gets no LODs):", ""]
        summary += [f"- `{f}`" for f in failures]
        summary.append("")
    write_summary(env, summary)

    print(f"done: {len(rendered)} rendered, {cached} cached, {len(failures)} failed in {elapsed:.0f}s")
    if failures:
        print(f"{len(failures)} render(s) failed:", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
