"""
Project Manifest loader.
Parses scad/project.json and provides typed accessors for modes, parts, parameters.
"""
import json
import logging
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)

_manifest_cache = None


class ProjectManifest:
    """Typed wrapper around project.json data."""

    def __init__(self, data: dict):
        self._data = data

    # --- Core accessors ---

    @property
    def project(self) -> dict:
        return self._data["project"]

    @property
    def modes(self) -> list:
        return self._data["modes"]

    @property
    def parts(self) -> list:
        return self._data["parts"]

    @property
    def parameters(self) -> list:
        return self._data["parameters"]

    @property
    def estimate_constants(self) -> dict:
        return self._data["estimate_constants"]

    # --- Derived maps ---

    def get_allowed_files(self) -> dict:
        """Returns {filename: Path} for all SCAD files referenced by modes."""
        result = {}
        for mode in self.modes:
            fname = mode["scad_file"]
            result[fname] = Config.SCAD_DIR / fname
        return result

    def get_parts_map(self) -> dict:
        """Returns {scad_filename: [part_ids]} derived from modes."""
        result = {}
        for mode in self.modes:
            result[mode["scad_file"]] = mode["parts"]
        return result

    def get_mode_map(self) -> dict:
        """Returns {part_id: render_mode_int} derived from parts."""
        return {p["id"]: p["render_mode"] for p in self.parts}

    def get_scad_file_for_mode(self, mode_id: str) -> str | None:
        """Returns the SCAD filename for a given mode id."""
        for mode in self.modes:
            if mode["id"] == mode_id:
                return mode["scad_file"]
        return None

    def get_parts_for_mode(self, mode_id: str) -> list:
        """Returns list of part ids for a given mode."""
        for mode in self.modes:
            if mode["id"] == mode_id:
                return mode["parts"]
        return []

    def calculate_estimate_units(self, mode_id: str, params: dict) -> int:
        """Evaluate the estimate formula for a mode given request params."""
        for mode in self.modes:
            if mode["id"] == mode_id:
                est = mode.get("estimate", {})
                formula = est.get("formula", "constant")
                base = est.get("base_units", 1)

                if formula == "grid":
                    rows = params.get("rows", 1)
                    cols = params.get("cols", 1)
                    return int(rows) * int(cols)
                else:
                    return int(base) if isinstance(base, (int, float)) else 1
        return 1

    def as_json(self) -> dict:
        """Return raw data for API serialization."""
        return self._data


def load_manifest() -> ProjectManifest:
    """Load and cache the project manifest from SCAD_DIR/project.json."""
    global _manifest_cache
    if _manifest_cache is not None:
        return _manifest_cache

    manifest_path = Config.SCAD_DIR / "project.json"
    logger.info(f"Loading project manifest from {manifest_path}")

    try:
        with open(manifest_path, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"Manifest not found: {manifest_path}")
        raise RuntimeError(f"Project manifest not found at {manifest_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in manifest {manifest_path}: {e}")
        raise RuntimeError(f"Project manifest contains invalid JSON: {e}")

    _manifest_cache = ProjectManifest(data)
    return _manifest_cache


def get_manifest() -> ProjectManifest:
    """Get the cached manifest (loads on first call)."""
    return load_manifest()
