import os
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AppConfig:
    """Application configuration with environment variable support."""

    # Paths
    BASE_DIR: Path = field(default_factory=lambda: Path(__file__).parent)
    
    _default_scad: Path = field(init=False)
    SCAD_DIR: Path = field(init=False)
    
    _default_projects: Path = field(init=False)
    PROJECTS_DIR: Path = field(init=False)
    
    _default_libs: Path = field(init=False)
    LIBS_DIR: Path = field(init=False)
    _dotscad_src: Path = field(init=False)
    OPENSCADPATH: str = field(init=False)
    
    MULTI_PROJECT: bool = field(init=False)
    
    STATIC_DIR: Path = field(init=False)
    
    _default_verify: Path = field(init=False)
    VERIFY_SCRIPT: Path = field(init=False)

    # Server
    DEBUG: bool = field(default_factory=lambda: os.getenv("FLASK_DEBUG", "false").lower() == "true")
    PORT: int = field(default_factory=lambda: int(os.getenv("PORT", 5000)))
    HOST: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))

    # OpenSCAD
    OPENSCAD_PATH: str = field(default_factory=lambda: os.getenv(
        "OPENSCAD_PATH",
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    ))

    STL_PREFIX: str = "preview_"

    # Janua Auth
    JANUA_ISSUER: str = field(default_factory=lambda: os.getenv("JANUA_ISSUER", "https://auth.madfam.io"))
    JANUA_JWKS_URL: str = field(init=False)
    JANUA_AUDIENCE: str = field(default_factory=lambda: os.getenv("JANUA_AUDIENCE", "yantra4d"))
    AUTH_ENABLED: bool = field(default_factory=lambda: os.getenv("AUTH_ENABLED", "true").lower() == "true")

    # Tiers
    TIERS_FILE: Path = field(init=False)

    # GitHub Import
    GITHUB_IMPORT_ENABLED: bool = field(default_factory=lambda: os.getenv("GITHUB_IMPORT_ENABLED", "true").lower() == "true")

    # AI
    AI_PROVIDER: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "anthropic"))
    AI_API_KEY: str = field(default_factory=lambda: os.getenv("AI_API_KEY", ""))
    AI_MODEL: str = field(default_factory=lambda: os.getenv("AI_MODEL", ""))
    AI_MAX_TOKENS: int = field(default_factory=lambda: int(os.getenv("AI_MAX_TOKENS", "2048")))

    # Janua API
    JANUA_API_URL: str = field(init=False)
    JANUA_API_KEY: str = field(default_factory=lambda: os.getenv("JANUA_API_KEY", ""))

    def __post_init__(self):
        # Initialize paths and computed fields
        parent = self.BASE_DIR.parent.parent
        
        self._default_scad = parent / "projects" / "gridfinity"
        self.SCAD_DIR = Path(os.getenv("SCAD_DIR", self._default_scad))

        self._default_projects = parent / "projects"
        self.PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", self._default_projects))

        self._default_libs = parent / "libs"
        self.LIBS_DIR = Path(os.getenv("LIBS_DIR", self._default_libs))
        self._dotscad_src = self._default_libs / "dotSCAD" / "src"
        self.OPENSCADPATH = os.getenv(
            "OPENSCADPATH",
            os.pathsep.join([str(self.LIBS_DIR), str(self._dotscad_src), str(self.PROJECTS_DIR)])
        )

        self.MULTI_PROJECT = os.getenv("PROJECTS_DIR") is not None or self._default_projects.is_dir()

        self.STATIC_DIR = self.BASE_DIR / "static"

        self._default_verify = self.BASE_DIR / "tests" / "verify_design.py"
        self.VERIFY_SCRIPT = Path(os.getenv("VERIFY_SCRIPT", self._default_verify))
        
        self.JANUA_JWKS_URL = os.getenv("JANUA_JWKS_URL", f"{self.JANUA_ISSUER}/.well-known/jwks.json")
        self.TIERS_FILE = Path(os.getenv("TIERS_FILE", self.BASE_DIR / "tiers.json"))
        self.JANUA_API_URL = os.getenv("JANUA_API_URL", f"{self.JANUA_ISSUER}/api/v1")

    # --- Manifest-delegated accessors (backward compat) ---
    # These are kept as instance methods now, but clients calling Config.method() will still work
    # if Config is an instance.

    def get_allowed_files(self):
        from manifest import get_manifest
        return get_manifest().get_allowed_files()

    def get_parts_map(self):
        from manifest import get_manifest
        return get_manifest().get_parts_map()

    def get_mode_map(self):
        from manifest import get_manifest
        return get_manifest().get_mode_map()

    def get_estimate_constants(self):
        from manifest import get_manifest
        return get_manifest().estimate_constants

# Create global instance
Config = AppConfig()
