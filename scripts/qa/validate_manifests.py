#!/usr/bin/env python3
"""
Validates all project manifests in projects/ against packages/schemas/project-manifest.schema.json.
usage: python3 scripts/validate_manifests.py
"""
import json
import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = ROOT_DIR / "projects"
SCHEMA_PATH = ROOT_DIR / "packages" / "schemas" / "project-manifest.schema.json"

def load_schema(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Schema not found at {path}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid schema JSON: {e}")
        return None

def validate_project(project_path, schema):
    project_slug = project_path.name
    manifest_path = project_path / "project.json"

    if not manifest_path.exists():
        logger.warning(f"No project.json found in {project_slug} (skipping)")
        return True # Not an error, just skipping non-project dirs

    try:
        import jsonschema
    except ImportError:
        logger.error("jsonschema library not installed. Please run `pip install jsonschema`")
        sys.exit(1)

    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        jsonschema.validate(instance=manifest, schema=schema)
        logger.info(f"✅ {project_slug} valid")
        return True
    except json.JSONDecodeError as e:
        logger.error(f"❌ {project_slug}: Invalid JSON in project.json - {e}")
        return False
    except jsonschema.ValidationError as e:
        logger.error(f"❌ {project_slug}: Schema validation failed - {e.message}")
        return False
    except Exception as e:
        logger.error(f"❌ {project_slug}: Unexpected error - {e}")
        return False

def main():
    if not SCHEMA_PATH.exists():
        logger.error(f"Schema file missing: {SCHEMA_PATH}")
        sys.exit(1)

    schema = load_schema(SCHEMA_PATH)
    if not schema:
        sys.exit(1)

    # Check for jsonschema
    try:
        import jsonschema
    except ImportError:
        logger.error("jsonschema library required. Installing...")
        os.system("pip install jsonschema")
        import jsonschema

    success = True
    project_dirs = [d for d in PROJECTS_DIR.iterdir() if d.is_dir()]
    project_dirs.sort()

    logger.info(f"Validating {len(project_dirs)} project directories against schema...")

    for project_dir in project_dirs:
        if not validate_project(project_dir, schema):
            success = False

    if success:
        logger.info("\nAll projects valid! ✨")
        sys.exit(0)
    else:
        logger.error("\nValidation failed for one or more projects.")
        sys.exit(1)

if __name__ == "__main__":
    main()
