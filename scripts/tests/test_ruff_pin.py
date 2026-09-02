"""The ruff pin must exist, and must be the same in both places.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_ruff_pin.py -q

``.github/workflows/ci.yml`` installed ruff unpinned, so the ``backend`` job's
rule set was whatever ruff had released by the time the job started: a ruff
release that adds a rule or changes a default fails a branch that changed
nothing, and the failure lands on whoever pushes next.
``apps/api/pyproject.toml`` pins the RULES; the pin this file guards is the
ENGINE that reads them.

A pin in two files is only a pin while the two agree, and "bump both together"
in a comment is a hope, not a mechanism. This is the mechanism. Deliberately
stdlib-and-regex only: the lane that runs scripts/tests installs jsonschema and
pytest, not PyYAML, and a guard that skipped for want of a parser would be no
guard at all.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CI = REPO / ".github" / "workflows" / "ci.yml"
DEV_REQUIREMENTS = REPO / "apps" / "api" / "requirements-dev.txt"

VERSION = r"[0-9]+(?:\.[0-9]+)*"
# `pip install "ruff==0.16.5" pip-audit`, quoted or not.
CI_PIN = re.compile(rf"""pip install\s+["']?ruff==({VERSION})["']?""")
# A requirements line, ignoring comments.
REQ_PIN = re.compile(rf"^\s*ruff==({VERSION})\s*$", re.MULTILINE)


def ci_pins() -> list[str]:
    return CI_PIN.findall(CI.read_text(encoding="utf-8"))


def requirement_pins() -> list[str]:
    return REQ_PIN.findall(DEV_REQUIREMENTS.read_text(encoding="utf-8"))


def test_ci_installs_a_pinned_ruff():
    assert ci_pins(), (
        "the backend job installs ruff without a version — the lint rule set is "
        "then whatever ruff released most recently"
    )


def test_the_api_dev_requirements_pin_ruff():
    assert requirement_pins(), (
        f"{DEV_REQUIREMENTS.relative_to(REPO)} does not pin ruff, so a developer's "
        f"ruff need not be the one CI runs"
    )


def test_ci_never_installs_ruff_unpinned():
    """A second, unpinned `pip install ruff` would quietly undo the pin."""
    unpinned = re.findall(
        r"pip install[^\n]*?(?<![\w=.-])ruff(?![\w.-]*==)", CI.read_text(encoding="utf-8"))
    assert unpinned == []


def test_both_pins_name_the_same_version():
    assert set(ci_pins()) == set(requirement_pins()), (
        f"ci.yml pins ruff {ci_pins()} but "
        f"{DEV_REQUIREMENTS.relative_to(REPO)} pins {requirement_pins()} — "
        f"bump both together"
    )


def test_the_pin_is_exact_rather_than_a_floor():
    """`>=` is not a pin: it lets the next release in on its release day."""
    text = DEV_REQUIREMENTS.read_text(encoding="utf-8")
    assert not re.search(r"^\s*ruff\s*(>=|~=|>)", text, re.MULTILINE)


def test_each_file_pins_ruff_exactly_once():
    assert len(ci_pins()) == 1
    assert len(requirement_pins()) == 1
