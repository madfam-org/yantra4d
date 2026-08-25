#!/usr/bin/env python3
"""Render real raster thumbnails for the commons catalog (defect D11).

Replaces SVG placeholders / missing thumbnails with real renders of each
cartridge's default mode, using the same engine contracts as production:

- CadQuery cartridges run through ``apps/api/services/engine/cq_runner.py``
  (the production sandbox runner) with ``target_part`` + manifest defaults,
  exactly like ``apps/worker/render_worker.py`` does.
- OpenSCAD cartridges run the OpenSCAD CLI with ``-D`` params and the part's
  ``render_mode``, with ``OPENSCADPATH`` set like
  ``apps/api/services/engine/openscad._openscad_env``.
- Implicit cartridges call ``apps/api/services/core/implicit_engine.run_render``
  imported as a library.

Meshes are rasterized offscreen with matplotlib (Agg) using flat lambert
shading, the manifest's ``iso`` camera view, per-part manifest colors, and a
consistent neutral background, then written as 800x600 WEBP (or PNG when the
manifest declares a .png thumbnail).

Run inside a venv that has: cadquery==2.7.0 trimesh numpy pillow matplotlib
scikit-image (for the implicit engine) and optionally fast-simplification
(decimation of very heavy meshes). Never install these globally.

Usage:
  render_commons_thumbnails.py render --worklist worklist.json --out STAGING \
      [--slugs a,b,c] [--jobs 4] [--force] [--keep-work]
  render_commons_thumbnails.py publish --out STAGING [--sync-legacy]
  render_commons_thumbnails.py recount

The worklist JSON is ``{"missing": [slug...], "svg_only": [slug...]}``.
``render`` is resumable: existing staged images are skipped unless --force.
"""

import argparse
import io
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS_DIR = REPO / "projects"
CQ_RUNNER = REPO / "apps" / "api" / "services" / "engine" / "cq_runner.py"
IMPLICIT_ENGINE = REPO / "apps" / "api" / "services" / "core" / "implicit_engine.py"
STUDIO_PUB = REPO / "apps" / "studio" / "public" / "projects"
LANDING_PUB = REPO / "apps" / "landing" / "public" / "projects"

RENDER_TIMEOUT_S = int(os.getenv("RENDER_TIMEOUT_S", "300"))  # matches render_engine.py
BACKGROUND = "#f4f4f2"
THUMB_SIZE = (800, 600)
MAX_FACES = 220_000  # decimate above this if fast-simplification is available
DEFAULT_CAM = [1.0, 1.0, 0.8]
FALLBACK_COLORS = ["#4a6f8f", "#5b83a3", "#6f9abf", "#8fb0c9", "#3d5a73", "#7a8fa3"]
RASTER_EXTS = (".webp", ".png", ".jpg", ".jpeg")

_RASTER_LOCK = threading.Lock()
_LOG_LOCK = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
# Manifest helpers (mirrors apps/api/manifest.py resolution rules)
# ──────────────────────────────────────────────────────────────────────────────

def load_manifest(slug: str) -> dict:
    with open(PROJECTS_DIR / slug / "project.json", encoding="utf-8") as f:
        return json.load(f)


def project_engine(manifest: dict) -> str:
    proj = manifest.get("project", {})
    explicit = proj.get("engine", "openscad")
    if explicit == "implicit":
        return "implicit"
    if "implicit_field" in proj.get("hyperobject", {}):
        return "implicit"
    if explicit in ("openscad", "cadquery"):
        return explicit
    return "openscad"


def mode_engine(manifest: dict, mode: dict) -> str:
    proj_eng = project_engine(manifest)
    if proj_eng == "implicit":
        return "implicit"
    explicit = mode.get("engine")
    if explicit in ("openscad", "cadquery", "implicit"):
        return explicit
    primary = mode.get("scad_file") or ""
    if primary.endswith((".py", ".cq")):
        return "cadquery"
    return proj_eng


