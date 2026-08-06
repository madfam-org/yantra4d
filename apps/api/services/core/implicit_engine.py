import json
import logging

import numpy as np
import trimesh
from skimage.measure import marching_cubes

logger = logging.getLogger(__name__)

def evaluate_tpms_field(topology, X, Y, Z, frequency):
    """Evaluates the mathematical scalar field for a given TPMS topology."""
    if topology == "gyroid":
        return np.sin(X * frequency) * np.cos(Y * frequency) + \
               np.sin(Y * frequency) * np.cos(Z * frequency) + \
               np.sin(Z * frequency) * np.cos(X * frequency)
    elif topology == "diamond":
        return np.sin(X * frequency) * np.sin(Y * frequency) * np.sin(Z * frequency) + \
               np.sin(X * frequency) * np.cos(Y * frequency) * np.cos(Z * frequency) + \
               np.cos(X * frequency) * np.sin(Y * frequency) * np.cos(Z * frequency) + \
               np.cos(X * frequency) * np.cos(Y * frequency) * np.sin(Z * frequency)
    elif topology == "schwarz_p":
        return np.cos(X * frequency) + np.cos(Y * frequency) + np.cos(Z * frequency)
    else:
        # Default fallback to gyroid
        return np.sin(X * frequency) * np.cos(Y * frequency) + \
               np.sin(Y * frequency) * np.cos(Z * frequency) + \
               np.sin(Z * frequency) * np.cos(X * frequency)

def run_render(output_path: str, config: dict, params: dict):
    """
    Generate an implicit mesh using Numpy and Marching Cubes.
    Saves the final generated mesh directly to output_path.
    """
    try:
        # 1. Parse configuration
        topology = config.get("topology", "gyroid")
        base_frequency = float(config.get("base_frequency", 5.0))
        resolution = int(config.get("resolution", 64))  # Voxels per dimension
        size = float(config.get("size", 20.0)) # Domain physical size
        
        # Override with UI Parameters
        top_idx = int(params.get("topology_type", 0))
        if top_idx == 1:
            topology = "diamond"
        elif top_idx == 2:
            topology = "schwarz_p"
        else:
            topology = "gyroid"
            
        base_frequency = float(params.get("frequency", base_frequency))
        
        # 2. Extract material intelligence multipliers
        tda_euler = params.get("tda_euler_characteristic")
        mat_shrink = params.get("mat_shrinkage_x", 1.0)
        
        # Basic heuristic: if material has negative euler characteristic (highly porous),
        # we natively increase the field density to reflect its physical tendency.
        frequency = base_frequency
        if tda_euler is not None:
            # Shift frequency depending on topology complexity. 
            # -420 / 100 -> +4 frequency modifier
            frequency += abs(float(tda_euler)) / 100.0

        # Extract Thermodynamic parameters
        sim_energy = float(params.get("simulated_energy", 0.0))
        t_g = float(params.get("thermo_glass_transition_temp", 999.0)) # Default high

        # Create localized bounds applying material shrinkage
        domain_size = size * float(mat_shrink)

        logger.info(f"Generating Implicit Field '{topology}' (Freq: {frequency:.2f}, Res: {resolution}^3)")

        # 3. Discretize spatial volume
        x = np.linspace(-domain_size, domain_size, resolution)
        y = np.linspace(-domain_size, domain_size, resolution)
        z = np.linspace(-domain_size, domain_size, resolution)
        
        # 4. Thermodynamic Collapse (Digital Twin Phase Shift)
        # If simulated energy (e.g. Temperature) exceeds the Glass Transition limit,
        # the material begins to fail structurally under its own weight (sag along Z).
        if sim_energy >= t_g:
            # Calculate degradation: 1.0 (normal) down to 0.1 (pancaked)
            # as energy scales past Tg.
            overage = sim_energy - t_g
            degradation_factor = max(0.1, 1.0 - (overage * 0.05))
            
            logger.info(f"Target Material exceeded Tg! ({sim_energy} >= {t_g}) -> Structural scaling Z by {degradation_factor:.2f}")
            z = z * degradation_factor
            
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')

        # 5. Evaluate Mathematical Field
        volume = evaluate_tpms_field(topology, X, Y, Z, frequency)

        # 5. Extract Zero-Level Set (Isosurface)
        # Use level=0.0 to find the boundary
        verts, faces, _normals, _values = marching_cubes(volume, level=0.0, spacing=(
            (2*domain_size)/resolution,
            (2*domain_size)/resolution,
            (2*domain_size)/resolution)
        )
        
        # Center vertices
        verts -= domain_size

        # 6. Export Mesh
        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=True)
        
        ext = output_path.split('.')[-1].lower()
        if ext == 'stl':
            mesh.export(output_path)
        elif ext in ('glb', 'gltf'):
            mesh.export(output_path, file_type='glb')
        else:
            mesh.export(output_path)

        return True, ""
    except Exception as e:
        logger.exception("Implicit Engine Failed")
        return False, str(e)

def stream_render(output_path: str, config: dict, params: dict, part_name: str, base_prog: float, weight: float, idx: int, total: int):
    """
    Yields SSE-compatible strings simulating progress, then executes the render.
    """
    yield json.dumps({"event": "progress", "progress": base_prog + weight * 0.1, "part": part_name})
    yield json.dumps({"event": "log", "data": f"Initializing {config.get('topology', 'gyroid')} SDF computation..."})
    
    success, err = run_render(output_path, config, params)
    
    yield json.dumps({"event": "progress", "progress": base_prog + weight * 0.9, "part": part_name})
    if success:
        yield json.dumps({"event": "part_done", "part": part_name, "progress": base_prog + weight, "part_index": idx, "total_parts": total})
    else:
        yield json.dumps({"event": "error", "data": err})
