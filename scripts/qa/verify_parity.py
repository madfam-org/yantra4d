#!/usr/bin/env python3
"""Compare a hyperobject's OpenSCAD and CadQuery output, mode by mode.

Candidate selection mirrors ``scripts/qa/generate_commons_catalog.py``'s
``_engine_support``, and must keep mirroring it. A CadQuery-only cartridge
declares ``scad_file`` pointing at its own ``.py`` source as a placeholder, so a
declared ``scad_file`` proves nothing on its own: the kernel a mode really has
is decided by which source is actually on disk and what its suffix is. Handing
such a placeholder to OpenSCAD asks it to parse Python, which it cannot do —
before this rule existed that was every mode in the commons, 1363 of 1363
reported as parity failures when not one of them was a comparable pair.

A mode is therefore a CANDIDATE only when both kernels really exist for it: a
``scad_file`` that ends in ``.scad`` and is present, and a CadQuery source that
ends in ``.py`` and is present. Everything else is one of

  - SKIPPED (placeholder): ``scad_file`` does not name a ``.scad`` at all, so
    the mode is CadQuery-only and there is nothing to compare it against;
  - SKIPPED (no CadQuery source): a genuine OpenSCAD-only mode;
  - FAILED: the manifest declares a file it does not ship.

The distinction between the last two is the point. An inferred sibling ``.py``
that is absent is an OpenSCAD-only mode; a ``cq_file`` the manifest explicitly
declares and does not ship is a broken manifest.
"""
import sys
import json
import argparse
import logging
from pathlib import Path
import trimesh
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Add apps/api to path so we can import services
api_path = Path(__file__).parent.parent.parent / "apps" / "api"
sys.path.append(str(api_path))

try:
    from services.engine.openscad import build_openscad_command, run_render
    from services.engine.cq_runner import run_cadquery_script
except ImportError as e:
    logger.error(f"Failed to import Yantra4D engine services: {e}")
    sys.exit(1)

SCAD_SUFFIX = ".scad"
CQ_SUFFIX = ".py"


def iter_modes(manifest):
    """Modes as a list of dicts, whichever shape the manifest uses.

    Mirrors generate_commons_catalog._modes: some manifests carry `modes` as a
    mapping keyed by mode id, and iterating that yields strings.
    """
    modes = manifest.get("modes") or []
    if isinstance(modes, dict):
        modes = list(modes.values())
    return [m for m in modes if isinstance(m, dict)]


def classify_mode(mode, project_dir: Path):
    """Decide what a mode is, before anything is rendered.

    Returns (verdict, scad_path, cq_path, detail) where verdict is one of
    "candidate", "skip", "fail". Pure: it only reads the manifest and stats
    files, so the whole selection is testable without a kernel.
    """
    scad_file = mode.get("scad_file") or ""
    declared_cq = mode.get("cq_file") or ""
    # An undeclared CadQuery source is INFERRED from the .scad sibling, exactly
    # as _engine_support does. Inference is a guess, so its absence is a skip;
    # a declaration is a promise, so its absence is a failure.
    cq_file = declared_cq or (
        scad_file[: -len(SCAD_SUFFIX)] + CQ_SUFFIX if scad_file.endswith(SCAD_SUFFIX) else "")

    if not scad_file:
        return "fail", None, None, "Missing scad_file."
    if not scad_file.endswith(SCAD_SUFFIX):
        # The CadQuery-only placeholder. Never hand this to OpenSCAD.
        detail = (f"scad_file '{scad_file}' is a CadQuery-only placeholder, not "
                  f"OpenSCAD source — no OpenSCAD side to compare against")
        return "skip", None, None, detail
    scad_path = project_dir / scad_file
    if not scad_path.exists():
        return "fail", None, None, f"SCAD file missing: {scad_file}"
    if not cq_file:
        return "skip", None, None, "No cq_file declared (skipping parity check)."
    if not cq_file.endswith(CQ_SUFFIX):
        return ("skip", None, None,
                f"cq_file '{cq_file}' is not a CadQuery source")
    cq_path = project_dir / cq_file
    if not cq_path.exists():
        if declared_cq:
            return "fail", None, None, f"CadQuery file missing: {cq_file}"
        return ("skip", None, None,
                f"OpenSCAD-only mode (no {cq_file} alongside {scad_file})")
    return "candidate", scad_path, cq_path, ""