def default_params(manifest: dict, mode_id: str) -> dict:
    """Manifest defaults for a mode, typed like openscad.validate_params."""
    params = {}
    for p in manifest.get("parameters", []):
        modes = p.get("modes")
        if modes and mode_id not in modes:
            continue
        if "default" not in p:
            continue
        d = p["default"]
        ptype = p.get("type", "slider")
        try:
            if ptype == "slider":
                v = float(d)
                # Keep integral sliders as ints: cartridge scripts often do
                # int(str(param)) and int("13.0") raises.
                params[p["id"]] = int(v) if v.is_integer() else v
            elif ptype == "checkbox":
                params[p["id"]] = 1 if str(d).lower() in ("1", "true", "1.0") else 0
            else:
                params[p["id"]] = str(d)
        except (TypeError, ValueError):
            continue
    return params


def part_defs(manifest: dict) -> dict:
    out = {}
    for p in manifest.get("parts", []):
        out[p["id"]] = {
            "render_mode": p.get("render_mode", 0),
            "color": p.get("color") or p.get("default_color"),
            "static_stl": p.get("static_stl"),
        }
    return out


def iso_camera(manifest: dict) -> list:
    views = manifest.get("camera_views", []) or []
    iso = next((v for v in views if v.get("id") == "iso"), None)
    pos = (iso or (views[0] if views else {})).get("position")
    if not pos or len(pos) != 3 or not any(pos):
        return list(DEFAULT_CAM)
    return [float(c) for c in pos]


def declared_thumbnail(manifest: dict) -> str:
    return manifest.get("project", {}).get("thumbnail") or ""


def thumb_ext(manifest: dict) -> str:
    return ".png" if declared_thumbnail(manifest).lower().endswith(".png") else ".webp"


# ──────────────────────────────────────────────────────────────────────────────
# Geometry generation (per part) — production engine contracts
# ──────────────────────────────────────────────────────────────────────────────

def find_openscad(cli_arg: str | None) -> str | None:
    candidates = [
        cli_arg,
        os.getenv("OPENSCAD_PATH"),
        shutil.which("openscad"),
        "/Applications/OpenSCAD-Snapshot.app/Contents/MacOS/OpenSCAD",
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    ]
    return next((c for c in candidates if c and Path(c).is_file()), None)


def _tail(text: str, n: int = 4) -> str:
    lines = [ln for ln in (text or "").strip().splitlines() if ln.strip()]
    return " | ".join(lines[-n:])[-500:]


def run_cadquery_part(script_path: Path, out_stl: Path, params: dict, part: str) -> tuple[bool, str]:
    """Render one part via the production cq_runner sandbox (subprocess)."""
    cq_params = dict(params)
    cq_params["target_part"] = part  # same injection as apps/worker/render_worker.py
    env = os.environ.copy()
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{PROJECTS_DIR}{os.pathsep}{prev}" if prev else str(PROJECTS_DIR)
    cmd = [sys.executable, str(CQ_RUNNER), str(script_path), str(out_stl),
           json.dumps(cq_params), "STL"]
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True,
                             timeout=RENDER_TIMEOUT_S, env=env, cwd=script_path.parent)
    except subprocess.TimeoutExpired:
        return False, f"cadquery timeout after {RENDER_TIMEOUT_S}s"
    if res.returncode != 0 or not out_stl.is_file() or out_stl.stat().st_size == 0:
        return False, f"cadquery rc={res.returncode}: {_tail(res.stdout + res.stderr)}"
    return True, ""


# NOTE: an earlier revision carried an automatic "unsandboxed exec" fallback
# here that re-ran cartridge scripts with unrestricted builtins whenever the
# cq_runner sandbox rejected them. That silently converted a security control's
# rejection into an unrestricted execution of (potentially vendored
# third-party) cartridge code, so it was removed before this script reached
# origin. A cartridge that fails the sandbox is reported as FAILED with the
# sandbox error — that is a defect in the cartridge to fix, not a reason to
# bypass the sandbox.


def openscad_d_args(params: dict) -> list:
    """Mirror openscad.build_openscad_command -D encoding."""
    args = []
    for key, value in params.items():
        if isinstance(value, bool):
            val = "1" if value else "0"
        elif isinstance(value, (int, float)):
            val = str(value)
        else:
            val = f'"{value}"'
        args.extend(["-D", f"{key}={val}"])
    return args


