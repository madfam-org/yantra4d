"""Tests for the render-environment parity guard.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_check_render_env.py -q

``scripts/qa/check_render_env.py`` compares apps/api/Dockerfile's render
environment against ``y4d_spec.render_environment``. Two things make it worth
pinning carefully:

  - It is INACTIVE today, on purpose. The module lands with lane L-G31 and is
    not in the pinned spec (v0.1.1), so the check exits 0 with a line saying
    so. A guard that is inactive by design and a guard that is broken look
    identical from a green CI log, so the tests below assert the difference:
    a MISSING ``render_environment`` stands down, and any other ImportError
    propagates rather than being swallowed as "too old".

  - Its Dockerfile parsing is deliberately literal rather than a shell parser.
    The cases below are the shapes that literalism has to get right: flags and
    line continuations dropped, the ``&&`` that ends the install respected so
    the chained wget/sha256sum/ln are not mistaken for packages.

The fixtures are synthetic — a fake Dockerfile and a fake module — because the
real values are expected to move whenever the image or the spec is bumped, and
a test that had to be edited on every bump would be deleted on the second one.
The one exception is a single case against the REAL Dockerfile, which pins the
parser against the file it actually has to read.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import check_render_env as lane

DOCKERFILE = """FROM python:3.12-slim

ARG OPENSCAD_VERSION=2026.02.01
ARG OPENSCAD_SHA256=deadbeef

