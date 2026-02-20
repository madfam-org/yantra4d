"""
Project Manifest loader.
Parses project.json and provides typed accessors for modes, parts, parameters.
Supports multi-project mode via PROJECTS_DIR.
"""
import copy
import json
import logging
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)

_manifest_cache: dict[str, "ProjectManifest"] = {}


class ProjectManifest:
    """Typed wrapper around project.json data."""

    def __init__(self, data: dict, project_dir: Path):
        self._data = data
        self.project_dir = project_dir

    # --- Core accessors ---

    @property
    def project(self) -> dict:
        return self._data["project"]

    @property
    def slug(self) -> str:
        return self._data["project"]["slug"]

    @property
    def engine(self) -> str:
        return self._data["project"].get("engine", "openscad")

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
            result[fname] = self.project_dir / fname
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

    def get_static_stl_map(self) -> dict:
        """Returns {part_id: absolute_path} for parts with static_stl defined."""
        result = {}
        for p in self.parts:
            if "static_stl" in p and p["static_stl"]:
                result[p["id"]] = self.project_dir / p["static_stl"]
        return result

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
                base = est.get("base_units", 1)
                formula_vars = est.get("formula_vars")

                if formula_vars:
                    result = 1
                    for var in formula_vars:
                        result *= int(params.get(var, 1))
                    return result
                else:
                    return int(base) if isinstance(base, (int, float)) else 1
        return 1

    def get_verification_config(self, mode_id: str) -> dict | None:
        """Build resolved verification config for a mode, with per-part overrides."""
        raw = self._data.get("verification")
        if raw is None:
            return None  # Signal to use script defaults

        base_stages = raw["stages"]
        mode_cfg = raw.get("mode_overrides", {}).get(mode_id, {})
        enabled_stage_ids = mode_cfg.get("stages", list(base_stages.keys()))

        # Filter to enabled stages only
        stages = {}
        for sid in enabled_stage_ids:
            if sid in base_stages:
                stages[sid] = copy.deepcopy(base_stages[sid])

        # Apply mode-level overrides (dot-notation: "geometry.facet_count")
        for key, val in mode_cfg.get("overrides", {}).items():
            stage_id, check_id = key.split(".", 1)
            if stage_id in stages and check_id in stages[stage_id]["checks"]:
                stages[stage_id]["checks"][check_id].update(val)

        return {"stages": stages, "part_overrides": mode_cfg.get("part_overrides", {})}

    def as_json(self) -> dict:
        """Return raw data for API serialization."""
        return self._data


def resolve_part_config(base_config: dict, part_id: str) -> dict:
    """Apply part_overrides to base config, return config for a single part."""
    result = copy.deepcopy(base_config["stages"])
    overrides = base_config.get("part_overrides", {}).get(part_id, {})
    for key, val in overrides.items():
        stage_id, check_id = key.split(".", 1)
        if stage_id in result and check_id in result[stage_id]["checks"]:
            result[stage_id]["checks"][check_id].update(val)
    return {"stages": result}



class ManifestService:
    """Service for managing project manifests."""

    def __init__(self):
        self._manifest_cache: dict[str, "ProjectManifest"] = {}

    def discover_projects(self) -> list[dict]:
        """Scan PROJECTS_DIR for projects, return metadata list."""
        projects = []
        projects_dir = Config.PROJECTS_DIR

        if projects_dir.is_dir():
            for child in sorted(projects_dir.iterdir()):
                manifest_path = child / "project.json"
                if child.is_dir() and manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            data = json.load(f)
                        proj = data.get("project", {})
                        projects.append({
                            "slug": proj.get("slug", child.name),
                            "name": proj.get("name", child.name),
                            "version": proj.get("version", "0.0.0"),
                            "description": proj.get("description", ""),
                        })
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Skipping invalid project at {child}: {e}")

        # Fallback: single-project mode via SCAD_DIR
        if not projects:
            manifest_path = Config.SCAD_DIR / "project.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path, "r") as f:
                        data = json.load(f)
                    proj = data.get("project", {})
                    projects.append({
                        "slug": proj.get("slug", "default"),
                        "name": proj.get("name", "Default Project"),
                        "version": proj.get("version", "0.0.0"),
                        "description": proj.get("description", ""),
                    })
                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Failed to load fallback manifest: {e}")

        return projects

    def _resolve_project_dir(self, slug: str | None) -> Path:
        """Resolve the project directory for a given slug."""
        if slug:
            # Try PROJECTS_DIR first
            candidate = Config.PROJECTS_DIR / slug
            if candidate.is_dir() and (candidate / "project.json").exists():
                return candidate

        # Fallback to SCAD_DIR (single-project mode)
        return Config.SCAD_DIR

    def load_manifest(self, slug: str | None = None) -> ProjectManifest:
        """Load and cache the project manifest for a given slug."""
        project_dir = self._resolve_project_dir(slug)
        cache_key = str(project_dir)

        if cache_key in self._manifest_cache:
            return self._manifest_cache[cache_key]

        manifest_path = project_dir / "project.json"
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

        manifest = ProjectManifest(data, project_dir)
        self._manifest_cache[cache_key] = manifest
        return manifest

    def invalidate_cache(self, slug: str | None = None) -> None:
        """Remove a cached manifest so the next load_manifest() re-reads disk."""
        project_dir = self._resolve_project_dir(slug)
        self._manifest_cache.pop(str(project_dir), None)

    def get_manifest(self, slug: str | None = None) -> ProjectManifest:
        """Get the cached manifest (loads on first call)."""
        return self.load_manifest(slug)


# Singleton instance
manifest_service = ManifestService()

# --- Module-level aliases for backward compatibility ---
discover_projects = manifest_service.discover_projects
load_manifest = manifest_service.load_manifest
invalidate_cache = manifest_service.invalidate_cache
get_manifest = manifest_service.get_manifest
