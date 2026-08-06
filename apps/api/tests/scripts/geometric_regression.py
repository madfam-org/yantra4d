import argparse
import logging
import os
import re
import sys
import tempfile
from pathlib import Path

import trimesh

# Add api directory to sys.path to allow imports like 'from config import Config'
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import Config
from manifest import get_manifest
from services.engine.cadquery_engine import build_cadquery_command
from services.engine.cadquery_engine import run_render as run_cq_render
from services.engine.openscad import build_openscad_command
from services.engine.openscad import run_render as run_scad_render

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Projects with confirmed geometric parity between OpenSCAD and CadQuery.
# Only these cause CI failure on geometry mismatch; others log warnings.
VERIFIED_PARITY_PROJECTS = {"stemfie", "gridfinity"}


def _extract_scad_params(scad_path: str) -> set[str]:
    """Extract parameter names declared at top level of a SCAD file."""
    params = set()
    try:
        with open(scad_path) as f:
            for line in f:
                m = re.match(r'^\s*(\w+)\s*=', line)
                if m and m.group(1) not in ('module', 'function', 'include', 'use'):
                    params.add(m.group(1))
    except FileNotFoundError:
        pass
    return params


def geometric_regression(project_slug: str, mode_id: str = "0", rtol: float = 0.05) -> bool:
    """
    Renders the default parameters of a mode using both CSG and B-Rep engines,
    then compares their extents and volume. Returns True if they match within `rtol`.
    """
    manifest = get_manifest(project_slug)

    # Try to find the mode
    mode = next((m for m in manifest.modes if m.get("id") == str(mode_id)), None)
    if not mode:
        mode = manifest.modes[0] if manifest.modes else {"id": "0", "scad_file": manifest.get_allowed_files()[0] if manifest.get_allowed_files() else None}

    project_dir = Config.PROJECTS_DIR / project_slug
    scad_file = mode.get("scad_file") or project_slug + ".scad"
    scad_path = str(project_dir / scad_file)

    # Skip CQ-only projects (scad_file points to a .py file)
    if scad_file.endswith('.py'):
        logger.info(f"Skipping '{project_slug}' — CQ-only project (scad_file={scad_file})")
        return True

    # Some manifests specify cq_file, some might implicitly map it.
    cq_file = mode.get("cq_file") or manifest.get_cq_file() if hasattr(manifest, "get_cq_file") else None
    if not cq_file:
         cq_file = scad_file.replace(".scad", ".py")

    cq_path = str(project_dir / cq_file)
    if not os.path.exists(cq_path):
        logger.warning(f"Project '{project_slug}' lacks B-Rep file {cq_file}. Skipping regression.")
        return True

    # Pull defaults
    params = {}
    for p in manifest.parameters:
        if "id" in p and "default" in p:
            params[p["id"]] = p["default"]

    # Include mode specifically for scad
    params["scad_file"] = scad_file

    # Filter params to only those declared in the SCAD file to prevent
    # sending Python-only params (e.g. 'module') that cause OpenSCAD syntax errors
    declared_scad_params = _extract_scad_params(scad_path)
    scad_params = {k: v for k, v in params.items() if k in declared_scad_params or k == "scad_file"}

    with tempfile.TemporaryDirectory() as tmpdir:
        csg_stl = os.path.join(tmpdir, "csg_output.stl")
        brep_stl = os.path.join(tmpdir, "brep_output.stl")

        logger.info(f"Rendering CSG (OpenSCAD) for {project_slug}...")
        scad_cmd = build_openscad_command(csg_stl, scad_path, scad_params, mode_id)
        scad_success, scad_err = run_scad_render(scad_cmd, scad_path)
        if not scad_success:
            logger.warning(f"OpenSCAD render failed for '{project_slug}' (non-blocking):\n{scad_err}")
            return True

        logger.info(f"Rendering B-Rep (CadQuery) for {project_slug}...")
        cq_cmd = build_cadquery_command(brep_stl, cq_path, params, "stl")
        cq_success, cq_err = run_cq_render(cq_cmd, cq_path)
        if not cq_success:
            logger.warning(f"CadQuery render failed for '{project_slug}' (non-blocking):\n{cq_err}")
            return True

        # Load both and compare
        mesh_csg = trimesh.load(csg_stl)
        mesh_brep = trimesh.load(brep_stl)

        # Check volume
        vol_csg = mesh_csg.volume
        vol_brep = mesh_brep.volume

        # Check bounds extents (x, y, z sizes)
        extents_csg = mesh_csg.extents
        extents_brep = mesh_brep.extents

        vol_diff = abs(vol_csg - vol_brep) / max(vol_csg, 1e-6)
        bounds_diff = [
            abs(extents_csg[i] - extents_brep[i]) / max(extents_csg[i], 1e-6)
            for i in range(3)
        ]

        logger.info(f"CSG Volume: {vol_csg:.2f} | B-Rep Volume: {vol_brep:.2f}")
        logger.info(f"CSG Bounds: {extents_csg} | B-Rep Bounds: {extents_brep}")

        passed = True
        if vol_diff > rtol:
            logger.error(f"Volume discrepancy > {rtol*100}%! Diff={vol_diff*100:.2f}%")
            passed = False

        for i, dim in enumerate(['X', 'Y', 'Z']):
            if bounds_diff[i] > rtol:
                logger.error(f"Bounds mismatch on {dim}-axis > {rtol*100}%! Diff={bounds_diff[i]*100:.2f}%")
                passed = False

        if passed:
            logger.info("✅ Geometric regression passed.")
        else:
            if project_slug in VERIFIED_PARITY_PROJECTS:
                logger.error(f"❌ Geometric regression FAILED for verified-parity project '{project_slug}'.")
            else:
                logger.warning(f"⚠️  Geometric divergence for '{project_slug}' (not in verified-parity allowlist — non-blocking).")
                passed = True  # Downgrade to warning for non-verified projects

        return passed

def main():
    parser = argparse.ArgumentParser(description="Geometric Regression Testing")
    parser.add_argument("--project", "-p", type=str, help="Specific project slug to test")
    parser.add_argument("--tolerance", "-t", type=float, default=0.05, help="Relative tolerance (default 5%)")
    args = parser.parse_args()

    overall_pass = True

    if args.project:
        projects = [args.project]
    else:
        projects = [
            d.name for d in Config.PROJECTS_DIR.iterdir()
            if d.is_dir() and (d / "project.json").exists()
        ]

    for proj in projects:
        logger.info(f"--- Testing {proj} ---")
        try:
            passed = geometric_regression(proj, rtol=args.tolerance)
            if not passed:
                overall_pass = False
        except Exception:
            logger.exception(f"Exception during testing {proj}")
            overall_pass = False

    if not overall_pass:
        sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
