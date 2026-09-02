"""Tests for the vendored commons-sandbox drift guard.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_check_sandbox_sync.py -q

``scripts/qa/check_sandbox_sync.py`` is a blocking step of the ``manifest-sync``
job. It guards a SECURITY core — the restricted-execution sandbox both this
repo's cq_runner and Fashion Cabinet's fc_runner load — so the only interesting
question is whether it can be made to pass while the bytes have moved. Every
case below is that question from a different direction:

  - a byte changed anywhere in a guarded file fails, including whitespace;
  - a missing guarded file fails rather than dropping out of the hash set;
  - a missing lock fails rather than being treated as "nothing pinned yet";
  - a lock that pins the wrong file, or pins nothing, fails;
  - ``--update`` re-pins and is the only way to make a changed core pass.

Fixtures are synthetic: the point is the guard, not the current contents of
the vendored core, which are expected to change whenever it is re-vendored.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import check_sandbox_sync as lane  # noqa: E402

CORE = "# the restricted-execution core\nBUILTINS = ('len', 'range')\n"
INIT = "from .core import BUILTINS\n"


@pytest.fixture
def vendored(tmp_path, monkeypatch):
    """A vendored package + a lock that matches it."""
    pkg = tmp_path / "commons_sandbox"
    pkg.mkdir()
    (pkg / "core.py").write_text(CORE, encoding="utf-8")
    (pkg / "__init__.py").write_text(INIT, encoding="utf-8")
    lock = tmp_path / "sandbox.lock.json"

    monkeypatch.setattr(lane, "PKG", pkg)
    monkeypatch.setattr(lane, "LOCK", lock)
    _pin(pkg, lock)
    return pkg, lock


def _pin(pkg: Path, lock: Path) -> None:
    lock.write_text(json.dumps({"hashes": {
        name: hashlib.sha256((pkg / name).read_bytes()).hexdigest()
        for name in lane.GUARDED
    }}) + "\n", encoding="utf-8")


def run(monkeypatch, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["check_sandbox_sync.py", *args])
    return lane.main()


# --- the guarded set -------------------------------------------------------

def test_the_guarded_set_is_the_security_core(vendored):
    """Both files are load-bearing: __init__ decides what core.py exports."""
    assert set(lane.GUARDED) == {"core.py", "__init__.py"}


def test_a_matching_checkout_passes(vendored, monkeypatch, capsys):
    assert run(monkeypatch) == 0
    assert "mismatches=0" in capsys.readouterr().out


# --- drift is drift, however small ----------------------------------------

def test_a_changed_core_fails(vendored, monkeypatch, capsys):
    pkg, _ = vendored
    (pkg / "core.py").write_text(CORE + "BUILTINS += ('open',)\n", encoding="utf-8")
    assert run(monkeypatch) == 1
    out = capsys.readouterr().out
    assert "mismatches=1" in out
    assert "core.py" in out
    assert "re-vendor from fashion-cabinet" in out


def test_a_changed_init_fails(vendored, monkeypatch, capsys):
    pkg, _ = vendored
    (pkg / "__init__.py").write_text(INIT + "from .core import *\n", encoding="utf-8")
    assert run(monkeypatch) == 1
    assert "__init__.py" in capsys.readouterr().out


def test_a_whitespace_only_change_still_fails(vendored, monkeypatch):
    """Hashes are over bytes: there is no 'cosmetic' edit to a security core."""
    pkg, _ = vendored
    (pkg / "core.py").write_text(CORE + "\n", encoding="utf-8")
    assert run(monkeypatch) == 1


def test_both_files_drifting_are_both_reported(vendored, monkeypatch, capsys):
    pkg, _ = vendored
    (pkg / "core.py").write_text("x = 1\n", encoding="utf-8")
    (pkg / "__init__.py").write_text("y = 2\n", encoding="utf-8")
    assert run(monkeypatch) == 1
    assert "mismatches=2" in capsys.readouterr().out


# --- read-proof / fail-closed ---------------------------------------------

def test_a_missing_guarded_file_fails_instead_of_shrinking_the_hash_set(
        vendored, monkeypatch, capsys):
    pkg, _ = vendored
    (pkg / "core.py").unlink()
    assert run(monkeypatch) == 1
    assert "vendored core missing: core.py" in capsys.readouterr().out


def test_a_missing_lock_fails_rather_than_pinning_nothing(vendored, monkeypatch, capsys):
    _, lock = vendored
    lock.unlink()
    assert run(monkeypatch) == 1
    out = capsys.readouterr().out
    assert "missing" in out
    assert "--update" in out


def test_a_lock_with_no_hashes_block_fails(vendored, monkeypatch):
    _, lock = vendored
    lock.write_text(json.dumps({"_comment": "re-pin me"}) + "\n", encoding="utf-8")
    assert run(monkeypatch) == 1


def test_a_lock_pinning_only_one_file_fails_on_the_other(vendored, monkeypatch, capsys):
    pkg, lock = vendored
    lock.write_text(json.dumps({"hashes": {
        "core.py": hashlib.sha256((pkg / "core.py").read_bytes()).hexdigest(),
    }}) + "\n", encoding="utf-8")
    assert run(monkeypatch) == 1
    out = capsys.readouterr().out
    assert "mismatches=1" in out
    assert "__init__.py" in out


# --- re-pinning ------------------------------------------------------------

def test_update_repins_and_only_then_does_the_check_pass(vendored, monkeypatch):
    pkg, _lock = vendored
    (pkg / "core.py").write_text("BUILTINS = ()\n", encoding="utf-8")
    assert run(monkeypatch) == 1
    assert run(monkeypatch, "--update") == 0
    assert run(monkeypatch) == 0


def test_update_writes_every_guarded_hash_and_says_where_the_source_is(
        vendored, monkeypatch):
    pkg, lock = vendored
    lock.unlink()
    assert run(monkeypatch, "--update") == 0
    written = json.loads(lock.read_text(encoding="utf-8"))
    assert set(written["hashes"]) == set(lane.GUARDED)
    assert written["hashes"]["core.py"] == hashlib.sha256(
        (pkg / "core.py").read_bytes()).hexdigest()
    assert "fashion-cabinet" in written["_comment"]


def test_update_refuses_to_pin_a_missing_file(vendored, monkeypatch):
    """--update must not be a way to drop a guarded file from the lock."""
    pkg, lock = vendored
    (pkg / "__init__.py").unlink()
    assert run(monkeypatch, "--update") == 1
    assert set(json.loads(lock.read_text(encoding="utf-8"))["hashes"]) == set(lane.GUARDED)


# --- the real vendored copy ------------------------------------------------

def test_the_committed_core_matches_the_committed_lock():
    """The same assertion CI makes, against the real files in this repo."""
    if not lane.LOCK.exists() or not (lane.PKG / "core.py").is_file():
        pytest.skip("packages/commons-sandbox is not present in this checkout")
    locked = json.loads(lane.LOCK.read_text(encoding="utf-8"))["hashes"]
    assert locked == lane._current()
