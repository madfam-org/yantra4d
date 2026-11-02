#!/usr/bin/env python3
"""Opt-in, local CadQuery preset archive; never contacts a render API.

Build real GLB/WebP assets and copy committed SVG projections from a clean, exact
public commons commit. This draft integration format is not a keystone schema.
The existing landing default/keyframe pipeline is unchanged. See
``docs/reference/factory-preset-archive.md`` for the contract and check scope.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import os
import platform
import re
import subprocess
import sys
import tarfile
import tempfile
from importlib.metadata import PackageNotFoundError, distribution, version
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
SCHEMA = "factory-preset-archive/0.1"
COMMONS_REPOSITORY = "https://github.com/madfam-org/solid-hyperobjects"
FULL_PIN = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
FRAME = {
    "units": "m", "up_axis": "Y", "handedness": "right",
    "source_units": "mm", "source_up_axis": "Z",
    "source_to_asset_matrix": [
        [0.001, 0, 0, 0], [0, 0, 0.001, 0], [0, -0.001, 0, 0], [0, 0, 0, 1],
    ],
    "matrix_convention": "row-major; column vectors; no recentering",
}
SVG_FRAME = {
    "units": "svg-user-unit", "up_axis": "negative-Y", "handedness": "screen",
    "scale": "presentation; not a physical millimetre drawing",
}


class ArchiveError(ValueError):
    """A missing or inconsistent source/artifact is an explicit failure."""


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), *args],
                                       text=True, stderr=subprocess.PIPE).strip()
    except subprocess.CalledProcessError as exc:
        raise ArchiveError(f"git source check failed: {exc.stderr.strip()}") from exc


def verify_source(root: Path, pin: str) -> None:
    if not FULL_PIN.fullmatch(pin):
        raise ArchiveError("--pin must be the full lowercase 40-character source commit")
    if git(root, "rev-parse", "HEAD") != pin:
        raise ArchiveError("full source pin mismatch")
    remote = git(root, "remote", "get-url", "origin").removesuffix(".git")
    if remote not in (COMMONS_REPOSITORY, "git@github.com:madfam-org/solid-hyperobjects"):
        raise ArchiveError("expected the explicitly trusted public solid commons repository")
    if git(root, "status", "--porcelain", "--untracked-files=normal"):
        raise ArchiveError("source checkout is dirty; freeze a clean commit first")


def safe_file(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ArchiveError("invalid relative asset/source path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or any(p in ("", ".", "..") for p in relative.split("/")):
        raise ArchiveError("asset/source path must stay within its root")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ArchiveError("asset/source path escapes its root")
    if not path.is_file():
        raise ArchiveError(f"missing asset/source: {relative}")
    return path


def source_identity(root: Path, pin: str, slug: str) -> dict:
    paths = git(root, "ls-files", "--", slug).splitlines()
    if f"{slug}/project.json" not in paths:
        raise ArchiveError(f"{slug}: manifest is not committed at the selected source")
    files = [{"path": p, "sha256": file_hash(safe_file(root, p))} for p in sorted(paths)]
    return {"commons": "solid-hyperobjects", "repository": COMMONS_REPOSITORY,
            "pin": pin, "tree": git(root, "rev-parse", "HEAD^{tree}"),
            "manifest_sha256": file_hash(root / slug / "project.json"),
            "files": files, "source_sha256": digest(files)}


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def native_helpers():
    return _module("archive_native_thumbnails", REPO / "scripts/dev/render_commons_thumbnails.py")


def normalize_parameters(manifest: dict, requested: dict) -> dict:
    # Share the API normalizer, without importing an engine, app or request context.
    api = str(REPO / "apps/api")
    if api not in sys.path:
        sys.path.insert(0, api)
    from services.engine.parameter_validation import validate_parameters

    defs = manifest.get("parameters") or []
    defaults = {p["id"]: p["default"] for p in defs if "default" in p}
    supplied = {**defaults, **requested}
    for key, value in supplied.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise ArchiveError(f"non-finite parameter: {key}")
    resolved = validate_parameters(supplied, defs)
    rejected = set(supplied) - set(resolved)
    if rejected:
        raise ArchiveError(f"rejected parameters: {', '.join(sorted(rejected))}")
    return resolved


def preset_items(root: Path, slug: str, selected: set[str] | None = None,
                 mode_override: str | None = None) -> tuple[list[dict], list[str]]:
    if not SLUG.fullmatch(slug):
        raise ArchiveError(f"invalid cartridge slug: {slug}")
    manifest = json.loads(safe_file(root, f"{slug}/project.json").read_text())
    access = [manifest.get("access_control"), (manifest.get("project") or {}).get("access_control")]
    if any(isinstance(a, dict) and a.get("view") == "private" for a in access):
        raise ArchiveError(f"{slug}: private cartridges are not archive inputs")
    meta_path = root / slug / "project.meta.json"
    if meta_path.is_file() and json.loads(meta_path.read_text()).get("source", {}).get("type") in ("fork", "github"):
        raise ArchiveError("only trusted public commons cartridges are supported")
    presets = [{"slug": "archetype-default", "kind": "archetype", "values": {},
                "source": "Manifest defaults; no historical product or edition is asserted."},
               *manifest.get("presets", [])]
    names = [p.get("slug") for p in presets]
    if len(set(names)) != len(names):
        raise ArchiveError(f"{slug}: duplicate preset identities")
    if selected and selected - set(names):
        raise ArchiveError(f"{slug}: unknown presets: {', '.join(sorted(selected - set(names)))}")
    modes = {m["id"]: m for m in manifest.get("modes", [])}
    if not modes:
        raise ArchiveError(f"{slug}: no modes")
    items, skipped = [], []
    for preset in presets:
        name = preset["slug"]
        if selected and name not in selected:
            continue
        if not SLUG.fullmatch(name):
            raise ArchiveError(f"invalid preset slug: {name}")
        if preset.get("kind") == "fold_state":
            skipped.append(f"solid/{slug}/{name}")
            continue
        mode_id = mode_override or preset.get("mode") or next(iter(modes))
        if mode_id not in modes:
            raise ArchiveError(f"{slug}/{name}: unknown mode {mode_id}")
        mode = modes[mode_id]
        engine = mode.get("engine") or manifest.get("project", {}).get("engine", "openscad")
        source_file = mode.get("scad_file", "")
        if engine != "cadquery" or not source_file.endswith((".py", ".cq")) or mode.get("graph_file"):
            raise ArchiveError(f"{slug}/{name}: only trusted native CadQuery modes supported")
        safe_file(root / slug, source_file)
        if f"{slug}/{source_file}" not in git(root, "ls-files", "--", f"{slug}/{source_file}").splitlines():
            raise ArchiveError("mode source must be committed")
        parts = list(mode.get("parts") or [])
        if not parts or len(set(parts)) != len(parts) or not all(SLUG.fullmatch(p) or re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts):
            raise ArchiveError(f"{slug}/{name}: mode must declare unique part IDs")
        declared_parts = {p["id"] for p in manifest.get("parts", [])}
        if set(parts) - declared_parts:
            raise ArchiveError(f"{slug}/{name}: mode names undeclared parts")
        requested = dict(preset.get("values") or {})
        items.append({"key": f"solid/{slug}/{name}", "slug": slug, "preset": name,
                      "mode": mode_id, "parts": parts, "requested": requested,
                      "resolved_parameters": normalize_parameters(manifest, requested),
                      "source_file": source_file, "manifest": manifest,
                      "preset_metadata": {k: v for k, v in preset.items() if k != "values"}})
    return items, skipped


def runtime_identity() -> dict:
    paths = ["scripts/dev/render_commons_presets.py", "scripts/dev/render_commons_thumbnails.py",
             "apps/api/services/engine/cq_runner.py", "apps/api/services/engine/cq_sandbox.py",
             "apps/api/services/engine/parameter_validation.py"]
    files = [{"path": p, "sha256": file_hash(REPO / p)} for p in paths]
    versions = {"python": platform.python_version(), "platform": platform.system(),
                "machine": platform.machine()}
    metadata = {}
    for name in ["cadquery", "cadquery-ocp", "trimesh", "numpy", "Pillow", "matplotlib", "commons-sandbox"]:
        try:
            dist = distribution(name)
            versions[name] = version(name)
            record = dist.read_text("RECORD")
            metadata[name] = hashlib.sha256((record or dist.read_text("METADATA") or "").encode()).hexdigest()
        except PackageNotFoundError:
            versions[name] = "unavailable"
    # Hash the installed sandbox's actual Python sources, not its version alone.
    import commons_sandbox
    sandbox = Path(commons_sandbox.__file__).parent
    for p in sorted(sandbox.rglob("*.py")):
        files.append({"path": "installed/commons_sandbox/" + str(p.relative_to(sandbox)),
                      "sha256": file_hash(p)})
    result = {"repository": "https://github.com/madfam-org/yantra4d",
              "revision": git(REPO, "rev-parse", "HEAD"),
              "working_tree_dirty": bool(git(REPO, "status", "--porcelain", "--untracked-files=normal")),
              "files": files,
              "versions": versions, "distribution_records_sha256": metadata,
              "scope": "actual batch/runner/sandbox sources plus package versions and distribution RECORD metadata; not an OS/container or installed-binary closure"}
    result["fingerprint"] = digest(result)
    return result


def projection_files(root: Path, item: dict) -> list[tuple[str, str]]:
    # Longest preset prefix prevents preset 'a' stealing 'a-longer-front.svg'.
    names = ["archetype-default", *[p["slug"] for p in item["manifest"].get("presets", [])]]
    matches = []
    for p in sorted((root / item["slug"] / "docs/projections").glob("*.svg")):
        owner = next((n for n in sorted(names, key=len, reverse=True) if p.stem.startswith(n + "-")), None)
        if owner == item["preset"]:
            relative = p.relative_to(root).as_posix()
            if relative not in git(root, "ls-files", "--", relative).splitlines():
                raise ArchiveError(f"projection is not committed: {relative}")
            matches.append((p.stem[len(owner) + 1:], relative))
    return matches


def entry_digest(source: dict, item: dict, runtime: dict) -> str:
    return digest({"source": source, "mode": item["mode"], "parts": item["parts"],
                   "requested": item["requested"], "resolved": item["resolved_parameters"],
                   "runtime": runtime["fingerprint"], "frame": FRAME})


def asset_record(path: Path, out: Path, frame: dict, **extra) -> dict:
    return {"path": path.relative_to(out).as_posix(), "sha256": file_hash(path),
            "bytes": path.stat().st_size, "frame": frame, **extra}


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    tmp.replace(path)


def normalized_glb(meshes: list[tuple[str, object, tuple]]) -> bytes:
    import numpy as np
    import trimesh
    scene = trimesh.Scene()
    for part, mesh, rgb in meshes:
        rendered = mesh.copy()
        rendered.apply_transform(np.asarray(FRAME["source_to_asset_matrix"]))
        rendered.units = "m"
        rendered.visual.face_colors = [round(c * 255) for c in rgb] + [255]
        scene.add_geometry(rendered, geom_name=part, node_name=part)
    return scene.export(file_type="glb")


def native_environment(root: Path) -> dict:
    """Minimal runtime linkage/locale environment, as in the worker CQ policy."""
    exact = {"PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "TMPDIR", "LD_LIBRARY_PATH",
             "PYTHONUNBUFFERED", "PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE",
             "FONTCONFIG_FILE", "FONTCONFIG_PATH"}
    prefixes = ("CSF_", "CASROOT", "MMGT_", "OCCT_", "OCP_")
    env = {k: v for k, v in os.environ.items() if k in exact or k.startswith(prefixes)}
    env["PYTHONPATH"] = str(root)
    env["YANTRA4D_CURATED_ROOTS"] = str(root)
    return env


def render_entry(root: Path, pin: str, item: dict, runtime: dict, out: Path,
                 timeout: float = 300, evaluation_root: Path | None = None) -> dict:
    helpers = native_helpers()
    evaluation_root = evaluation_root or root
    helpers.PROJECTS_DIR = evaluation_root
    helpers.RENDER_TIMEOUT_S = timeout
    source = {**source_identity(root, pin, item["slug"]), "params": item["requested"]}
    for record in source["files"]:
        if file_hash(safe_file(evaluation_root, record["path"])) != record["sha256"]:
            raise ArchiveError("frozen evaluation bytes differ from source identity")
    entry_hash = entry_digest(source, item, runtime)
    dest = out / item["key"] / entry_hash
    dest.mkdir(parents=True, exist_ok=True)
    meshes, part_results = [], []
    defs = {p["id"]: p for p in item["manifest"].get("parts", [])}
    with tempfile.TemporaryDirectory(prefix="factory-preset-") as work:
        for i, part in enumerate(item["parts"]):
            stl = Path(work) / f"{part}.stl"
            definition = defs.get(part, {})
            if definition.get("static_stl"):
                stl.write_bytes(safe_file(evaluation_root / item["slug"], definition["static_stl"]).read_bytes())
            else:
                ok, error = helpers.run_cadquery_part(evaluation_root / item["slug"] / item["source_file"],
                                                     stl, item["resolved_parameters"], part,
                                                     runtime_env=native_environment(evaluation_root))
                if not ok:
                    raise ArchiveError(f"{item['key']}/{part}: {error}")
            mesh = helpers.load_mesh(stl)
            if not all(math.isfinite(float(v)) for row in mesh.bounds for v in row):
                raise ArchiveError(f"{item['key']}/{part}: non-finite geometry bounds")
            rgb = helpers.hex_to_rgb(definition.get("color") or definition.get("default_color"), i)
            meshes.append((part, mesh, rgb))
            part_results.append({"id": part, "native_mesh_sha256": file_hash(stl),
                                 "bounds_mm": mesh.bounds.tolist(), "faces": len(mesh.faces),
                                 "watertight": bool(mesh.is_watertight)})
    glb, webp = dest / "model.glb", dest / "preview.webp"
    atomic_bytes(glb, normalized_glb(meshes))
    helpers.rasterize([(mesh, rgb) for _, mesh, rgb in meshes],
                      helpers.iso_camera(item["manifest"]), webp, ".webp")
    assets = {
        "glb": asset_record(glb, out, FRAME),
        "webp": asset_record(webp, out, {"units": "pixel", "up_axis": "negative-Y",
                                        "scale": "presentation", "source_frame": {"units": "mm", "up_axis": "Z"}}),
    }
    projections = []
    for view, relative in projection_files(root, item):
        copied = dest / f"projection-{view}.svg"
        atomic_bytes(copied, safe_file(evaluation_root, relative).read_bytes())
        projections.append(asset_record(copied, out, SVG_FRAME, view=view,
                                       source_path=relative, verification="committed-source-only",
                                       parameter_parity="not rerendered; source view overrides not recorded"))
    if projections:
        assets["svg"] = projections[0]
        assets["projections"] = projections
    verify_source(root, pin)  # detect source edits during evaluation
    return {"key": item["key"], "slug": item["slug"], "preset": item["preset"],
            "mode": item["mode"], "status": "rendered", "source": source,
            "resolved_parameters": item["resolved_parameters"], "frame": FRAME,
            "parts": item["parts"], "part_results": part_results,
            "geometry_sha256": digest(part_results), "engine_fingerprint": runtime["fingerprint"],
            "runtime": runtime, "entry_digest": entry_hash, "assets": assets,
            "provenance": {"geometry": "evaluated canonical parametric family; not a historical product likeness",
                           "preset": item["preset_metadata"], "source_status": "clean exact commit",
                           "verification": "all declared mode parts rendered; mesh observations are not fabrication or physical fit verification",
                           "historical_reference": "caller-owned; no historical SKU identity inferred from the family or preset"}}


def all_assets(entry: dict):
    for kind, value in entry.get("assets", {}).items():
        if kind == "projections":
            yield from value
        elif isinstance(value, dict):
            yield value


def _check_archive(out: Path, expected_pin: str | None = None) -> dict:
    manifest = json.loads(safe_file(out, "manifest.json").read_text())
    if manifest.get("schema") != SCHEMA or manifest.get("factory") != "solid":
        raise ArchiveError("unsupported archive format/factory")
    if expected_pin is not None and not FULL_PIN.fullmatch(expected_pin):
        raise ArchiveError("expected pin must be full40")
    entries = manifest.get("entries", [])
    keys = [e.get("key") for e in entries]
    requested = manifest.get("coverage", {}).get("requested", [])
    if not requested or len(set(keys)) != len(keys) or sorted(keys) != sorted(requested):
        raise ArchiveError("missing, duplicate or incomplete per-preset coverage")
    if sorted(manifest.get("coverage", {}).get("rendered", [])) != sorted(keys):
        raise ArchiveError("stale rendered coverage ledger")
    if manifest.get("coverage", {}).get("failed"):
        raise ArchiveError("archive contains failed preset coverage")
    for entry in entries:
        pin = entry.get("source", {}).get("pin", "")
        if not FULL_PIN.fullmatch(pin) or (expected_pin and pin != expected_pin):
            raise ArchiveError("full source pin mismatch")
        if entry.get("status") != "rendered" or entry.get("key") != f"solid/{entry.get('slug')}/{entry.get('preset')}":
            raise ArchiveError("invalid preset identity/status")
        if entry.get("frame") != FRAME:
            raise ArchiveError("unsupported or stale frame")
        parts = entry.get("parts", [])
        if not parts or [p["id"] for p in entry.get("part_results", [])] != parts:
            raise ArchiveError("missing declared mode part coverage")
        if entry.get("geometry_sha256") != digest(entry["part_results"]):
            raise ArchiveError("stale geometry digest")
        runtime = dict(entry.get("runtime", {}))
        fp = runtime.pop("fingerprint", None)
        if digest(runtime) != fp or fp != entry.get("engine_fingerprint"):
            raise ArchiveError("stale runtime fingerprint")
        source = entry["source"]
        if source.get("source_sha256") != digest(source.get("files")):
            raise ArchiveError("stale source file digest")
        item = {"mode": entry["mode"], "parts": parts, "requested": source["params"],
                "resolved_parameters": entry["resolved_parameters"]}
        if entry.get("entry_digest") != entry_digest(source, item, entry["runtime"]):
            raise ArchiveError("stale parameters/source/runtime digest")
        if not all(kind in entry.get("assets", {}) for kind in ("glb", "webp")):
            raise ArchiveError("missing required GLB/WebP assets")
        if entry["assets"]["glb"].get("frame") != FRAME:
            raise ArchiveError("stale GLB asset frame")
        for asset in all_assets(entry):
            path = safe_file(out, asset["path"])
            if not SHA256.fullmatch(asset.get("sha256", "")) or file_hash(path) != asset["sha256"]:
                raise ArchiveError(f"stale asset hash: {asset['path']}")
            if path.stat().st_size != asset.get("bytes") or path.stat().st_size == 0:
                raise ArchiveError(f"stale/empty asset size: {asset['path']}")
    return manifest


def check_archive(out: Path, expected_pin: str | None = None) -> dict:
    """Reject malformed manifests as integrity errors rather than type tracebacks."""
    try:
        return _check_archive(out, expected_pin)
    except ArchiveError:
        raise
    except (AttributeError, TypeError, KeyError, ValueError, IndexError) as exc:
        raise ArchiveError("malformed archive manifest or evidence value") from exc


def build_archive(root: Path, pin: str, slugs: list[str], out: Path,
                  presets: set[str] | None = None, mode: str | None = None,
                  timeout: float = 300, force: bool = False) -> dict:
    root, out = root.resolve(), out.resolve()
    verify_source(root, pin)
    if out == root or out.is_relative_to(root):
        raise ArchiveError("output must be outside the frozen source checkout")
    items, skipped = [], []
    for slug in slugs:
        batch, omitted = preset_items(root, slug, presets, mode)
        items.extend(batch)
        skipped.extend(omitted)
    if not items:
        raise ArchiveError("no eligible presets requested; zero coverage is not a pass")
    if len({i["key"] for i in items}) != len(items):
        raise ArchiveError("duplicate requested preset keys")
    runtime = runtime_identity()
    old = {}
    if (out / "manifest.json").is_file() and not force:
        try:
            old = {e["key"]: e for e in check_archive(out)["entries"]}
        except (ArchiveError, ValueError, KeyError, OSError):
            pass  # stale/missing assets must be rendered again, never accepted by existence alone
    entries, failures = [], []
    # Execute an immutable git-archive export, never ignored/untracked helpers or
    # a live worktree that another process can edit while the runner imports it.
    with tempfile.TemporaryDirectory(prefix="factory-source-") as frozen:
        frozen_root = Path(frozen)
        exported = subprocess.check_output(["git", "-C", str(root), "archive", pin])
        with tarfile.open(fileobj=io.BytesIO(exported)) as archive:
            archive.extractall(frozen_root, filter="data")
        for item in items:
            try:
                source = {**source_identity(root, pin, item["slug"]), "params": item["requested"]}
                previous = old.get(item["key"])
                if previous and previous["entry_digest"] == entry_digest(source, item, runtime):
                    entries.append(previous)
                else:
                    entries.append(render_entry(root, pin, item, runtime, out, timeout, frozen_root))
            except (ArchiveError, ValueError, OSError) as exc:
                failures.append({"key": item["key"], "error": str(exc)})
    verify_source(root, pin)
    manifest = {"schema": SCHEMA, "factory": "solid", "entries": entries,
                "coverage": {"requested": [i["key"] for i in items],
                             "rendered": [e["key"] for e in entries],
                             "failed": failures, "skipped_fold_state": skipped}}
    atomic_bytes(out / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2,
                                                   allow_nan=False).encode() + b"\n")
    return manifest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--projects-root", type=Path, default=REPO / "projects")
    build.add_argument("--pin", required=True, help="full exact public commons commit")
    build.add_argument("--slugs", required=True, help="comma-separated cartridge slugs")
    build.add_argument("--preset", action="append", help="selected preset, repeatable; default: all")
    build.add_argument("--mode", help="explicit mode override; otherwise preset mode or first mode")
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--timeout", type=float, default=300)
    build.add_argument("--force", action="store_true")
    check = sub.add_parser("check")
    check.add_argument("--out", type=Path, required=True)
    check.add_argument("--pin", help="require this exact full source pin for every entry")
    args = ap.parse_args(argv)
    try:
        if args.command == "check":
            manifest = check_archive(args.out.resolve(), args.pin)
        else:
            manifest = build_archive(args.projects_root, args.pin,
                                     [s.strip() for s in args.slugs.split(",") if s.strip()],
                                     args.out, set(args.preset) if args.preset else None,
                                     args.mode, args.timeout, args.force)
            if manifest["coverage"]["failed"]:
                print(json.dumps(manifest["coverage"], indent=2), file=sys.stderr)
                return 3
            check_archive(args.out.resolve(), args.pin)
        print(f"{SCHEMA}: entries={len(manifest['entries'])} failures=0")
        return 0
    except (ArchiveError, OSError, KeyError, ValueError) as exc:
        print(f"archive error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
