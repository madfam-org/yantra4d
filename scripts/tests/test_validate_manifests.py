"""Tests for the project-manifest validator's classification logic.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_validate_manifests.py -q

The point of these tests is the one thing the old validator got wrong: a
`projects/<slug>/` directory with no `project.json` used to return True, so an
uninitialised submodule was indistinguishable from a passing cartridge and 37
of them reported success while being unread. Every case below pins which of
those two a given directory is, and `parse_gitmodules` is exercised against the
repo's REAL `.gitmodules` so the client-private marker cannot drift away from
the file it describes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import validate_manifests as vm

SCHEMA = {
    "type": "object",
    "required": ["slug", "name"],
    "properties": {
        "slug": {"type": "string"},
        "name": {"type": "string"},
    },
}


def make_project(tmp_path, slug, manifest=None, raw=None):
    """Create projects/<slug>/ under tmp_path, optionally with a project.json."""
    project = tmp_path / slug
    project.mkdir(parents=True)
    if raw is not None:
        (project / "project.json").write_text(raw, encoding="utf-8")
    elif manifest is not None:
        (project / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    return project


# --- the regression this script exists for --------------------------------

def test_uninitialised_submodule_is_a_failure(tmp_path):
    project = make_project(tmp_path, "gears")
    status, message = vm.classify_project(project, SCHEMA, {"gears": {"path": "projects/gears"}})
    assert status == vm.FAILED_UNINITIALISED
    assert "gears" in message
    assert "submodule not initialised" in message


def test_uninitialised_submodule_marked_update_none_is_skipped_with_reason(tmp_path):
    project = make_project(tmp_path, "tablaco")
    status, message = vm.classify_project(
        project, SCHEMA, {"tablaco": {"path": "projects/tablaco", "update": "none"}}
    )
    assert status == vm.SKIPPED_PRIVATE
    assert "update = none" in message
    assert "client-private" in message


def test_uninitialised_submodule_is_skipped_when_allowed(tmp_path):
    project = make_project(tmp_path, "gears")
    status, message = vm.classify_project(
        project, SCHEMA, {"gears": {"path": "projects/gears"}}, allow_uninitialised=True
    )
    assert status == vm.SKIPPED_UNINITIALISED
    assert "allow-uninitialised-submodules" in message


def test_plain_directory_without_manifest_still_skips(tmp_path):
    """A non-submodule dir with no project.json is an ordinary directory."""
    project = make_project(tmp_path, "exports-scratch")
    status, _ = vm.classify_project(project, SCHEMA, {})
    assert status == vm.SKIPPED_NOT_A_PROJECT


def test_skip_validation_does_not_mask_an_unfetched_submodule(tmp_path, monkeypatch):
    """SKIP_VALIDATION waives upstream SCHEMA drift, not a missing checkout."""
    monkeypatch.setattr(vm, "SKIP_VALIDATION", {"rubiks-hyperobject"})
    project = make_project(tmp_path, "rubiks-hyperobject")
    status, _ = vm.classify_project(
        project, SCHEMA, {"rubiks-hyperobject": {"path": "projects/rubiks-hyperobject"}}
    )
    assert status == vm.FAILED_UNINITIALISED


# --- ordinary validation ---------------------------------------------------

def test_valid_manifest(tmp_path):
    project = make_project(tmp_path, "coaster", manifest={"slug": "coaster", "name": "Coaster"})
    status, _ = vm.classify_project(project, SCHEMA, {})
    assert status == vm.VALID


def test_schema_violation_fails(tmp_path):
    project = make_project(tmp_path, "coaster", manifest={"slug": "coaster"})
    status, message = vm.classify_project(project, SCHEMA, {})
    assert status == vm.FAILED_INVALID
    assert "Schema validation failed" in message


def test_malformed_json_fails(tmp_path):
    project = make_project(tmp_path, "coaster", raw="{not json")
    status, message = vm.classify_project(project, SCHEMA, {})
    assert status == vm.FAILED_INVALID
    assert "Invalid JSON" in message


def test_skip_validation_waives_schema_drift_when_checked_out(tmp_path, monkeypatch):
    monkeypatch.setattr(vm, "SKIP_VALIDATION", {"rubiks-hyperobject"})
    project = make_project(tmp_path, "rubiks-hyperobject", manifest={"nope": True})
    status, _ = vm.classify_project(
        project, SCHEMA, {"rubiks-hyperobject": {"path": "projects/rubiks-hyperobject"}}
    )
    assert status == vm.SKIPPED_UPSTREAM


# --- .gitmodules parsing ---------------------------------------------------

def test_parse_gitmodules_handles_tab_indented_keys(tmp_path):
    (tmp_path / ".gitmodules").write_text(
        '[submodule "projects/gears"]\n'
        "\tpath = projects/gears\n"
        "\turl = https://example.invalid/gears.git\n"
        '[submodule "projects/tablaco"]\n'
        "\tpath = projects/tablaco\n"
        "\turl = https://example.invalid/tablaco.git\n"
        "\tupdate = none\n",
        encoding="utf-8",
    )
    subs = vm.parse_gitmodules(tmp_path / ".gitmodules")
    assert subs["projects/gears"]["url"] == "https://example.invalid/gears.git"
    assert "update" not in subs["projects/gears"]
    assert subs["projects/tablaco"]["update"] == "none"


def test_parse_gitmodules_missing_file_is_not_an_error(tmp_path):
    assert vm.parse_gitmodules(tmp_path / "nope") == {}


def test_submodule_paths_under_projects_ignores_libs():
    registered = vm.submodule_paths_under_projects(
        {
            "libs/BOSL2": {"path": "libs/BOSL2"},
            "projects/gears": {"path": "projects/gears"},
            "projects/nested/deep": {"path": "projects/nested/deep"},
        }
    )
    assert set(registered) == {"gears"}


def test_real_gitmodules_registers_the_commons_as_one_submodule():
    """Pins the real file the ratchet reads, not a fixture (RFC 0038 P2)."""
    subs = vm.parse_gitmodules()
    assert vm.COMMONS_SUBMODULE_PATH in subs
    assert subs[vm.COMMONS_SUBMODULE_PATH]["url"].endswith("solid-hyperobjects.git")
    # No per-cartridge gitlinks under projects/ any more.
    assert vm.submodule_paths_under_projects(subs) == {}


def test_real_gitmodules_mounts_the_private_cartridges_off_the_commons():
    """They must NOT be under projects/, and must stay `update = none`."""
    subs = vm.parse_gitmodules()
    private = {p: c for p, c in subs.items() if p.startswith("private-projects/")}
    assert set(private) == {"private-projects/tablaco", "private-projects/tablaco-v2"}
    assert all(c.get("update") == "none" for c in private.values())


def test_the_commons_ratchet_fires_on_an_empty_commons(tmp_path):
    """An uninitialised commons is a failure, not a silently-green skip."""
    subs = {vm.COMMONS_SUBMODULE_PATH: {"path": vm.COMMONS_SUBMODULE_PATH}}
    empty = tmp_path / "projects"
    empty.mkdir()
    assert vm.commons_submodule_state(subs, empty) == (True, False)

    (empty / "gears").mkdir()
    (empty / "gears" / "project.json").write_text("{}", encoding="utf-8")
    assert vm.commons_submodule_state(subs, empty) == (True, True)


def test_the_commons_ratchet_never_fires_on_the_private_mounts(tmp_path):
    """A private mount is out of the ratchet's scope by construction."""
    subs = {
        vm.COMMONS_SUBMODULE_PATH: {"path": vm.COMMONS_SUBMODULE_PATH},
        "private-projects/tablaco": {"path": "private-projects/tablaco", "update": "none"},
    }
    projects = tmp_path / "projects"
    (projects / "gears").mkdir(parents=True)
    (projects / "gears" / "project.json").write_text("{}", encoding="utf-8")
    # The private mount is absent (update = none, never fetched) and the
    # commons is healthy: nothing to report.
    assert vm.commons_submodule_state(subs, projects) == (True, True)


