"""Every Vite variable the Studio image is built with must reach `npm run build`.

Vite inlines `import.meta.env.VITE_*` at build time, so a value passed as a
`--build-arg` but never declared as `ARG` (or declared but never exported as
`ENV` before `npm run build`) is silently dropped: the image builds, the flag
reads unset. The geom-core soak flips `VITE_GEOM_CORE_BROWSER` through the
repository variable STUDIO_GEOM_CORE_BROWSER (apps/studio/README.md, "Soak
plan"), so this test pins that whole path.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "apps/studio/Dockerfile"
WORKFLOW = ROOT / ".github/workflows/deploy.yml"


def _studio_build_args() -> dict[str, str]:
    workflow = yaml.safe_load(WORKFLOW.read_text())
    steps = workflow["jobs"]["build-studio"]["steps"]
    build = next(s for s in steps if s.get("name") == "Build and push")
    assert build["with"]["file"] == "./apps/studio/Dockerfile"
    args = {}
    for line in build["with"]["build-args"].splitlines():
        if line.strip():
            key, _, value = line.strip().partition("=")
            args[key] = value
    return args


def _builder_stage() -> str:
    # The builder stage (the first FROM) runs `npm run build`; the nginx stage
    # never sees these ARGs.
    return DOCKERFILE.read_text().split("\nFROM ")[1]


def _declared(stage: str) -> tuple[set[str], set[str]]:
    before_build = stage.split("RUN npm run build", 1)[0]
    args = set(re.findall(r"^ARG ([A-Z0-9_]+)", before_build, re.M))
    envs = set(re.findall(r"^ENV ([A-Z0-9_]+)=\$\{\1\}", before_build, re.M))
    return args, envs


def test_every_vite_build_arg_is_declared_and_exported_before_the_build():
    args, envs = _declared(_builder_stage())
    vite = {k for k in _studio_build_args() if k.startswith("VITE_")}
    assert vite, "deploy.yml passes no VITE_* build-args to the Studio image"
    assert vite <= args, f"build-args without ARG: {sorted(vite - args)}"
    assert vite <= envs, f"ARGs never exported as ENV before npm run build: {sorted(vite - envs)}"


def test_geom_core_flag_comes_from_the_repository_variable_and_defaults_off():
    assert _studio_build_args()["VITE_GEOM_CORE_BROWSER"] == "${{ vars.STUDIO_GEOM_CORE_BROWSER }}"
    # An empty default keeps the flag off when the variable is unset; the
    # browser code treats '' as off (src/lib/geomCoreBrowser.test.js).
    assert re.search(r"^ARG VITE_GEOM_CORE_BROWSER=$", _builder_stage(), re.M)
