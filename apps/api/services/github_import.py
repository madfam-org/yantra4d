"""
GitHub import service: clone repos, find SCAD files, validate/generate manifests.
"""
import json
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)

REPO_URL_PATTERN = re.compile(
    r"^https?://github\.com/[\w.-]+/[\w.-]+(\.git)?/?$"
)


def validate_repo_url(repo_url: str) -> bool:
    """Check if repo URL matches expected GitHub pattern."""
    return bool(REPO_URL_PATTERN.match(repo_url))


def check_repo_exists(repo_url: str) -> bool:
    """Use git ls-remote to verify repo is accessible."""
    try:
        result = subprocess.run(
            ["git", "ls-remote", "--exit-code", repo_url],
            capture_output=True, timeout=15,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def clone_repo(repo_url: str, dest: Path) -> bool:
    """Shallow clone a repo to dest directory."""
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(dest)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            logger.error("git clone failed: %s", result.stderr)
            return False
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        logger.error("git clone error: %s", e)
        return False


def find_scad_files(repo_path: Path) -> list[dict]:
    """Walk repo for .scad files, return list of {path, size, name}."""
    files = []
    for p in repo_path.rglob("*.scad"):
        rel = p.relative_to(repo_path)
        # Skip hidden dirs and node_modules
        if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
            continue
        files.append({
            "path": str(rel),
            "name": p.name,
            "size": p.stat().st_size,
        })
    return sorted(files, key=lambda f: f["path"])


def check_manifest(repo_path: Path) -> dict | None:
    """Look for project.json in repo root. Return parsed dict or None."""
    manifest_path = repo_path / "project.json"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Invalid project.json in repo: %s", e)
        return None


def validate_repo(repo_url: str) -> dict:
    """Full validation pipeline: check URL, clone, find files.

    Returns dict with keys: valid, scad_files, has_manifest, manifest, error
    """
    if not validate_repo_url(repo_url):
        return {"valid": False, "error": "Invalid GitHub repository URL"}

    if not check_repo_exists(repo_url):
        return {"valid": False, "error": "Repository not found or not accessible"}

    with tempfile.TemporaryDirectory(prefix="qubic_import_") as tmpdir:
        dest = Path(tmpdir) / "repo"
        if not clone_repo(repo_url, dest):
            return {"valid": False, "error": "Failed to clone repository"}

        scad_files = find_scad_files(dest)
        if not scad_files:
            return {"valid": False, "error": "No .scad files found in repository"}

        manifest = check_manifest(dest)

        return {
            "valid": True,
            "scad_files": scad_files,
            "has_manifest": manifest is not None,
            "manifest": manifest,
        }


def import_repo(repo_url: str, slug: str, manifest: dict) -> dict:
    """Clone repo and copy SCAD files + manifest to projects/{slug}/.

    Returns dict with keys: success, slug, error
    """
    project_dir = Config.PROJECTS_DIR / slug
    if project_dir.exists():
        return {"success": False, "error": f"Project '{slug}' already exists"}

    with tempfile.TemporaryDirectory(prefix="qubic_import_") as tmpdir:
        dest = Path(tmpdir) / "repo"
        if not clone_repo(repo_url, dest):
            return {"success": False, "error": "Failed to clone repository"}

        project_dir.mkdir(parents=True)

        # Copy all .scad files preserving relative structure
        for scad in dest.rglob("*.scad"):
            rel = scad.relative_to(dest)
            if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
                continue
            target = project_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scad, target)

        # Write manifest
        with open(project_dir / "project.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Write project.meta.json for sync capability
        import datetime
        meta = {
            "source": {
                "type": "github",
                "repo_url": repo_url,
                "imported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        }
        with open(project_dir / "project.meta.json", "w") as f:
            json.dump(meta, f, indent=2)

    return {"success": True, "slug": slug}


def sync_repo(slug: str) -> dict:
    """Re-clone from stored remote and update files.

    Returns dict with keys: success, updated_files, error
    """
    project_dir = Config.PROJECTS_DIR / slug
    meta_path = project_dir / "project.meta.json"

    if not meta_path.exists():
        return {"success": False, "error": "No source metadata found for this project"}

    try:
        with open(meta_path) as f:
            meta = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"success": False, "error": "Invalid project.meta.json"}

    source = meta.get("source", {})
    if source.get("type") != "github" or not source.get("repo_url"):
        return {"success": False, "error": "Project was not imported from GitHub"}

    repo_url = source["repo_url"]

    with tempfile.TemporaryDirectory(prefix="qubic_sync_") as tmpdir:
        dest = Path(tmpdir) / "repo"
        if not clone_repo(repo_url, dest):
            return {"success": False, "error": "Failed to clone repository"}

        updated = []
        for scad in dest.rglob("*.scad"):
            rel = scad.relative_to(dest)
            if any(part.startswith(".") or part == "node_modules" for part in rel.parts):
                continue
            target = project_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(scad, target)
            updated.append(str(rel))

        # Update manifest if one exists in repo
        repo_manifest = check_manifest(dest)
        if repo_manifest:
            with open(project_dir / "project.json", "w") as f:
                json.dump(repo_manifest, f, indent=2)
            updated.append("project.json")

        # Update sync timestamp
        import datetime
        source["last_synced_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    return {"success": True, "updated_files": updated}
