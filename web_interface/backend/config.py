import os
from pathlib import Path

class Config:
    """Application configuration with environment variable support."""
    
    # Paths
    BASE_DIR = Path(__file__).parent
    SCAD_DIR = BASE_DIR.parent.parent / "scad"
    STATIC_DIR = BASE_DIR / "static"
    VERIFY_SCRIPT = BASE_DIR.parent.parent / "tests" / "verify_design.py"
    
    # Server
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # OpenSCAD
    OPENSCAD_PATH = os.getenv(
        "OPENSCAD_PATH", 
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    )
    
    # Allowed SCAD files
    ALLOWED_FILES = {
        "half_cube.scad": SCAD_DIR / "half_cube.scad",
        "assembly.scad": SCAD_DIR / "assembly.scad",
        "tablaco.scad": SCAD_DIR / "tablaco.scad"
    }
    
    # Parts configuration
    PARTS_MAP = {
        "half_cube.scad": ["main"],
        "assembly.scad": ["bottom", "top"],
        "tablaco.scad": ["bottom", "top", "rods", "stoppers"]
    }
    
    MODE_MAP = {
        "main": 0,
        "bottom": 1,
        "top": 2,
        "rods": 3,
        "stoppers": 4
    }
    
    # Render time estimation constants
    ESTIMATE_CONSTANTS = {
        "base_time": 5,
        "per_unit": 1.5,
        "fn_factor": 64,
        "per_part": 8
    }