def _openscad_env(project_dir: Path) -> dict:
    env = os.environ.copy()
    env["OPENSCADPATH"] = os.pathsep.join([
        str(project_dir),
        str(REPO / "libs"),
        str(REPO / "libs" / "dotSCAD" / "src"),
        str(PROJECTS_DIR),
    ])
    return env


def run_openscad_stl(openscad: str, scad_path: Path, out_stl: Path, params: dict,
                     render_mode: int) -> tuple[bool, str]:
    cmd = [openscad, "-o", str(out_stl)] + openscad_d_args(params)
    if render_mode:
        cmd.extend(["-D", f"render_mode={render_mode}"])
    cmd.append(str(scad_path))
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True,
                             timeout=RENDER_TIMEOUT_S, env=_openscad_env(scad_path.parent),
                             cwd=scad_path.parent)
    except subprocess.TimeoutExpired:
        return False, f"openscad timeout after {RENDER_TIMEOUT_S}s"
    if res.returncode != 0 or not out_stl.is_file() or out_stl.stat().st_size == 0:
        return False, f"openscad rc={res.returncode}: {_tail(res.stderr)}"
    return True, ""


def run_openscad_png(openscad: str, scad_path: Path, out_png: Path, params: dict,
                     render_mode: int, cam: list) -> tuple[bool, str]:
    """Fallback: let OpenSCAD rasterize a preview PNG directly (2x supersampled)."""
    cmd = [openscad, "-o", str(out_png), "--imgsize=1600,1200", "--viewall",
           "--autocenter", "--colorscheme=Tomorrow", "--projection=p",
           f"--camera={cam[0]},{cam[1]},{cam[2]},0,0,0"]
    cmd += openscad_d_args(params)
    if render_mode:
        cmd.extend(["-D", f"render_mode={render_mode}"])
    cmd.append(str(scad_path))
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=180,
                             env=_openscad_env(scad_path.parent), cwd=scad_path.parent)
    except subprocess.TimeoutExpired:
        return False, "openscad png timeout after 180s"
    if res.returncode != 0 or not out_png.is_file() or out_png.stat().st_size == 0:
        return False, f"openscad png rc={res.returncode}: {_tail(res.stderr)}"
    return True, ""


_implicit_module = None


def run_implicit_part(manifest: dict, out_stl: Path, params: dict) -> tuple[bool, str]:
    global _implicit_module
    if _implicit_module is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("yantra_implicit", IMPLICIT_ENGINE)
        _implicit_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_implicit_module)
    config = manifest.get("project", {}).get("hyperobject", {}).get("implicit_field", {})
    try:
        ok = _implicit_module.run_render(str(out_stl), config, params)
    except Exception as e:  # noqa: BLE001 — report, never fake
        return False, f"implicit engine: {e}"
    if not (out_stl.is_file() and out_stl.stat().st_size > 0):
        return False, f"implicit engine produced no mesh (ok={ok})"
    return True, ""


# ──────────────────────────────────────────────────────────────────────────────
# Rasterization — matplotlib Agg, flat lambert shading, manifest camera/colors
# ──────────────────────────────────────────────────────────────────────────────

