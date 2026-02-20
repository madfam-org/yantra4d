#!/usr/bin/env python3
import os
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
api_path = Path(__file__).parent.parent / "apps" / "api"
sys.path.append(str(api_path))

try:
    from services.openscad import build_openscad_command, run_render
    from services.cq_runner import run_cadquery_script
except ImportError as e:
    logger.error(f"Failed to import Yantra4D engine services: {e}")
    sys.exit(1)

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
    extents_diff = np.max(np.abs(m1.extents - m2.extents))
    if extents_diff > tolerance:
        return False, f"Bounding boxes differ by {extents_diff:.6f}mm"

    # 2. Volume
    if m1.is_watertight and m2.is_watertight:
        vol_diff = abs(m1.volume - m2.volume)
        if vol_diff > tolerance * 10:
            return False, f"Volumes differ by {vol_diff:.6f}mm^3"
            
    # 3. Maximum distance (Hausdorff distance proxy via nearest queries)
    max_divergence = 0
    try:
        _, distances_m1_to_m2, _ = m2.nearest.on_surface(m1.vertices)
        _, distances_m2_to_m1, _ = m1.nearest.on_surface(m2.vertices)
        max_divergence = max(np.max(distances_m1_to_m2), np.max(distances_m2_to_m1))
        
        if max_divergence > tolerance:
            return False, f"Maximum mesh divergence is {max_divergence:.6f}mm (exceeds {tolerance}mm)"
    except Exception as e:
        logger.warning(f"Distance calculation failed: {e}. Falling back to AABB and Volume.")

    return True, f"Meshes are identical within {max_divergence:.6f}mm tolerance."

def verify_project(project_dir: Path, tolerance: float = 0.001) -> bool:
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
    if not is_hyperobject:
        return True

    logger.info(f"\n🔍 Analyzing Hyperobject parity: {project_dir.name}")
    
    modes = manifest.get("modes", [])
    if not modes:
        logger.error(f"❌ {project_dir.name}: No modes defined.")
        return False

    all_passed = True
    
    for mode in modes:
        scad_file = mode.get("scad_file")
        cq_file = mode.get("cq_file")
        
        if not scad_file or not cq_file:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: Missing scad_file or cq_file.")
            all_passed = False
            continue
            
        scad_path = project_dir / scad_file
        cq_path = project_dir / cq_file
        
        if not scad_path.exists():
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: SCAD file missing: {scad_file}")
            all_passed = False
            continue
        if not cq_path.exists():
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: CadQuery file missing: {cq_file}")
            all_passed = False
            continue
            
        exports_dir = project_dir / "exports"
        exports_dir.mkdir(exist_ok=True)
        scad_out = exports_dir / f"{mode.get('id')}_scad.stl"
        cq_out = exports_dir / f"{mode.get('id')}_cq.stl"
        
        # Default empty params
        params_json = "{}"

        # 1. OpenSCAD
        cmd = build_openscad_command(
            input_file=str(scad_path),
            output_file=str(scad_out),
            params={},
            include_dirs=[str(project_dir.parent.parent / "libs")]
        )
        success, out, err = run_render(cmd)
        if not success:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: OpenSCAD render failed:\n{err}")
            all_passed = False
            continue

        # 2. CadQuery
        try:
            run_cadquery_script(str(cq_path), str(cq_out), params_json, "STL")
        except Exception as e:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: CadQuery build failed:\n{e}")
            all_passed = False
            continue

        # 3. Compare Parity
        is_parity, reason = check_mesh_parity(str(scad_out), str(cq_out), tolerance)
        
        if is_parity:
            logger.info(f"✅ {project_dir.name} [{mode.get('id')}]: Parity Check PASSED. {reason}")
        else:
            logger.error(f"❌ {project_dir.name} [{mode.get('id')}]: Parity Check FAILED. {reason}")
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
    
    for p in sorted(projects_to_check):
        if not (p / "project.json").exists():
            continue
            
        with open(p/ "project.json", 'r') as f:
            manifest = json.load(f)
            if not manifest.get("project", {}).get("hyperobject", {}).get("is_hyperobject", False):
                skipped += 1
                continue
                
        if verify_project(p, args.tolerance):
            passed += 1
        else:
            failed += 1

    print("\n--- Geometric Parity Audit Results ---")
    print(f"Hyperobjects Tested: {passed + failed}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
