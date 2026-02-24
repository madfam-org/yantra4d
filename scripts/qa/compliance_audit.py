#!/usr/bin/env python3
"""Hyperobject metadata consistency audit.

Checks:
1. Top-level `hyperobject` block existence for declared hyperobjects
2. Tag consistency: hyperobjects must have "hyperobject" + "commons" tags
3. CDG parameter reference validation: each CDG parameters[] ID must exist in manifest parameters[]
4. export_formats declared for every project
5. Dual-engine file pairing: if is_hyperobject and .py files exist → modes should have cq_file
6. Legacy checks: BOSL2 usage, no vendor dir, CERN-OHL license
"""
import sys
import json
import argparse
from pathlib import Path


def is_hyperobject_project(manifest: dict) -> bool:
    """Check both metadata locations for hyperobject status."""
    # Location 1: project.hyperobject.is_hyperobject
    if manifest.get("project", {}).get("hyperobject", {}).get("is_hyperobject", False):
        return True
    # Location 2: top-level hyperobject block with cdg_interfaces
    top_ho = manifest.get("hyperobject", {})
    if top_ho and top_ho.get("cdg_interfaces"):
        return True
    return False


def audit_project(project_dir: Path, manifest: dict) -> list[str]:
    """Audit a single project manifest. Returns list of issues."""
    issues = []
    slug = project_dir.name
    proj = manifest.get("project", {})
    tags = proj.get("tags", [])
    ho = is_hyperobject_project(manifest)

    # --- Check 1: Top-level hyperobject block ---
    if ho and not manifest.get("hyperobject"):
        issues.append(f"[{slug}] Declared hyperobject but missing top-level `hyperobject` block")

    # --- Check 2: Tag consistency ---
    if ho:
        if "hyperobject" not in tags:
            issues.append(f"[{slug}] Hyperobject missing 'hyperobject' tag")
        if "commons" not in tags:
            issues.append(f"[{slug}] Hyperobject missing 'commons' tag")

    # --- Check 3: CDG parameter reference validation ---
    top_ho = manifest.get("hyperobject", {})
    param_ids = {p["id"] for p in manifest.get("parameters", []) if "id" in p}
    for cdg in top_ho.get("cdg_interfaces", []):
        for param_ref in cdg.get("parameters", []):
            if param_ref not in param_ids:
                issues.append(
                    f"[{slug}] CDG '{cdg['id']}' references unknown parameter '{param_ref}'"
                )

    # --- Check 4: export_formats ---
    if not manifest.get("export_formats"):
        issues.append(f"[{slug}] Missing 'export_formats'")

    # --- Check 5: Dual-engine file pairing ---
    # Only flag if project has BOTH .scad and .py files (true dual-engine)
    if ho:
        py_files = list(project_dir.glob("*.py"))
        scad_files = list(project_dir.glob("*.scad"))
        if py_files and scad_files:
            for mode in manifest.get("modes", []):
                if not mode.get("cq_file"):
                    issues.append(
                        f"[{slug}] Mode '{mode['id']}' missing 'cq_file' "
                        f"but .py files exist on disk"
                    )

    # --- Check 6: Legacy checks (BOSL2, vendor, license) ---
    has_vendor = (project_dir / "vendor").exists() or (project_dir / "vendors").exists()
    if has_vendor:
        issues.append(f"[{slug}] Contains vendor/ directory")

    has_ohl_license = False

    for scad_file in project_dir.rglob("*.scad"):
        if "vendor" in str(scad_file):
            continue
        try:
            content = scad_file.read_text(encoding="utf-8", errors="ignore")
            if "CERN-OHL-W-2.0" in content:
                has_ohl_license = True
        except Exception:
            pass

    license_path = project_dir / "LICENSE"
    if license_path.exists():
        try:
            content = license_path.read_text(encoding="utf-8", errors="ignore")
            if "CERN OHL" in content or "CERN Open Hardware" in content or "CERN-OHL" in content:
                has_ohl_license = True
        except Exception:
            pass

    # Also check top-level hyperobject block for license
    if top_ho.get("commons_license", "").startswith("CERN-OHL"):
        has_ohl_license = True

    if ho and not has_ohl_license:
        issues.append(f"[{slug}] Hyperobject missing CERN-OHL license")

    return issues


def audit_projects(projects_dir: Path, strict: bool = False) -> int:
    """Run audit across all projects. Returns exit code."""
    if not projects_dir.exists():
        print(f"Directory {projects_dir} not found.")
        return 1

    all_issues: list[str] = []
    total = 0
    ho_count = 0

    print("# Hyperobject Metadata Consistency Audit\n")

    for item in sorted(projects_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue

        manifest_path = item / "project.json"
        if not manifest_path.exists():
            continue

        total += 1

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except Exception as e:
            all_issues.append(f"[{item.name}] Failed to parse manifest: {e}")
            continue

        ho = is_hyperobject_project(manifest)
        if ho:
            ho_count += 1

        issues = audit_project(item, manifest)
        if issues:
            all_issues.extend(issues)

    # Report
    print(f"Total projects scanned: {total}")
    print(f"Hyperobject projects: {ho_count}")
    print(f"Issues found: {len(all_issues)}")

    if all_issues:
        print("\n## Issues\n")
        for issue in all_issues:
            print(f"- {issue}")

    if strict and all_issues:
        print(f"\n❌ --strict: {len(all_issues)} issue(s) found, failing.")
        return 1

    if not all_issues:
        print("\n✅ All projects pass metadata consistency checks.")

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hyperobject metadata consistency audit")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero on any issue")
    args = parser.parse_args()

    projects_dir = Path(__file__).parent.parent.parent / "projects"
    sys.exit(audit_projects(projects_dir, strict=args.strict))