def hex_to_rgb(color: str | None, idx: int) -> tuple:
    c = (color or FALLBACK_COLORS[idx % len(FALLBACK_COLORS)]).lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    try:
        return tuple(int(c[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return (0.35, 0.48, 0.60)


def load_mesh(path: Path):
    import trimesh
    mesh = trimesh.load(str(path), force="mesh", process=True)
    if mesh is None or not hasattr(mesh, "faces") or len(mesh.faces) == 0:
        raise ValueError("empty mesh")
    return mesh


def maybe_decimate(mesh, budget: int):
    if len(mesh.faces) <= budget:
        return mesh
    try:
        import fast_simplification  # noqa: F401
        return mesh.simplify_quadric_decimation(face_count=budget)
    except Exception:  # noqa: BLE001 — decimation is best-effort
        return mesh  # render full geometry, just slower


def rasterize(meshes: list, cam: list, out_path: Path, fmt: str) -> None:
    """meshes: [(trimesh.Trimesh, (r,g,b))]. Writes 800x600 webp/png."""
    import matplotlib
    import numpy as np

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from PIL import Image, ImageOps

    total = sum(len(m.faces) for m, _ in meshes)
    if total > MAX_FACES:
        share = MAX_FACES / total
        meshes = [(maybe_decimate(m, max(2000, int(len(m.faces) * share))), c)
                  for m, c in meshes]

    lo = np.min([m.bounds[0] for m, _ in meshes], axis=0)
    hi = np.max([m.bounds[1] for m, _ in meshes], axis=0)
    center = (lo + hi) / 2.0
    half = float(np.max(hi - lo)) / 2.0
    if half <= 0:
        raise ValueError("degenerate mesh bounds")
    half *= 1.02

    cam_v = np.array(cam, dtype=float)
    cam_u = cam_v / (np.linalg.norm(cam_v) or 1.0)
    elev = math.degrees(math.asin(max(-1.0, min(1.0, cam_u[2]))))
    azim = math.degrees(math.atan2(cam_u[1], cam_u[0]))
    light = cam_u * 0.55 + np.array([0.0, 0.0, 0.85])
    light /= np.linalg.norm(light)

    fig = plt.figure(figsize=(8, 6), dpi=125)
    try:
        ax = fig.add_subplot(111, projection="3d")
        fig.patch.set_facecolor(BACKGROUND)
        ax.set_facecolor(BACKGROUND)
        ax.set_axis_off()
        fig.subplots_adjust(left=0, right=1, bottom=0, top=1)

        for mesh, rgb in meshes:
            shade = 0.34 + 0.64 * np.clip(mesh.face_normals @ light, 0.0, 1.0)
            facecolors = np.clip(np.array(rgb)[None, :] * shade[:, None], 0.0, 1.0)
            coll = Poly3DCollection(mesh.vertices[mesh.faces], shade=False,
                                    facecolors=facecolors, edgecolors=facecolors,
                                    linewidths=0.05)
            coll.set_zsort("average")
            ax.add_collection3d(coll)

        ax.set_xlim(center[0] - half, center[0] + half)
        ax.set_ylim(center[1] - half, center[1] + half)
        ax.set_zlim(center[2] - half, center[2] + half)
        ax.set_box_aspect((1, 1, 1))
        ax.view_init(elev=elev, azim=azim)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", facecolor=BACKGROUND)
    finally:
        plt.close(fig)

    buf.seek(0)
    img = Image.open(buf).convert("RGB")
    img = _frame(img, ImageOps)
    _save_raster(img, out_path, fmt)


def _frame(img, ImageOps):
    """Tight-crop the render and recompose on a consistent 4:3 canvas."""
    from PIL import Image, ImageChops
    bg = Image.new("RGB", img.size, BACKGROUND)
    diff = ImageChops.difference(img, bg)
    bbox = diff.getbbox()
    if bbox:
        img = img.crop(bbox)
    pad_w = int(img.width * 0.08) or 10
    pad_h = int(img.height * 0.08) or 10
    canvas_w = img.width + 2 * pad_w
    canvas_h = img.height + 2 * pad_h
    ratio = THUMB_SIZE[0] / THUMB_SIZE[1]
    if canvas_w / canvas_h < ratio:
        canvas_w = int(canvas_h * ratio)
    else:
        canvas_h = int(canvas_w / ratio)
    canvas = Image.new("RGB", (canvas_w, canvas_h), BACKGROUND)
    canvas.paste(img, ((canvas_w - img.width) // 2, (canvas_h - img.height) // 2))
    return canvas.resize(THUMB_SIZE, Image.LANCZOS)


def _save_raster(img, out_path: Path, fmt: str) -> None:
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    if fmt == ".webp":
        img.save(tmp, "WEBP", quality=90, method=6)
    else:
        img.save(tmp, "PNG", optimize=True)
    os.replace(tmp, out_path)


def convert_png_file(src_png: Path, out_path: Path, fmt: str) -> None:
    from PIL import Image
    img = Image.open(src_png).convert("RGB")
    img = img.resize(THUMB_SIZE, Image.LANCZOS)
    _save_raster(img, out_path, fmt)


# ──────────────────────────────────────────────────────────────────────────────
# Per-slug pipeline
# ──────────────────────────────────────────────────────────────────────────────

def render_slug(slug: str, out_dir: Path, work_root: Path, openscad: str | None,
                keep_work: bool) -> dict:
    t0 = time.monotonic()
    entry = {"slug": slug, "status": "failed", "engine": None, "parts": [],
             "failed_parts": [], "method": "mesh", "error": None, "seconds": 0.0}
    work = work_root / slug
    try:
        manifest = load_manifest(slug)
    except Exception as e:  # noqa: BLE001
        entry["error"] = f"manifest: {e}"
        return entry

    fmt = thumb_ext(manifest)
    out_path = out_dir / f"{slug}{fmt}"
    modes = manifest.get("modes") or []
    if not modes:
        entry["error"] = "manifest has no modes"
        return entry
    mode = modes[0]  # default mode, same as render_orchestrator.resolve_render_context
    engine = mode_engine(manifest, mode)
    entry["engine"] = engine
    params = default_params(manifest, mode.get("id", ""))
    defs = part_defs(manifest)
    parts = list(mode.get("parts") or list(defs)[:1])
    cam = iso_camera(manifest)
    project_dir = PROJECTS_DIR / slug

    work.mkdir(parents=True, exist_ok=True)
    meshes = []
    seen_render_modes = {}
    try:
        for i, part in enumerate(parts[:8]):
            pdef = defs.get(part, {"render_mode": 0, "color": None, "static_stl": None})
            rgb = hex_to_rgb(pdef["color"], i)
            stl = work / f"{part}.stl"
            ok, err = False, "unknown engine"

            if pdef["static_stl"]:
                src = project_dir / pdef["static_stl"]
                if src.is_file():
                    shutil.copyfile(src, stl)
                    ok, err = True, ""
                else:
                    ok, err = False, f"static_stl missing: {pdef['static_stl']}"
            elif engine == "cadquery":
                script = mode.get("cq_file") or mode.get("scad_file")
                ok, err = run_cadquery_part(project_dir / script, stl, params, part)
                if not ok and "is not defined" in err:
                    # Sandbox-blocked builtin (globals/getattr/eval/...) — a
                    # cartridge defect to fix at the source; never bypassed.
                    err = f"sandbox-blocked (fix the cartridge): {err}"
                if not ok and openscad:
                    # Reverse dual-engine fallback: a sibling .scad with the same
                    # stem is the cartridge's own legacy-kernel source (e.g.
                    # rail.py -> rail.scad). Real geometry, shipped by the
                    # cartridge itself.
                    sibling = (project_dir / script).with_suffix(".scad")
                    if sibling.is_file():
                        sc_ok, sc_err = run_openscad_stl(
                            openscad, sibling, stl, params, pdef["render_mode"])
                        if sc_ok:
                            ok, err = True, ""
                            entry["method"] = "mesh+scad-fallback"
                        else:
                            err = f"{err}; scad fallback: {sc_err}"
            elif engine == "implicit":
                ok, err = run_implicit_part(manifest, stl, params)
            elif engine == "openscad":
                rm = pdef["render_mode"]
                if rm in seen_render_modes:  # identical geometry already rendered
                    prior = seen_render_modes[rm]
                    if prior is not None:
                        meshes.append((prior, rgb))
                    continue
                ok, err = run_openscad_stl(openscad, project_dir / mode["scad_file"],
                                           stl, params, rm) if openscad else \
                    (False, "no OpenSCAD binary found")
                if not ok and mode.get("cq_file") and mode["cq_file"] != mode.get("scad_file"):
                    # Dual-engine cartridge: fall back to the mode's CadQuery file,
                    # like render_orchestrator.resolve_engine_config does.
                    cq_ok, cq_err = run_cadquery_part(
                        project_dir / mode["cq_file"], stl, params, part)
                    if cq_ok:
                        ok, err = True, ""
                        entry["method"] = "mesh+cq-fallback"
                    else:
                        err = f"{err}; cq fallback: {cq_err}"

            if not ok:
                entry["failed_parts"].append({"part": part, "error": err})
                if engine == "openscad":
                    seen_render_modes[pdef["render_mode"]] = None
                continue
            try:
                mesh = load_mesh(stl)
            except Exception as e:  # noqa: BLE001
                entry["failed_parts"].append({"part": part, "error": f"mesh load: {e}"})
                if engine == "openscad":
                    seen_render_modes[pdef["render_mode"]] = None
                continue
            meshes.append((mesh, rgb))
            entry["parts"].append(part)
            if engine == "openscad":
                seen_render_modes[pdef["render_mode"]] = mesh

        if meshes:
            with _RASTER_LOCK:
                rasterize(meshes, cam, out_path, fmt)
            entry["status"] = "rendered" if not entry["failed_parts"] else "partial"
        elif engine == "openscad" and openscad:
            # Last resort: OpenSCAD's own preview rasterizer (real geometry, its colors)
            png = work / "fallback.png"
            rm = defs.get(parts[0], {}).get("render_mode", 0) if parts else 0
            ok, err = run_openscad_png(openscad, project_dir / mode["scad_file"],
                                       png, params, rm, [c * 140 for c in DEFAULT_CAM])
            if ok:
                with _RASTER_LOCK:
                    convert_png_file(png, out_path, fmt)
                entry["status"] = "rendered"
                entry["method"] = "openscad-png"
                entry["parts"] = parts[:1]
            else:
                entry["error"] = "; ".join(
                    f"{f['part']}: {f['error']}" for f in entry["failed_parts"]) or err
        else:
            entry["error"] = "; ".join(
                f"{f['part']}: {f['error']}" for f in entry["failed_parts"]) or "no parts"
    except Exception as e:  # noqa: BLE001
        entry["error"] = f"raster: {e}"
    finally:
        if not keep_work:
            shutil.rmtree(work, ignore_errors=True)
        entry["seconds"] = round(time.monotonic() - t0, 1)
    return entry


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────

def cmd_render(args) -> int:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    work_root = out_dir / "work"
    log_path = Path(args.log) if args.log else out_dir / "render-log.jsonl"

    if args.slugs:
        slugs = [s.strip() for s in args.slugs.split(",") if s.strip()]
    else:
        with open(args.worklist, encoding="utf-8") as f:
            wl = json.load(f)
        slugs = list(wl.get("missing", [])) + list(wl.get("svg_only", []))

    openscad = find_openscad(args.openscad)
    if not openscad:
        print("WARNING: no OpenSCAD binary found; openscad cartridges will fail",
              file=sys.stderr)

    todo = []
    for slug in slugs:
        try:
            fmt = thumb_ext(load_manifest(slug))
        except Exception:  # noqa: BLE001 — render_slug reports the real error
            fmt = ".webp"
        if not args.force and (out_dir / f"{slug}{fmt}").is_file():
            continue
        todo.append(slug)
    print(f"{len(slugs)} slugs requested, {len(slugs) - len(todo)} already staged, "
          f"{len(todo)} to render (jobs={args.jobs})")

    results = []
    done = 0
    with open(log_path, "a", encoding="utf-8") as log, \
            ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(render_slug, s, out_dir, work_root, openscad,
                               args.keep_work): s for s in todo}
        for fut in as_completed(futures):
            entry = fut.result()
            results.append(entry)
            done += 1
            with _LOG_LOCK:
                log.write(json.dumps(entry) + "\n")
                log.flush()
            flag = {"rendered": "ok", "partial": "PARTIAL"}.get(entry["status"], "FAILED")
            print(f"[{done}/{len(todo)}] {entry['slug']}: {flag} "
                  f"({entry['engine']}, {entry['seconds']}s"
                  + (f", {entry['error']}" if entry.get("error") else "") + ")")

    ok = sum(1 for r in results if r["status"] in ("rendered", "partial"))
    failed = [r for r in results if r["status"] == "failed"]
    print(f"\nrendered {ok}/{len(todo)}; {len(failed)} failed")
    for r in failed:
        print(f"  FAILED {r['slug']}: {r['error']}")
    return 0 if not failed else 1


def cmd_publish(args) -> int:
    out_dir = Path(args.out)
    images = sorted(p for p in out_dir.iterdir()
                    if p.suffix in (".webp", ".png") and p.is_file())
    for dest in (STUDIO_PUB, LANDING_PUB):
        dest.mkdir(parents=True, exist_ok=True)
        for img in images:
            shutil.copyfile(img, dest / img.name)
    print(f"published {len(images)} images to {STUDIO_PUB} and {LANDING_PUB}")

    if args.sync_legacy:
        synced = 0
        for src in sorted(LANDING_PUB.iterdir()):
            if src.suffix not in RASTER_EXTS:
                continue
            slug = src.stem
            if not (PROJECTS_DIR / slug / "project.json").is_file():
                continue
            if not any((STUDIO_PUB / f"{slug}{e}").is_file() for e in RASTER_EXTS):
                shutil.copyfile(src, STUDIO_PUB / src.name)
                synced += 1
        print(f"synced {synced} legacy landing rasters into studio")
    return 0


def cmd_recount(_args) -> int:
    rows = []
    for mpath in sorted(PROJECTS_DIR.glob("*/project.json")):
        slug = mpath.parent.name
        try:
            manifest = load_manifest(slug)
        except Exception as e:  # noqa: BLE001
            rows.append((slug, "manifest-error", str(e)))
            continue
        declared = declared_thumbnail(manifest)
        if not declared:
            rows.append((slug, "none-declared", ""))
            continue
        if not declared.startswith("/projects/"):
            resolved = (mpath.parent / declared).is_file()
            rows.append((slug, "relative-" + ("ok" if resolved else "missing"), declared))
            continue
        name = declared.rsplit("/", 1)[-1]
        in_studio = (STUDIO_PUB / name).is_file()
        in_landing = (LANDING_PUB / name).is_file()
        is_raster = name.lower().endswith(RASTER_EXTS)
        svg = (STUDIO_PUB / f"{slug}.svg").is_file() or (LANDING_PUB / f"{slug}.svg").is_file()
        if is_raster and in_studio and in_landing:
            state = "raster-both"
        elif is_raster and (in_studio or in_landing):
            state = "raster-one-dir"
        elif svg:
            state = "svg-only"
        else:
            state = "missing"
        rows.append((slug, state, declared))

    from collections import Counter
    counts = Counter(state for _, state, _ in rows)
    print(f"{len(rows)} manifests scanned")
    for state, n in sorted(counts.items()):
        print(f"  {state}: {n}")
    for slug, state, detail in rows:
        if state not in ("raster-both",):
            print(f"  GAP {slug}: {state} ({detail})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("render", help="render thumbnails into a staging dir")
    r.add_argument("--worklist", help="JSON with {missing:[], svg_only:[]}")
    r.add_argument("--slugs", help="comma-separated slugs (overrides --worklist)")
    r.add_argument("--out", required=True, help="staging output dir")
    r.add_argument("--jobs", type=int, default=4)
    r.add_argument("--openscad", help="path to OpenSCAD binary")
    r.add_argument("--force", action="store_true")
    r.add_argument("--keep-work", action="store_true")
    r.add_argument("--log", help="JSONL log path (default: <out>/render-log.jsonl)")
    r.set_defaults(fn=cmd_render)

    p = sub.add_parser("publish", help="copy staged images into both public dirs")
    p.add_argument("--out", required=True)
    p.add_argument("--sync-legacy", action="store_true",
                   help="also copy legacy landing rasters missing from studio")
    p.set_defaults(fn=cmd_publish)

    c = sub.add_parser("recount", help="classify declared thumbnails vs files on disk")
    c.set_defaults(fn=cmd_recount)

    args = ap.parse_args()
    if args.cmd == "render" and not (args.worklist or args.slugs):
        ap.error("render requires --worklist or --slugs")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