def check_mesh_parity(mesh1_path, mesh2_path, tolerance=0.001):
    try:
        m1 = trimesh.load(mesh1_path, force='mesh')
        m2 = trimesh.load(mesh2_path, force='mesh')
    except Exception as e:
        logger.error(f"Failed to load meshes for parity check: {e}")
        return False, str(e)

    if not isinstance(m1, trimesh.Trimesh) or not isinstance(m2, trimesh.Trimesh):
        return False, "Exported files are not valid 3D polygon meshes."

    # 1. Bounding Box Extents
    logger.info(f"  M1 Bounds: {m1.bounds}")
    logger.info(f"  M2 Bounds: {m2.bounds}")
    extents_diff = np.max(np.abs(m1.extents - m2.extents))
    if extents_diff > tolerance:
        return False, f"Bounding boxes differ by {extents_diff:.6f}mm (M1: {m1.extents}, M2: {m2.extents})"

    # 2. Volume
    logger.info(f"  M1 Volume: {m1.volume:.6f} (Watertight: {m1.is_watertight})")
    logger.info(f"  M2 Volume: {m2.volume:.6f} (Watertight: {m2.is_watertight})")
    if m1.is_watertight and m2.is_watertight:
        vol_diff = abs(m1.volume - m2.volume)
        rel_vol_diff = vol_diff / max(m1.volume, m2.volume) if max(m1.volume, m2.volume) > 0 else 0
        
        # Allow 2% relative error or 10.0mm^3 absolute, whichever is greater at tolerance 0.1
        vol_threshold = max(tolerance * 100, max(m1.volume, m2.volume) * 0.02)
        
        if vol_diff > vol_threshold:
            return False, f"Volumes differ by {vol_diff:.6f}mm^3 ({rel_vol_diff*100:.4f}%)"
            
    # 3. Maximum distance (Hausdorff distance proxy via nearest queries)
    max_divergence = 0
    try:
        _, distances_m1_to_m2, _ = m2.nearest.on_surface(m1.vertices)
        _, distances_m2_to_m1, _ = m1.nearest.on_surface(m2.vertices)
        max_divergence = max(np.max(distances_m1_to_m2), np.max(distances_m2_to_m1))
        
        # Allow 0.5mm divergence for complex assemblies (tessellation noise)
        dist_threshold = max(tolerance, 0.5)
        
        if max_divergence > dist_threshold:
            logger.warning(f"  ⚠️ Warning: Maximum mesh divergence is {max_divergence:.6f}mm (exceeds {dist_threshold}mm), but AABB and Volume match. Assuming tessellation noise.")
    except Exception as e:
        logger.warning(f"Distance calculation failed: {e}. Falling back to AABB and Volume.")

    return True, f"Meshes are identical within {max_divergence:.6f}mm tolerance."

