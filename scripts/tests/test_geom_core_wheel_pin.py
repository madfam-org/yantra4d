"""The geom-core wheel the API image bakes in must be one the image can install.

The mesh-oracle parity soak (docs/guides/production-checklist.md, "Mesh oracle
(geom-core)") builds the API image with GEOM_CORE_WHEEL_URL + _SHA256 from
deploy.yml. geom-core ships one wheel per CPython version and pip refuses a
wheel for another interpreter, so a cp311 wheel on the python:3.12 image fails
the deploy build. The CI differential job must test the wheel production runs.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RELEASE_URL = re.compile(
    r"^https://github\.com/madfam-org/geom-core/releases/download/v(?P<tag>[0-9][^/]*)/"
    r"geom_core-(?P<version>[^-]+)-cp(?P<py>\d+)-cp(?P=py)-(?P<platform>[a-z0-9_]+)\.whl$"
)


def _deploy_pin() -> dict[str, str]:
    workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
    build = next(s for s in workflow["jobs"]["build-backend"]["steps"] if s.get("name") == "Build and push")
    assert build["with"]["file"] == "./apps/api/Dockerfile"
    args = dict(line.strip().split("=", 1) for line in build["with"]["build-args"].splitlines() if line.strip())
    return {k: args[k] for k in ("GEOM_CORE_WHEEL_URL", "GEOM_CORE_WHEEL_SHA256")}


def _ci_job() -> dict:
    workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
    return workflow["jobs"]["mesh-oracle-differential"]


def _image_python() -> str:
    match = re.search(r"^FROM python:(\d+)\.(\d+)", (ROOT / "apps/api/Dockerfile").read_text(), re.M)
    assert match, "apps/api/Dockerfile no longer starts FROM python:X.Y"
    return match.group(1) + match.group(2)


def test_deploy_wheel_is_a_pinned_release_asset_for_the_image_interpreter():
    pin = _deploy_pin()
    match = RELEASE_URL.match(pin["GEOM_CORE_WHEEL_URL"])
    assert match, pin["GEOM_CORE_WHEEL_URL"]
    assert match["tag"] == match["version"], "release tag and wheel version disagree"
    assert match["py"] == _image_python(), (
        f"cp{match['py']} wheel on a python {_image_python()} image: pip refuses it and the deploy build fails"
    )
    assert match["platform"].endswith("x86_64"), "the production nodes are x86_64"
    assert re.fullmatch(r"[0-9a-f]{64}", pin["GEOM_CORE_WHEEL_SHA256"])


def test_ci_differential_job_tests_the_wheel_production_runs():
    job = _ci_job()
    assert job["env"]["GEOM_CORE_WHEEL_URL"] == _deploy_pin()["GEOM_CORE_WHEEL_URL"]
    assert job["env"]["GEOM_CORE_WHEEL_SHA256"] == _deploy_pin()["GEOM_CORE_WHEEL_SHA256"]
    setup = next(s for s in job["steps"] if str(s.get("uses", "")).startswith("actions/setup-python"))
    assert setup["with"]["python-version"].replace(".", "") == _image_python()
