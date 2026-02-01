import os
from pathlib import Path

class Config:
    """Application configuration with environment variable support."""

    # Paths
    BASE_DIR = Path(__file__).parent

    _default_scad = BASE_DIR.parent.parent / "projects" / "tablaco"
    SCAD_DIR = Path(os.getenv("SCAD_DIR", _default_scad))

    _default_projects = BASE_DIR.parent.parent / "projects"
    PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", _default_projects))

    _default_libs = BASE_DIR.parent.parent / "libs"
    LIBS_DIR = Path(os.getenv("LIBS_DIR", _default_libs))
    OPENSCADPATH = os.getenv("OPENSCADPATH", str(LIBS_DIR))

    MULTI_PROJECT = os.getenv("PROJECTS_DIR") is not None or _default_projects.is_dir()

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

    # Janua Auth
    JANUA_ISSUER = os.getenv("JANUA_ISSUER", "https://auth.madfam.io")
    JANUA_JWKS_URL = os.getenv("JANUA_JWKS_URL", f"{JANUA_ISSUER}/.well-known/jwks.json")
    JANUA_AUDIENCE = os.getenv("JANUA_AUDIENCE", "qubic")
    AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"

    # Tiers
    TIERS_FILE = Path(os.getenv("TIERS_FILE", BASE_DIR / "tiers.json"))

    # GitHub Import
    GITHUB_IMPORT_ENABLED = os.getenv("GITHUB_IMPORT_ENABLED", "true").lower() == "true"
    
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