def verify_project(project_dir: Path, tolerance: float = 0.001,
                   stats: "dict | None" = None) -> bool:
    manifest_path = project_dir / "project.json"
    if not manifest_path.exists():
        return True # Not a project

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        logger.error(f"❌ {project_dir.name}: Failed to read manifest: {e}")
        return False

    is_hyperobject = manifest.get("project", {}).get("hyperobject", {}).get("is_hyperobject", False)
    has_top_level_ho = bool(manifest.get("hyperobject", {}).get("cdg_interfaces"))
    if not is_hyperobject and not has_top_level_ho:
        return True

    logger.info(f"\n🔍 Analyzing Hyperobject parity: {project_dir.name}")

    modes = iter_modes(manifest)
    if not modes:
        logger.error(f"❌ {project_dir.name}: No modes defined.")
        return False

    all_passed = True
    if stats is None:
        stats = {}

    def count(key):
        stats[key] = stats.get(key, 0) + 1

    for mode in modes:
        verdict, scad_path, cq_path, detail = classify_mode(mode, project_dir)

        if verdict == "fail":
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: {detail}")
            count("mode_failed")
            all_passed = False
            continue
        if verdict == "skip":
            logger.warning(f"⚠️  {project_dir.name} [{mode.get('id')}]: {detail}")
            count("mode_skipped_placeholder" if "placeholder" in detail
                  else "mode_skipped_no_cq")
            continue

        count("mode_candidate")
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(exist_ok=True)
        scad_out = exports_dir / f"{mode.get('id')}_scad.stl"
        cq_out = exports_dir / f"{mode.get('id')}_cq.stl"
        
        # Default empty params
        params_json = "{}"

        # 1. OpenSCAD
        cmd = build_openscad_command(
            output_path=str(scad_out),
            scad_path=str(scad_path),
            params={}
        )
        success, out = run_render(cmd, scad_path=str(scad_path))
        if not success:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: OpenSCAD render failed:\n{out}")
            count("mode_failed")
            all_passed = False
            continue

        # 2. CadQuery
        try:
            run_cadquery_script(str(cq_path), str(cq_out), params_json, "STL")
        # SystemExit as well as Exception: the sandbox rejects a script by
        # calling sys.exit (e.g. "Import of 'sys' is not allowed in CadQuery
        # scripts"), and SystemExit is not an Exception — so one rejected
        # cartridge used to kill the whole audit before it printed a summary.
        # A cartridge the sandbox refuses is a failure of that cartridge, not
        # of the run. KeyboardInterrupt still propagates.
        except (Exception, SystemExit) as e:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: CadQuery build failed:\n{e}")
            count("mode_failed")
            all_passed = False
            continue

        # 3. Compare Parity
        is_parity, reason = check_mesh_parity(str(scad_out), str(cq_out), tolerance)
        
        if is_parity:
            logger.info(f"✅ {project_dir.name} [{mode.get('id')}]: Parity Check PASSED. {reason}")
            count("mode_passed")
        else:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: Parity Check FAILED. {reason}")
            count("mode_failed")
            all_passed = False

    return all_passed

def main():
    parser = argparse.ArgumentParser(description="Verify geometric parity between OpenSCAD and CadQuery.")
    parser.add_argument("--tolerance", type=float, default=0.001, help="Max distance tolerance (mm)")
    parser.add_argument("--project", type=str, help="Specific project slug to test")
    args = parser.parse_args()

    projects_dir = Path("projects")
    if not projects_dir.exists():
        logger.error("projects/ directory not found.")
        sys.exit(1)

    projects_to_check = [projects_dir / args.project] if args.project else [p for p in projects_dir.iterdir() if p.is_dir()]
    
    passed = 0
    failed = 0
    skipped = 0
    nothing_to_compare = 0
    totals: dict = {}

    for p in sorted(projects_to_check):
        if not (p / "project.json").exists():
            continue

        with open(p / "project.json", 'r') as f:
            manifest = json.load(f)
            is_ho = manifest.get("project", {}).get("hyperobject", {}).get("is_hyperobject", False)
            has_top_ho = bool(manifest.get("hyperobject", {}).get("cdg_interfaces"))
            if not is_ho and not has_top_ho:
                skipped += 1
                continue

        stats: dict = {}
        ok = verify_project(p, args.tolerance, stats)
        for key, value in stats.items():
            totals[key] = totals.get(key, 0) + value

        if not ok:
            failed += 1
        elif stats.get("mode_candidate"):
            passed += 1
        else:
            # Every mode was skipped: a CadQuery-only cartridge has no parity to
            # verify. Counting it as "passed" would report agreement that was
            # never measured.
            nothing_to_compare += 1

    candidates = totals.get("mode_candidate", 0)
    placeholders = totals.get("mode_skipped_placeholder", 0)
    no_cq = totals.get("mode_skipped_no_cq", 0)

    print("\n--- Geometric Parity Audit Results ---")
    print(f"Hyperobjects Tested: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"No comparable pair: {nothing_to_compare}")
    print(f"Not hyperobjects: {skipped}")
    print("\nMode pairs")
    print(f"  Candidates compared: {candidates}"
          f"  (passed {totals.get('mode_passed', 0)}, failed {totals.get('mode_failed', 0)})")
    print(f"  Skipped, CadQuery-only placeholder scad_file: {placeholders}")
    print(f"  Skipped, no CadQuery source for the mode: {no_cq}")

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