RUN apt-get update && \\
  apt-get install -y --no-install-recommends \\
  wget \\
  fontconfig \\
  xvfb && \\
  wget -q "https://example.invalid/OpenSCAD-${OPENSCAD_VERSION}.AppImage" \\
  -O /tmp/openscad.AppImage && \\
  echo "${OPENSCAD_SHA256}  /tmp/openscad.AppImage" | sha256sum -c - && \\
  rm -rf /var/lib/apt/lists/*
"""


def spec_module(packages=("wget", "fontconfig", "xvfb"),
                version="2026.02.01", sha="deadbeef"):
    """A stand-in for y4d_spec.render_environment."""
    m = types.SimpleNamespace()
    m.APT_PACKAGES = tuple(packages)
    m.OPENSCAD_VERSION = version
    m.OPENSCAD_SHA256 = sha
    return m


# ──────────────────────────────────────────────────────────────────────────────
# reading the Dockerfile
# ──────────────────────────────────────────────────────────────────────────────

def test_the_apt_list_is_read_without_its_flags():
    assert lane.parse_apt_packages(DOCKERFILE) == {"wget", "fontconfig", "xvfb"}


def test_the_chained_commands_after_the_install_are_not_packages():
    """`&&` ends the install; wget/sha256sum/rm ride the same RUN."""
    packages = lane.parse_apt_packages(DOCKERFILE)
    assert "sha256sum" not in packages
    assert "rm" not in packages
    assert "-O" not in packages


def test_a_dockerfile_with_no_apt_install_reads_as_no_packages():
    assert lane.parse_apt_packages("FROM scratch\n") == set()


def test_the_args_are_read_by_name():
    args = lane.parse_args_block(DOCKERFILE)
    assert args["OPENSCAD_VERSION"] == "2026.02.01"
    assert args["OPENSCAD_SHA256"] == "deadbeef"


def test_the_parser_reads_the_real_dockerfile():
    """The synthetic cases are worthless if the real file has another shape."""
    text = lane.DOCKERFILE.read_text(encoding="utf-8")
    packages = lane.parse_apt_packages(text)
    args = lane.parse_args_block(text)
    assert "wget" in packages and "xvfb" in packages
    assert not any(p.startswith("-") for p in packages)
    assert args["OPENSCAD_VERSION"]
    assert len(args["OPENSCAD_SHA256"]) == 64


# ──────────────────────────────────────────────────────────────────────────────
# what counts as a disagreement
# ──────────────────────────────────────────────────────────────────────────────

def test_a_matching_environment_has_no_problems():
    assert lane.compare(spec_module(), DOCKERFILE) == []


def test_package_sets_are_compared_regardless_of_order():
    reordered = spec_module(packages=("xvfb", "wget", "fontconfig"))
    assert lane.compare(reordered, DOCKERFILE) == []


def test_a_package_only_the_spec_has_is_reported():
    problems = lane.compare(spec_module(packages=("wget", "fontconfig", "xvfb", "libgl1")),
                            DOCKERFILE)
    assert len(problems) == 1
    assert "in the spec but not in apps/api/Dockerfile" in problems[0]
    assert "libgl1" in problems[0]


def test_a_package_only_the_image_has_is_reported():
    problems = lane.compare(spec_module(packages=("wget", "fontconfig")), DOCKERFILE)
    assert len(problems) == 1
    assert "in apps/api/Dockerfile but not in the spec" in problems[0]
    assert "xvfb" in problems[0]


def test_a_different_openscad_version_is_reported():
    problems = lane.compare(spec_module(version="2026.03.01"), DOCKERFILE)
    assert len(problems) == 1
    assert "OPENSCAD_VERSION differs" in problems[0]


def test_a_nearly_right_sha_is_still_wrong():
    """The ARG is piped into `sha256sum -c`: close is a different binary."""
    problems = lane.compare(spec_module(sha="deadbeee"), DOCKERFILE)
    assert len(problems) == 1
    assert "OPENSCAD_SHA256 differs" in problems[0]


def test_a_missing_arg_is_reported_rather_than_read_as_a_match():
    problems = lane.compare(spec_module(), "FROM scratch\n")
    assert any("declares no ARG OPENSCAD_VERSION" in p for p in problems)
    assert any("declares no ARG OPENSCAD_SHA256" in p for p in problems)


def test_every_disagreement_is_reported_not_just_the_first():
    problems = lane.compare(
        spec_module(packages=("wget",), version="9.9.9", sha="0"), DOCKERFILE)
    assert len(problems) == 3


# ──────────────────────────────────────────────────────────────────────────────
# inactive-until-the-pin-bumps
# ──────────────────────────────────────────────────────────────────────────────

def test_an_absent_spec_stands_the_check_down_rather_than_failing(monkeypatch, capsys):
    monkeypatch.setattr(lane, "load_spec", lambda: (None, "No module named 'y4d_spec'"))
    assert lane.main([]) == 0
    out = capsys.readouterr().out
    assert "spec too old" in out
    assert "check inactive" in out


def test_the_real_load_stands_down_on_a_missing_render_environment():
    """Today's actual state: v0.1.1 has no render_environment."""
    spec, reason = lane.load_spec()
    if spec is not None:
        pytest.skip("the pinned spec now carries render_environment — the "
                    "check is live and the other tests cover it")
    assert reason


def test_an_unrelated_import_error_is_not_mistaken_for_an_old_spec(monkeypatch):
    """A spec that is present but BROKEN must not read as merely old."""
    def exploding_import(name, *a, **k):
        if name == "y4d_spec":
            raise ImportError("No module named 'some_dependency'",
                              name="some_dependency")
        return original(name, *a, **k)

    import builtins
    original = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", exploding_import)
    monkeypatch.delitem(sys.modules, "y4d_spec", raising=False)
    with pytest.raises(ImportError):
        lane.load_spec()


# ──────────────────────────────────────────────────────────────────────────────
# the command
# ──────────────────────────────────────────────────────────────────────────────

def test_a_matching_environment_exits_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lane, "load_spec", lambda: (spec_module(), None))
    path = tmp_path / "Dockerfile"
    path.write_text(DOCKERFILE, encoding="utf-8")
    assert lane.main(["--dockerfile", str(path)]) == 0
    assert "mismatches=0" in capsys.readouterr().out


def test_a_drifting_environment_exits_one_and_names_the_drift(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lane, "load_spec",
                        lambda: (spec_module(version="1999.01.01"), None))
    path = tmp_path / "Dockerfile"
    path.write_text(DOCKERFILE, encoding="utf-8")
    assert lane.main(["--dockerfile", str(path)]) == 1
    out = capsys.readouterr().out
    assert "OPENSCAD_VERSION differs" in out
    assert "mismatches=1" in out


def test_a_missing_dockerfile_fails_rather_than_passing_vacuously(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(lane, "load_spec", lambda: (spec_module(), None))
    assert lane.main(["--dockerfile", str(tmp_path / "nope")]) == 1
    assert "not found" in capsys.readouterr().out


def test_build_only_fetch_tools_are_not_drift(tmp_path):
    """wget/curl/ca-certificates exist to build the image, not to render."""
    class Spec:
        APT_PACKAGES = ("libgl1", "fontconfig")
        OPENSCAD_VERSION = "2026.02.13"
        OPENSCAD_SHA256 = "a" * 64

    dockerfile = (
        "ARG OPENSCAD_VERSION=2026.02.13\n"
        "ARG OPENSCAD_SHA256=" + "a" * 64 + "\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
        "  libgl1 \\\n  fontconfig \\\n  wget \\\n  ca-certificates && \\\n"
        "  wget -q https://example.invalid/openscad.AppImage\n"
    )
    assert lane.compare(Spec, dockerfile) == []

