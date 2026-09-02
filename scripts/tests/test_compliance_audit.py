"""Tests for the hyperobject metadata consistency audit.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_compliance_audit.py -q

``scripts/qa/compliance_audit.py --strict`` is a blocking step of the
``metadata-consistency`` job. Every check it makes is a claim a cartridge makes
about itself that nothing else verifies, so the suite pins each one from both
sides: the shape that must be reported, and the neighbouring shape that must
NOT be — a false positive here is a lane that gets muted.

The two that carry the most weight:

  - ``is_hyperobject_project`` reads TWO metadata locations. A cartridge that
    declares itself in either one is subject to the whole audit; getting that
    wrong silently exempts a cartridge from every check below it.
  - the dual-engine pairing check only fires when the .py actually exists on
    disk, because a SCAD-only mode inside a hyperobject cartridge (a
    calibration gauge, say) is legitimate.

``--strict`` is the difference between a report and a gate, so the exit code is
asserted separately from the issue list.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import compliance_audit as lane  # noqa: E402

SCRIPT = REPO / "scripts" / "qa" / "compliance_audit.py"


def cartridge(projects: Path, slug: str, manifest: dict, files=(), license_text=None) -> Path:
    directory = projects / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in files:
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("// geometry\n", encoding="utf-8")
    if license_text is not None:
        (directory / "LICENSE").write_text(license_text, encoding="utf-8")
    return directory


def hyperobject(**overrides) -> dict:
    """A manifest that passes every check, as the baseline to break."""
    manifest = {
        "project": {"name": "Gears", "tags": ["hyperobject", "commons"],
                    "hyperobject": {"is_hyperobject": True}},
        "hyperobject": {"commons_license": "CERN-OHL-W-2.0",
                        "cdg_interfaces": [{"id": "bore", "parameters": ["d"]}]},
        "parameters": [{"id": "d"}],
        "export_formats": ["stl"],
        "modes": [],
    }
    manifest.update(overrides)
    return manifest


def audit(tmp_path, slug="gears", **kwargs) -> list[str]:
    projects = tmp_path / "projects"
    directory = cartridge(projects, slug, **kwargs)
    return lane.audit_project(directory, json.loads((directory / "project.json").read_text()))


# --- the clean baseline ----------------------------------------------------

def test_a_complete_hyperobject_reports_nothing(tmp_path):
    assert audit(tmp_path, manifest=hyperobject()) == []


# --- which cartridges the audit applies to --------------------------------

def test_a_hyperobject_declared_in_the_project_block_is_audited():
    assert lane.is_hyperobject_project(
        {"project": {"hyperobject": {"is_hyperobject": True}}}) is True


def test_a_hyperobject_declared_only_by_its_cdg_interfaces_is_audited():
    assert lane.is_hyperobject_project(
        {"hyperobject": {"cdg_interfaces": [{"id": "bore"}]}}) is True


def test_a_top_level_block_with_no_interfaces_does_not_make_a_hyperobject():
    assert lane.is_hyperobject_project({"hyperobject": {"domain": "mechanical"}}) is False
    assert lane.is_hyperobject_project({"hyperobject": {"cdg_interfaces": []}}) is False


def test_a_plain_cartridge_is_only_checked_for_export_formats(tmp_path):
    issues = audit(tmp_path, manifest={"project": {"name": "Plain"}})
    assert issues == ["[gears] Missing 'export_formats'"]


def test_a_plain_cartridge_needs_no_tags_no_licence_and_no_hyperobject_block(tmp_path):
    assert audit(tmp_path, manifest={"project": {"name": "Plain"},
                                     "export_formats": ["stl"]}) == []


# --- check 1: the top-level block -----------------------------------------

def test_declaring_a_hyperobject_without_the_top_level_block_is_reported(tmp_path):
    manifest = hyperobject()
    del manifest["hyperobject"]
    issues = audit(tmp_path, manifest=manifest)
    assert any("missing top-level `hyperobject` block" in i for i in issues)


# --- check 2: tag consistency ---------------------------------------------

def test_a_hyperobject_missing_the_hyperobject_tag_is_reported(tmp_path):
    manifest = hyperobject()
    manifest["project"]["tags"] = ["commons"]
    assert any("missing 'hyperobject' tag" in i for i in audit(tmp_path, manifest=manifest))


def test_a_hyperobject_missing_the_commons_tag_is_reported(tmp_path):
    manifest = hyperobject()
    manifest["project"]["tags"] = ["hyperobject"]
    assert any("missing 'commons' tag" in i for i in audit(tmp_path, manifest=manifest))


# --- check 3: CDG parameter references ------------------------------------

def test_a_cdg_interface_referencing_an_unknown_parameter_is_reported(tmp_path):
    manifest = hyperobject()
    manifest["hyperobject"]["cdg_interfaces"][0]["parameters"] = ["d", "pitch"]
    issues = audit(tmp_path, manifest=manifest)
    assert any("references unknown parameter 'pitch'" in i for i in issues)
    assert not any("'d'" in i for i in issues)


def test_a_parameter_entry_without_an_id_cannot_satisfy_a_reference(tmp_path):
    manifest = hyperobject()
    manifest["parameters"] = [{"name": "d"}]
    assert any("unknown parameter 'd'" in i for i in audit(tmp_path, manifest=manifest))


# --- check 4: export formats ----------------------------------------------

def test_an_empty_export_formats_list_counts_as_missing(tmp_path):
    manifest = hyperobject()
    manifest["export_formats"] = []
    assert any("Missing 'export_formats'" in i for i in audit(tmp_path, manifest=manifest))


# --- check 5: dual-engine mode pairing ------------------------------------

def test_a_mode_whose_py_exists_but_declares_no_cq_file_is_reported(tmp_path):
    manifest = hyperobject(modes=[{"id": "main", "scad_file": "main.scad"}])
    issues = audit(tmp_path, manifest=manifest, files=["main.scad", "main.py"])
    assert any("Mode 'main' missing 'cq_file'" in i for i in issues)


def test_a_scad_only_mode_inside_a_hyperobject_is_legitimate(tmp_path):
    """Calibration gauges ship SCAD-only modes; flagging them mutes the lane."""
    manifest = hyperobject(modes=[
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"},
        {"id": "gauge", "scad_file": "gauge.scad"},
    ])
    assert audit(tmp_path, manifest=manifest,
                 files=["main.scad", "main.py", "gauge.scad"]) == []


def test_the_pairing_check_is_silent_when_the_cartridge_ships_no_python(tmp_path):
    manifest = hyperobject(modes=[{"id": "main", "scad_file": "main.scad"}])
    assert audit(tmp_path, manifest=manifest, files=["main.scad"]) == []


def test_a_declared_cq_file_satisfies_the_pairing_check(tmp_path):
    manifest = hyperobject(modes=[
        {"id": "main", "scad_file": "main.scad", "cq_file": "main.py"}])
    assert audit(tmp_path, manifest=manifest, files=["main.scad", "main.py"]) == []


# --- check 6: vendoring and licence ---------------------------------------

def test_a_vendor_directory_is_reported(tmp_path):
    manifest = hyperobject()
    issues = audit(tmp_path, manifest=manifest, files=["vendor/BOSL2/std.scad"])
    assert any("Contains vendor/ directory" in i for i in issues)


def test_a_vendors_directory_is_reported_too(tmp_path):
    issues = audit(tmp_path, manifest=hyperobject(), files=["vendors/lib/std.scad"])
    assert any("Contains vendor/ directory" in i for i in issues)


def test_a_hyperobject_with_no_cern_licence_anywhere_is_reported(tmp_path):
    manifest = hyperobject()
    manifest["hyperobject"]["commons_license"] = "MIT"
    assert any("missing CERN-OHL license" in i for i in audit(tmp_path, manifest=manifest))


def test_a_cern_licence_file_satisfies_the_licence_check(tmp_path):
    manifest = hyperobject()
    manifest["hyperobject"]["commons_license"] = "MIT"
    issues = audit(tmp_path, manifest=manifest,
                   license_text="CERN Open Hardware Licence Version 2\n")
    assert not any("missing CERN-OHL license" in i for i in issues)


def test_a_cern_header_in_a_scad_file_satisfies_the_licence_check(tmp_path):
    manifest = hyperobject()
    manifest["hyperobject"]["commons_license"] = "MIT"
    projects = tmp_path / "projects"
    directory = cartridge(projects, "gears", manifest)
    (directory / "gears.scad").write_text("// SPDX: CERN-OHL-W-2.0\n", encoding="utf-8")
    issues = lane.audit_project(directory, manifest)
    assert not any("missing CERN-OHL license" in i for i in issues)


def test_a_cern_header_inside_vendor_does_not_licence_the_cartridge(tmp_path):
    """Upstream's licence is not the cartridge's own."""
    manifest = hyperobject()
    manifest["hyperobject"]["commons_license"] = "MIT"
    projects = tmp_path / "projects"
    directory = cartridge(projects, "gears", manifest)
    vendored = directory / "vendor" / "up.scad"
    vendored.parent.mkdir(parents=True)
    vendored.write_text("// CERN-OHL-W-2.0\n", encoding="utf-8")
    assert any("missing CERN-OHL license" in i for i in lane.audit_project(directory, manifest))


# --- the run: scanning, counting, and --strict ----------------------------

def test_a_missing_projects_directory_fails(tmp_path, capsys):
    assert lane.audit_projects(tmp_path / "absent") == 1
    assert "not found" in capsys.readouterr().out


def test_directories_without_a_manifest_are_not_counted(tmp_path, capsys):
    projects = tmp_path / "projects"
    cartridge(projects, "gears", {"project": {"name": "Gears"}, "export_formats": ["stl"]})
    (projects / "uninitialised").mkdir()
    (projects / ".cache").mkdir()
    assert lane.audit_projects(projects) == 0
    assert "Total projects scanned: 1" in capsys.readouterr().out


def test_an_unparseable_manifest_is_reported_rather_than_crashing(tmp_path, capsys):
    projects = tmp_path / "projects"
    (projects / "broken").mkdir(parents=True)
    (projects / "broken" / "project.json").write_text("{not json", encoding="utf-8")
    assert lane.audit_projects(projects, strict=True) == 1
    assert "Failed to parse manifest" in capsys.readouterr().out


def test_without_strict_a_defective_cartridge_reports_but_does_not_gate(tmp_path, capsys):
    projects = tmp_path / "projects"
    cartridge(projects, "gears", {"project": {"name": "Gears"}})
    assert lane.audit_projects(projects) == 0
    assert "Issues found: 1" in capsys.readouterr().out


def test_strict_turns_the_same_report_into_a_failure(tmp_path, capsys):
    projects = tmp_path / "projects"
    cartridge(projects, "gears", {"project": {"name": "Gears"}})
    assert lane.audit_projects(projects, strict=True) == 1
    assert "--strict" in capsys.readouterr().out


def test_strict_passes_a_clean_commons(tmp_path, capsys):
    projects = tmp_path / "projects"
    cartridge(projects, "gears", hyperobject())
    assert lane.audit_projects(projects, strict=True) == 0
    assert "Hyperobject projects: 1" in capsys.readouterr().out


def test_the_cli_exits_non_zero_under_strict(tmp_path):
    """The lane runs as `python3 scripts/qa/compliance_audit.py --strict`."""
    projects = tmp_path / "projects"
    cartridge(projects, "gears", {"project": {"name": "Gears"}})
    scratch = tmp_path / "scripts" / "qa"
    scratch.mkdir(parents=True)
    (scratch / "compliance_audit.py").write_text(
        SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

    clean = subprocess.run(
        [sys.executable, str(scratch / "compliance_audit.py")],
        capture_output=True, text=True, check=False)
    strict = subprocess.run(
        [sys.executable, str(scratch / "compliance_audit.py"), "--strict"],
        capture_output=True, text=True, check=False)

    assert clean.returncode == 0
    assert strict.returncode == 1
    assert "Missing 'export_formats'" in strict.stdout
