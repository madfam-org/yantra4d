import os
from pathlib import Path

class Config:
    """Application configuration with environment variable support."""
    
    # Paths
    BASE_DIR = Path(__file__).parent
    
    _default_scad = BASE_DIR.parent.parent / "scad"
    SCAD_DIR = Path(os.getenv("SCAD_DIR", _default_scad))
    
    STATIC_DIR = BASE_DIR / "static"
    
    _default_verify = BASE_DIR.parent.parent / "tests" / "verify_design.py"
    VERIFY_SCRIPT = Path(os.getenv("VERIFY_SCRIPT", _default_verify))
    
    # Server
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))
    HOST = os.getenv("HOST", "0.0.0.0")
    
    # OpenSCAD
    OPENSCAD_PATH = os.getenv(
        "OPENSCAD_PATH",
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    )

    STL_PREFIX = "preview_"
    
    # --- Manifest-delegated accessors (backward compat) ---

    @staticmethod
    def get_allowed_files():
        from manifest import get_manifest
        return get_manifest().get_allowed_files()

    @staticmethod
    def get_parts_map():
        from manifest import get_manifest
        return get_manifest().get_parts_map()

    @staticmethod
    def get_mode_map():
        from manifest import get_manifest
        return get_manifest().get_mode_map()

    @staticmethod
    def get_estimate_constants():
        from manifest import get_manifest
        return get_manifest().estimate_constants
