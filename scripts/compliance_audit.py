import os
import json
from pathlib import Path

# Hyperobject Standards (from Phase 3.5 Roadmap)
# 1. BOSL2 Usage
# 2. No External Vendors (no `vendor/` dir)
# 3. CERN OHL License (CERN-OHL-W-2.0 string in SCAD or LICENSE file)
# 4. is_hyperobject: true in manifest

def audit_projects(projects_dir: Path):
    results = {}
    
    if not projects_dir.exists():
        print(f"Directory {projects_dir} not found.")
        return
        
    for item in sorted(projects_dir.iterdir()):
        if not item.is_dir() or item.name.startswith("."):
            continue
            
        manifest_path = item / "project.json"
        
        project_slug = item.name
        
        # Defaults
        is_hyperobject = False
        has_vendor = (item / "vendor").exists() or (item / "vendors").exists()
        has_bosl2 = False
        has_ohl_license = False
        
        if manifest_path.exists():
            try:
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                    is_hyperobject = manifest.get("project", {}).get("hyperobject", {}).get("is_hyperobject", False)
            except Exception:
                pass
                
        # Check SCAD files for BOSL2 and License
        for scad_file in item.rglob("*.scad"):
            if "vendor" in str(scad_file):
                continue
            try:
                content = scad_file.read_text(encoding="utf-8", errors="ignore")
                if "BOSL2" in content:
                    has_bosl2 = True
                if "CERN-OHL-W-2.0" in content:
                    has_ohl_license = True
            except Exception:
                pass
                
        # Check LICENSE file
        license_path = item / "LICENSE"
        if license_path.exists():
            try:
                content = license_path.read_text(encoding="utf-8", errors="ignore")
                if "CERN OHL" in content or "CERN Open Hardware" in content or "CERN-OHL" in content:
                    has_ohl_license = True
            except:
                pass

        results[project_slug] = {
            "is_hyperobject": is_hyperobject,
            "has_vendor": has_vendor,
            "has_bosl2": has_bosl2,
            "has_ohl_license": has_ohl_license
        }
        
    # Generate Report
    total = len(results)
    compliant = 0
    non_compliant = []
    
    print("# Hyperobject Compliance Audit\n")
    print("| Project | Is Hyperobject | BOSL2 | No Vendors | CERN-OHL |\n|---|---|---|---|---|")
    for slug, data in results.items():
        # A project is compliant if it meets all standards. But let's just mark if it is explicitly marked as hyperobject.
        is_ho = "✅" if data["is_hyperobject"] else "❌"
        bosl2 = "✅" if data["has_bosl2"] else "❌"
        vendor = "❌" if data["has_vendor"] else "✅"
        ohl = "✅" if data["has_ohl_license"] else "❌"
        
        print(f"| `{slug}` | {is_ho} | {bosl2} | {vendor} | {ohl} |")
        
    print("\n## Overview")
    
    ho_projects_compliant = [s for s, d in results.items() if d["is_hyperobject"] and d["has_bosl2"] and not d["has_vendor"] and d["has_ohl_license"]]
    ho_projects_failed = [s for s, d in results.items() if d["is_hyperobject"] and not (d["has_bosl2"] and not d["has_vendor"] and d["has_ohl_license"])]
    
    print(f"Total Projects Scanned: {total}")
    print(f"Projects Marked as Hyperobject: {len([s for s, d in results.items() if d['is_hyperobject']])}")
    print(f"Fully Compliant Hyperobjects: {len(ho_projects_compliant)}")
    print(f"Failing Hyperobjects: {len(ho_projects_failed)}")
    
    if ho_projects_failed:
        print("\nFailing issues in declared Hyperobjects:")
        for slug in ho_projects_failed:
            issues = []
            d = results[slug]
            if not d["has_bosl2"]:
                issues.append("Missing BOSL2")
            if d["has_vendor"]:
                issues.append("Contains `vendor/`")
            if not d["has_ohl_license"]:
                issues.append("Missing CERN-OHL-W-2.0 License")
            print(f"- `{slug}`: {', '.join(issues)}")

if __name__ == "__main__":
    audit_projects(Path(__file__).parent.parent / "projects")
