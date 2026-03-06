"""Mesh format conversion using trimesh."""

import logging

import trimesh

logger = logging.getLogger(__name__)

TRIMESH_EXPORT_FORMATS = {'stl', 'glb', 'gltf', '3mf', 'off', 'obj', 'ply'}


def convert_mesh(input_path: str, output_path: str, input_type: str = None, output_type: str = None) -> bool:
    """Convert between any trimesh-supported mesh formats.

    Returns True on success, False on failure.
    """
    try:
        in_type = input_type or input_path.rsplit('.', 1)[-1].lower()
        out_type = output_type or output_path.rsplit('.', 1)[-1].lower()
        if out_type not in TRIMESH_EXPORT_FORMATS:
            logger.warning("Unsupported output format: %s", out_type)
            return False
        mesh = trimesh.load(input_path, file_type=in_type)
        mesh.export(output_path, file_type=out_type)
        return True
    except Exception as e:
        logger.warning("Mesh conversion %s->%s failed: %s", in_type, out_type, e)
        return False


def stl_to_glb(stl_path: str, glb_path: str) -> bool:
    """Convert an STL file to binary GLB using trimesh.

    Returns True on success, False on failure.
    The original STL is preserved on disk for download/export.
    """
    return convert_mesh(stl_path, glb_path, input_type="stl", output_type="glb")