def test_main_fails_when_the_commons_submodule_is_uninitialised(tmp_path, monkeypatch, caplog):
    empty = tmp_path / "projects"
    empty.mkdir()
    gitmodules = tmp_path / ".gitmodules"
    gitmodules.write_text(
        '[submodule "projects"]\n'
        "\tpath = projects\n"
        "\turl = https://github.com/madfam-org/solid-hyperobjects.git\n",
        encoding="utf-8")
    monkeypatch.setattr(vm, "PROJECTS_DIR", empty)
    monkeypatch.setattr(vm, "GITMODULES_PATH", gitmodules)

    assert vm.main([]) == 1
    assert "submodule is not initialised" in caplog.text


# --- read-proof ------------------------------------------------------------

def test_main_fails_when_nothing_was_validated(tmp_path, monkeypatch):
    empty = tmp_path / "projects"
    empty.mkdir()
    monkeypatch.setattr(vm, "PROJECTS_DIR", empty)
    monkeypatch.setattr(vm, "GITMODULES_PATH", tmp_path / "nope")
    assert vm.main([]) == 1


def test_main_passes_on_a_healthy_tree(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    projects.mkdir()
    make_project(projects, "coaster", manifest={"slug": "coaster", "name": "Coaster"})
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps(SCHEMA), encoding="utf-8")
    monkeypatch.setattr(vm, "PROJECTS_DIR", projects)
    monkeypatch.setattr(vm, "SCHEMA_PATH", schema_file)
    monkeypatch.setattr(vm, "GITMODULES_PATH", tmp_path / "nope")
    assert vm.main([]) == 0


def test_main_fails_on_an_uninitialised_submodule(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    projects.mkdir()
    make_project(projects, "coaster", manifest={"slug": "coaster", "name": "Coaster"})
    make_project(projects, "gears")
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps(SCHEMA), encoding="utf-8")
    gitmodules = tmp_path / ".gitmodules"
    gitmodules.write_text(
        '[submodule "projects/gears"]\n\tpath = projects/gears\n\turl = x\n', encoding="utf-8"
    )
    monkeypatch.setattr(vm, "PROJECTS_DIR", projects)
    monkeypatch.setattr(vm, "SCHEMA_PATH", schema_file)
    monkeypatch.setattr(vm, "GITMODULES_PATH", gitmodules)
    assert vm.main([]) == 1
    # ...and the documented local escape hatch turns it green again.
    assert vm.main(["--allow-uninitialised-submodules"]) == 0


def test_env_var_sets_the_default(tmp_path, monkeypatch):
    monkeypatch.setenv("VALIDATE_MANIFESTS_ALLOW_UNINITIALISED", "1")
    assert vm.parse_args([]).allow_uninitialised_submodules is True
    monkeypatch.setenv("VALIDATE_MANIFESTS_ALLOW_UNINITIALISED", "0")
    assert vm.parse_args([]).allow_uninitialised_submodules is False
    monkeypatch.delenv("VALIDATE_MANIFESTS_ALLOW_UNINITIALISED")
    assert vm.parse_args([]).allow_uninitialised_submodules is False


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
