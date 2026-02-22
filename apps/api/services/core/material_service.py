"""
Material Service

Handles discovering and parsing material.json definitions.
"""
import json
import logging
from pathlib import Path


logger = logging.getLogger(__name__)

# Cache of all discovered material dictionaries
_materials_cache = None


def get_materials_dir() -> Path:
    """Get the absolute path to the materials directory."""
    # Assuming config defines ROOT_DIR or PROJECTS_DIR.
    # We will derive the materials dir similarly based on the project structure.
    # yantra4d/apps/api is the CWD, materials is ../../materials
    base = Path(__file__).parent.parent.parent.parent.parent
    mat_dir = base / "materials"
    return mat_dir.resolve()


def discover_materials(force_refresh=False):
    """
    Scan the materials directory for material.json files.
    Returns a list of parsed JSON objects.
    """
    global _materials_cache

    if not force_refresh and _materials_cache is not None:
        return _materials_cache

    materials = []
    mat_dir = get_materials_dir()
    
    if not mat_dir.exists() or not mat_dir.is_dir():
        logger.warning(f"Materials directory not found at {mat_dir}")
        return materials

    for child in mat_dir.iterdir():
        if not child.is_dir():
            continue
            
        manifest_path = child / "material.json"
        if manifest_path.exists() and manifest_path.is_file():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    materials.append(data)
            except Exception as e:
                logger.error(f"Failed to parse material.json in {child.name}: {e}")
                
    _materials_cache = materials
    return materials


def get_material(slug: str):
    """Retrieve a specific material by its slug."""
    materials = discover_materials()
    for mat in materials:
        mat_def = mat.get("material", {})
        if mat_def.get("slug") == slug:
            return mat
            
    raise RuntimeError(f"Material manifest '{slug}' not found.")
