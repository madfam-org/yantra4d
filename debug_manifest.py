import sys
import os
from pathlib import Path

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'apps/api'))

# Mock config
class Config:
    PROJECTS_DIR = Path("projects")
    SCAD_DIR = Path("projects/gridfinity")
    MULTI_PROJECT = True
    DEBUG = True

import config # noqa: E402
config.Config = Config

from manifest import ManifestService # noqa: E402

def test():
    service = ManifestService()
    try:
        manifest = service.load_manifest("glia-diagnostic")
        print(f"Loaded manifest for {manifest.slug}")
        
        mode_id = "stethoscope"
        parts = manifest.get_parts_for_mode(mode_id)
        print(f"Parts for mode '{mode_id}': {parts}")
        
        mode_map = manifest.get_mode_map()
        print(f"Mode map: {mode_map}")
        
        # params = {"diaphragm_size_mm": 44}
        # from services.openscad import validate_params
        # We need to mock get_manifest usage in validate_params if it uses the singleton
        # But for this test let's just check manifest logic directly first.
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test()
