"""STL to GLB format conversion using trimesh."""

import logging

import trimesh

logger = logging.getLogger(__name__)


def stl_to_glb(stl_path: str, glb_path: str) -> bool:
    """Convert an STL file to binary GLB using trimesh.

    Returns True on success, False on failure.
    The original STL is preserved on disk for download/export.
    """
    try:
        mesh = trimesh.load(stl_path, file_type="stl")
        mesh.export(glb_path, file_type="glb")
        return True
    except Exception as e:
        logger.warning("STL→GLB conversion failed for %s: %s", stl_path, e)
        return False
