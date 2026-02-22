#!/usr/bin/env python3
"""
Audit Compliance Script for Yantra4D Projects.
Enforces the 4-point compliance standard.
"""

import os
import json
import logging
import sys
from pathlib import Path

# Adjust path to import from apps.api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../apps/api')))
try:
    from manifest import ManifestService
    manifest_service = ManifestService()
except ImportError as e:
    print(f"Warning: Could not import ManifestService: {e}")
    manifest_service = None

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("audit")

PROJECTS_DIR = Path(os.path.join(os.path.dirname(__file__), '../projects')).resolve()

# Projects that MUST have an attribution block
ATTRIBUTION_REQUIRED = {
    "gridfinity",
    "stemfie",
    "multiboard"
}

# Whitelist for vendor folders (empty for now to enforce strictness)
VENDOR_WHITELIST = set()

def check_rule_1_no_absolute_or_escaped_paths(project_dir: Path) -> list:
    errors = []
    for filepath in project_dir.rglob("*"):
        if not filepath.is_file() or filepath.suffix not in [".scad", ".py"]:
            continue
            
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            continue
            
        for i, line in enumerate(lines):
            line_str = line.strip()
            # SCAD checks
            if filepath.suffix == ".scad" and (line_str.startswith("use <") or line_str.startswith("include <")):
                path_part = line_str.split("<")[1].split(">")[0]
                if path_part.startswith("/"):
                    errors.append(f"{filepath.relative_to(PROJECTS_DIR)}:{i+1} Absolute path found in include/use: {path_part}")
                elif "../" in path_part:
                    # Resolve the path relative to the file's parent
                    resolved_path = (filepath.parent / path_part).resolve()
                    # It's an error ONLY if it escapes the project_dir AND isn't in LIBS
                    if not str(resolved_path).startswith(str(project_dir)) and "libs" not in str(resolved_path):
                        errors.append(f"{filepath.relative_to(PROJECTS_DIR)}:{i+1} Escaping cross-project path found: {path_part}")
    return errors

def check_rule_2_no_vendor(project_dir: Path) -> list:
    errors = []
    vendor_dir = project_dir / "vendor"
    if vendor_dir.is_dir() and project_dir.name not in VENDOR_WHITELIST:
        errors.append(f"Vendor directory found at {vendor_dir.relative_to(PROJECTS_DIR)}")
    return errors

def check_rule_3_attribution(project_dir: Path) -> list:
    errors = []
    manifest_path = project_dir / "project.json"
    if not manifest_path.exists():
        return errors
        
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        proj = data.get("project", {})
        slug = proj.get("slug", project_dir.name)
        
        has_attribution = "attribution" in proj and isinstance(proj["attribution"], dict)
        
        if slug in ATTRIBUTION_REQUIRED and not has_attribution:
            errors.append(f"Project '{slug}' is required to have an 'attribution' block in project.json but it is missing.")
    except json.JSONDecodeError:
        pass
    
    return errors

def check_rule_4_standardization(project_dir: Path) -> list:
    errors = []
    if manifest_service:
        try:
            manifest_service._validate_manifest_strictness(
                json.loads(open(project_dir / "project.json").read()), 
                project_dir / "project.json"
            )
        except Exception as e:
            errors.append(f"Manifest validation failed: {e}")
    return errors

def main():
    if not PROJECTS_DIR.is_dir():
        logger.error(f"Projects directory not found at {PROJECTS_DIR}")
        sys.exit(1)
        
    total_projects = 0
    total_errors = 0
    
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir() or not (project_dir / "project.json").exists():
            continue
            
        total_projects += 1
        
        errors = []
        errors.extend(check_rule_1_no_absolute_or_escaped_paths(project_dir))
        errors.extend(check_rule_2_no_vendor(project_dir))
        errors.extend(check_rule_3_attribution(project_dir))
        errors.extend(check_rule_4_standardization(project_dir))
        
        if errors:
            logger.error(f"❌ {project_dir.name} failed compliance:")
            for err in errors:
                logger.error(f"   - {err}")
            total_errors += len(errors)
        else:
            logger.info(f"✅ {project_dir.name} is compliant.")
            
    if total_errors > 0:
        logger.error(f"\nAudit Failed: Found {total_errors} compliance violations across {total_projects} projects.")
        sys.exit(1)
    else:
        logger.info(f"\nAudit Passed: All {total_projects} projects are fully compliant! 🎉")
        sys.exit(0)

if __name__ == "__main__":
    main()
