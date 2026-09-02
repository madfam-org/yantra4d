"""Tests for the Studio offline fallback-manifest drift gate.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_sync_fallback_manifest.py -q

``scripts/qa/sync_fallback_manifest.py --check`` is a blocking step of the
``manifest-sync`` job, which ``ci-success`` requires. What it actually decides
is narrow and worth pinning exactly:

  - the fallback must equal the gridfinity manifest MINUS
    ``project.force_backend`` — and only that key, only in that block;
  - the comparison is over parsed JSON, so reformatting the committed file is
    not drift, but any changed *value* is;
  - a missing source manifest (the classic uninitialised-submodule checkout) is
    a FAILURE with the fix in the message, never a silent pass.

Every case builds its own two-file tree in tmp_path and repoints the script's
module-level paths at it: the real gridfinity cartridge is a submodule that is
empty in a partial checkout, and a suite that needs it would skip exactly where
it matters.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import sync_fallback_manifest as lane  # noqa: E402

SOURCE_MANIFEST = {
    "project": {
        "slug": "gridfinity",
        "name": "Gridfinity",
        "force_backend": True,
    },
    "parameters": [{"id": "width", "type": "number", "default": 42}],
    "modes": [{"id": "bin", "scad_file": "bin.scad"}],
}


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """A minimal repo: projects/gridfinity/project.json + the studio fallback."""
    source = tmp_path / "projects" / "gridfinity" / "project.json"
    source.parent.mkdir(parents=True)
    source.write_text(json.dumps(SOURCE_MANIFEST, indent=2), encoding="utf-8")

    fallback = tmp_path / "apps" / "studio" / "src" / "config" / "fallback-manifest.json"
    fallback.parent.mkdir(parents=True)

    monkeypatch.setattr(lane, "REPO", tmp_path)
    monkeypatch.setattr(lane, "SOURCE", source)
    monkeypatch.setattr(lane, "FALLBACK", fallback)
    return source, fallback


def run(monkeypatch, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["sync_fallback_manifest.py", *args])
    return lane.main()


# --- what the fallback is defined to be -----------------------------------

def test_expected_drops_force_backend_and_nothing_else(tree):
    want = lane.expected()
    assert "force_backend" not in want["project"]
    assert want["project"] == {"slug": "gridfinity", "name": "Gridfinity"}
    assert want["parameters"] == SOURCE_MANIFEST["parameters"]
    assert want["modes"] == SOURCE_MANIFEST["modes"]


def test_expected_leaves_a_source_without_force_backend_untouched(tree, monkeypatch):
    source, _ = tree
    plain = {"project": {"slug": "gridfinity"}, "parameters": []}
    source.write_text(json.dumps(plain), encoding="utf-8")
    assert lane.expected() == plain


def test_a_force_backend_outside_the_project_block_is_not_stripped(tree, monkeypatch):
    """The key is only meaningless under `project`; elsewhere it is data."""
    source, _ = tree
    source.write_text(json.dumps({
        "project": {"slug": "gridfinity"},
        "modes": [{"id": "bin", "force_backend": True}],
    }), encoding="utf-8")
    assert lane.expected()["modes"][0]["force_backend"] is True


# --- the drift gate --------------------------------------------------------

def test_check_passes_when_the_fallback_matches(tree, monkeypatch, capsys):
    _, fallback = tree
    fallback.write_text(json.dumps(lane.expected(), indent=2) + "\n", encoding="utf-8")
    assert run(monkeypatch, "--check") == 0
    assert "in sync" in capsys.readouterr().out


def test_check_fails_when_the_fallback_still_carries_force_backend(tree, monkeypatch, capsys):
    _, fallback = tree
    fallback.write_text(json.dumps(SOURCE_MANIFEST, indent=2) + "\n", encoding="utf-8")
    assert run(monkeypatch, "--check") == 1
    out = capsys.readouterr().out
    assert "out of sync" in out
    assert "sync_fallback_manifest.py" in out  # the fix is in the message


def test_check_fails_when_a_parameter_value_drifted(tree, monkeypatch):
    _, fallback = tree
    want = lane.expected()
    want["parameters"][0]["default"] = 43
    fallback.write_text(json.dumps(want, indent=2) + "\n", encoding="utf-8")
    assert run(monkeypatch, "--check") == 1


def test_check_fails_when_the_fallback_is_absent(tree, monkeypatch):
    assert not tree[1].exists()
    assert run(monkeypatch, "--check") == 1


def test_check_compares_values_not_bytes(tree, monkeypatch):
    """Reformatting the committed file is not drift — only its content is."""
    _, fallback = tree
    fallback.write_text(
        json.dumps(lane.expected(), indent=8, sort_keys=True), encoding="utf-8")
    assert run(monkeypatch, "--check") == 0


# --- fail-closed on a partial checkout ------------------------------------

def test_missing_source_manifest_fails_with_the_submodule_hint(tree, monkeypatch, capsys):
    source, _ = tree
    source.unlink()
    assert run(monkeypatch, "--check") == 1
    out = capsys.readouterr().out
    assert "source manifest missing" in out
    assert "git submodule update --init" in out


def test_missing_source_fails_in_write_mode_too(tree, monkeypatch):
    """A partial checkout must not be able to overwrite the fallback."""
    source, fallback = tree
    source.unlink()
    assert run(monkeypatch) == 1
    assert not fallback.exists()


# --- the writer ------------------------------------------------------------

def test_write_mode_produces_a_file_check_then_accepts(tree, monkeypatch):
    _, fallback = tree
    assert run(monkeypatch) == 0
    assert json.loads(fallback.read_text(encoding="utf-8")) == lane.expected()
    assert run(monkeypatch, "--check") == 0


def test_write_mode_ends_the_file_with_a_newline(tree, monkeypatch):
    _, fallback = tree
    run(monkeypatch)
    assert fallback.read_text(encoding="utf-8").endswith("}\n")


def test_write_mode_preserves_non_ascii_rather_than_escaping_it(tree, monkeypatch):
    source, fallback = tree
    source.write_text(json.dumps(
        {"project": {"slug": "gridfinity", "name": "Rejilla · 42 mm"}},
        ensure_ascii=False), encoding="utf-8")
    run(monkeypatch)
    assert "Rejilla · 42 mm" in fallback.read_text(encoding="utf-8")
