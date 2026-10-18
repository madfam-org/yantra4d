"""The verifier POST /api/verify launches has to exist where every config says it is.

The route runs ``[sys.executable, Config.VERIFY_SCRIPT, <stl>]``. When the
script moved to ``tests/scripts/`` (7887c1ed) the config default, the image
``ENV`` and the dev compose env kept the old ``tests/verify_design.py``, so the
interpreter exited with "can't open file" and every part was reported as
failed. The route's own tests mock ``subprocess.run`` and could not see it;
these read the three places the path is configured and check each one lands
on the real script.
"""
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

import yaml

API_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = API_DIR.parents[1]
SCRIPT = API_DIR / "tests" / "scripts" / "verify_design.py"


def _assert_is_the_verifier(path: Path) -> None:
    assert path.is_file(), f"{path} does not exist"
    assert os.access(path, os.R_OK), f"{path} is not readable"
    # The route hands it to the interpreter, so "executable" means the
    # interpreter can run it: with no arguments it prints its usage and exits 2.
    proc = subprocess.run(
        [sys.executable, str(path)], capture_output=True, text=True, timeout=60, check=False
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "Usage: verify_design.py" in proc.stdout


def test_config_default_points_at_the_verifier(monkeypatch):
    monkeypatch.delenv("VERIFY_SCRIPT", raising=False)
    from config import AppConfig

    default = AppConfig().VERIFY_SCRIPT
    assert default.resolve() == SCRIPT.resolve()
    _assert_is_the_verifier(default)


def test_config_honours_the_env_override(monkeypatch, tmp_path):
    override = tmp_path / "custom_verify.py"
    monkeypatch.setenv("VERIFY_SCRIPT", str(override))
    from config import AppConfig

    assert AppConfig().VERIFY_SCRIPT == override


def _image_path_to_repo_path(dockerfile: Path, image_path: str) -> Path:
    """Map an absolute path inside the API image back to the repo file COPY put there."""
    workdir = PurePosixPath("/")
    copies: list[tuple[PurePosixPath, str]] = []
    for line in dockerfile.read_text().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        if parts[0] == "WORKDIR":
            workdir = workdir / parts[1]
        elif parts[0] == "COPY" and len(parts) == 3 and not parts[1].startswith("--"):
            copies.append((workdir / parts[2], parts[1]))
    target = PurePosixPath(image_path)
    for dest, src in copies:
        if src.endswith("/") and target.is_relative_to(dest):
            return REPO_ROOT / src / target.relative_to(dest)
    raise AssertionError(f"no COPY line in {dockerfile} puts anything at {image_path}")


def test_image_env_points_at_the_copied_verifier():
    dockerfile = API_DIR / "Dockerfile"
    match = re.search(r"^ENV VERIFY_SCRIPT=(\S+)$", dockerfile.read_text(), re.MULTILINE)
    assert match, "apps/api/Dockerfile no longer sets VERIFY_SCRIPT"
    repo_file = _image_path_to_repo_path(dockerfile, match.group(1))
    assert repo_file.resolve() == SCRIPT.resolve()
    _assert_is_the_verifier(repo_file)


def test_dev_compose_env_points_at_the_mounted_verifier():
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.dev.yml").read_text())
    backend = next(
        svc for svc in compose["services"].values()
        if "VERIFY_SCRIPT" in (svc.get("environment") or {})
    )
    container_path = PurePosixPath(backend["environment"]["VERIFY_SCRIPT"])
    for volume in backend.get("volumes", []):
        host, _, rest = volume.partition(":")
        mount = PurePosixPath(rest.split(":")[0])
        if host.startswith("./") and container_path.is_relative_to(mount):
            repo_file = REPO_ROOT / host / container_path.relative_to(mount)
            break
    else:
        raise AssertionError(f"no bind mount in docker-compose.dev.yml covers {container_path}")
    assert repo_file.resolve() == SCRIPT.resolve()
    _assert_is_the_verifier(repo_file)
