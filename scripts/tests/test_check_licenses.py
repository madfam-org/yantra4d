"""Tests for the cartridge licensing audit.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_check_licenses.py -q

``scripts/qa/check_licenses.py --strict-all`` is a blocking step of the
``metadata-consistency`` job, and it is the lane that decides what a public
commons is allowed to ship. Three of its judgements are legal, not cosmetic:

  - a cartridge declaring CERN-OHL-W while shipping GPL is a CONFLICT — an
    upstream fork cannot be relicensed, so the declaration is simply false;
  - a LICENSE file that is a saved HTML error page means the cartridge ships no
    licence at all, which must not read as "has a LICENSE, fine";
  - a NonCommercial licence vendored BELOW the cartridge root travels with
    those files and constrains commercial use of the whole cartridge, so it is
    a CONFLICT unless it is acknowledged in ``KNOWN_NC_EXPOSURE``.

The severity ladder is the other half: ``--strict`` gates on CONFLICT only so
the metadata backlog can be worked down, ``--strict-all`` (what CI runs) gates
on MISMATCH and METADATA too, and WARNING/NESTED never gate — acknowledging an
exposure is the mechanism for keeping CI green while the catalogue surfaces it.
A test that let WARNING block would make acknowledgement useless.

All fixtures are synthetic cartridge trees in tmp_path: real licence texts are
long, and the identifier logic only ever reads the first 4 kB.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import check_licenses as lane  # noqa: E402

GPL3 = "GNU GENERAL PUBLIC LICENSE\nVersion 3, 29 June 2007\n"
CERN_W = "CERN Open Hardware Licence Version 2 - Weakly Reciprocal\n"
MIT = "MIT License\n\nPermission is hereby granted, free of charge, to any person\n"
CC_BY_NC_SA = ("Creative Commons Attribution-NonCommercial-ShareAlike 4.0 "
               "International\nNonCommercial\nShareAlike\n")
HTML_404 = "<!DOCTYPE html>\n<html><body>404 Not Found</body></html>\n"
PROPRIETARY = "Copyright 2026. All rights reserved. Uso Privado.\n"


@pytest.fixture
def commons(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    projects.mkdir()
    monkeypatch.setattr(lane, "REPO", tmp_path)
    monkeypatch.setattr(lane, "PROJECTS", projects)
    return projects


def cartridge(projects: Path, slug: str, declared=None, licenses=None,
              nested=None, field="hyperobject.commons_license") -> Path:
    directory = projects / slug
    directory.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"project": {"name": slug}}
    if declared is not None:
        if field == "hyperobject.commons_license":
            manifest["hyperobject"] = {"commons_license": declared}
        elif field == "project.license":
            manifest["project"]["license"] = declared
        else:
            manifest["license"] = declared
    (directory / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, text in (licenses or {}).items():
        (directory / name).write_text(text, encoding="utf-8")
    for rel, text in (nested or {}).items():
        path = directory / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return directory


def gitmodules(tmp_path, *slugs) -> None:
    (tmp_path / ".gitmodules").write_text("".join(
        f'[submodule "projects/{s}"]\n\tpath = projects/{s}\n'
        f"\turl = https://github.com/madfam-org/{s}.git\n" for s in slugs
    ), encoding="utf-8")


def catalogue(tmp_path, *slugs) -> None:
    path = tmp_path / "docs" / "commons-catalog.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"cartridges": [{"slug": s} for s in slugs]}),
                    encoding="utf-8")


def findings(slug=None, severity=None) -> list[dict]:
    return [f for f in lane.audit()
            if (slug is None or f["slug"] == slug)
            and (severity is None or f["severity"] == severity)]


def run(monkeypatch, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["check_licenses.py", *args])
    return lane.main()


# --- identifying what a file actually is ----------------------------------

@pytest.mark.parametrize("text,expected", [
    (GPL3, "GPL-3.0"),
    ("GNU GENERAL PUBLIC LICENSE\nVersion 2, June 1991\n", "GPL-2.0"),
    ("GNU LESSER GENERAL PUBLIC LICENSE\nVersion 3\n", "LGPL-3.0"),
    ("GNU AFFERO GENERAL PUBLIC LICENSE\nVersion 3\n", "AGPL-3.0"),
    (CERN_W, "CERN-OHL-W-2.0"),
    ("CERN Open Hardware Licence Version 2 - Strongly Reciprocal\n", "CERN-OHL-S-2.0"),
    ("CERN Open Hardware Licence Version 2 - Permissive\n", "CERN-OHL-P-2.0"),
    ("Apache License\nVersion 2.0\n", "Apache-2.0"),
    (MIT, "MIT"),
    ("BSD 3-Clause License\n", "BSD-3-Clause"),
    (PROPRIETARY, "PROPRIETARY"),
    ("some notes about this design\n", "UNKNOWN"),
])
def test_identify_reads_the_licence_out_of_the_text(tmp_path, text, expected):
    path = tmp_path / "LICENSE"
    path.write_text(text, encoding="utf-8")
    assert lane.identify(path) == expected


def test_a_saved_error_page_is_named_as_one_not_guessed_at(tmp_path):
    """"Has a LICENSE file" must not be the same sentence as "is licensed"."""
    path = tmp_path / "LICENSE"
    path.write_text(HTML_404, encoding="utf-8")
    assert lane.identify(path) == "HTML-ERROR-PAGE"


def test_creative_commons_variants_are_resolved_not_flattened_to_cc(tmp_path):
    """CC-BY and CC-BY-NC-SA differ on the only question that matters."""
    path = tmp_path / "LICENSE"
    path.write_text(CC_BY_NC_SA, encoding="utf-8")
    assert lane.identify(path) == "CC-BY-NC-SA-4.0"
    path.write_text("Creative Commons Attribution 4.0 International\n", encoding="utf-8")
    assert lane.identify(path) == "CC-BY-4.0"


def test_noncommercial_is_detected_from_the_identifier_segments():
    assert lane.is_noncommercial("CC-BY-NC-SA-4.0") is True
    assert lane.is_noncommercial("CC-BY-NC-4.0") is True
    assert lane.is_noncommercial("CC-BY-SA-4.0") is False
    assert lane.is_noncommercial("CERN-OHL-W-2.0") is False


def test_spdx_upgrade_suffixes_do_not_make_two_different_licences():
    assert lane.normalize("GPL-3.0-or-later") == "GPL-3.0"
    assert lane.normalize("GPL-3.0-only") == "GPL-3.0"
    assert lane.normalize("CERN-OHL-W-2.0") == "CERN-OHL-W-2.0"
    assert lane.normalize(None) is None


def test_an_or_later_declaration_matching_the_shipped_file_is_not_a_mismatch(commons):
    cartridge(commons, "gears", declared="GPL-3.0-or-later", licenses={"LICENSE": GPL3})
    assert findings("gears", "MISMATCH") == []
    assert findings("gears", "CONFLICT") == []


# --- the conflicts ---------------------------------------------------------

def test_declaring_cern_while_shipping_gpl_is_a_conflict(commons):
    cartridge(commons, "fork", declared="CERN-OHL-W-2.0", licenses={"LICENSE": GPL3})
    conflicts = findings("fork", "CONFLICT")
    assert len(conflicts) == 1
    assert "copyleft cannot be relicensed" in conflicts[0]["message"]


def test_declaring_the_copyleft_it_actually_ships_is_accepted(commons):
    cartridge(commons, "fork", declared="GPL-3.0", licenses={"LICENSE": GPL3})
    assert findings("fork", "CONFLICT") == []
    assert findings("fork", "MISMATCH") == []


def test_an_html_error_page_licence_is_a_conflict(commons):
    cartridge(commons, "broken", declared="CERN-OHL-W-2.0",
              licenses={"LICENSE": HTML_404})
    assert any("saved HTML error page" in f["message"]
               for f in findings("broken", "CONFLICT"))


def test_a_proprietary_licence_in_the_public_commons_is_a_conflict(commons):
    cartridge(commons, "gears", licenses={"LICENSE": PROPRIETARY})
    assert any("public commons catalogue" in f["message"]
               for f in findings("gears", "CONFLICT"))


def test_a_proprietary_licence_is_correct_for_acknowledged_client_work(commons):
    """The requirement inverts: client work is right to be all-rights-reserved."""
    slug = min(lane.CLIENT_PRIVATE)
    cartridge(commons, slug, licenses={"LICENSE": PROPRIETARY})
    assert findings(slug, "CONFLICT") == []
    assert any(f["severity"] == "OK" for f in findings(slug))


def test_client_work_appearing_in_the_published_catalogue_is_a_conflict(commons, tmp_path):
    slug = min(lane.CLIENT_PRIVATE)
    catalogue(tmp_path, slug, "gears")
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W})
    assert any("appears in the published catalogue" in f["message"]
               for f in findings(slug, "CONFLICT"))


def test_client_work_absent_from_the_catalogue_raises_nothing(commons, tmp_path):
    catalogue(tmp_path, "gears")
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W})
    assert findings(severity="CONFLICT") == []


def test_shipping_two_different_licences_is_a_conflict(commons):
    cartridge(commons, "gears", declared="MIT",
              licenses={"LICENSE": MIT, "LICENSE.gpl": GPL3})
    assert any("ships more than one license" in f["message"]
               for f in findings("gears", "CONFLICT"))


def test_a_manifest_contradicting_itself_across_fields_is_a_conflict(commons):
    directory = commons / "gears"
    directory.mkdir()
    (directory / "project.json").write_text(json.dumps({
        "project": {"name": "gears", "license": "MIT"},
        "hyperobject": {"commons_license": "CERN-OHL-W-2.0"},
    }), encoding="utf-8")
    (directory / "LICENSE").write_text(CERN_W, encoding="utf-8")
    assert any("conflicting licences in different fields" in f["message"]
               for f in findings("gears", "CONFLICT"))


def test_two_fields_agreeing_is_not_a_conflict(commons):
    directory = commons / "gears"
    directory.mkdir()
    (directory / "project.json").write_text(json.dumps({
        "project": {"name": "gears", "license": "CERN-OHL-W-2.0"},
        "hyperobject": {"commons_license": "CERN-OHL-W-2.0-or-later"},
    }), encoding="utf-8")
    (directory / "LICENSE").write_text(CERN_W, encoding="utf-8")
    assert findings("gears", "CONFLICT") == []


# --- nested third-party licences ------------------------------------------

def test_a_nested_license_file_is_found_below_the_cartridge_root(commons):
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W},
              nested={"vendor/BOSL2/LICENSE": MIT})
    nested = findings("gears", "NESTED")
    assert len(nested) == 1
    assert nested[0]["files"] == {"vendor/BOSL2/LICENSE": "MIT"}


def test_a_lowercase_nested_license_is_still_a_licence(commons):
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W},
              nested={"vendor/lib/license.txt": MIT})
    assert findings("gears", "NESTED")[0]["files"] == {"vendor/lib/license.txt": "MIT"}


def test_a_copying_file_counts_as_a_licence(commons):
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W},
              nested={"vendor/lib/COPYING": GPL3})
    assert findings("gears", "NESTED")[0]["files"] == {"vendor/lib/COPYING": "GPL-3.0"}


def test_an_unacknowledged_nested_nc_licence_is_a_conflict(commons):
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W},
              nested={"vendor/upstream/LICENSE": CC_BY_NC_SA})
    conflicts = findings("gears", "CONFLICT")
    assert len(conflicts) == 1
    assert "vendors NonCommercial-licensed files" in conflicts[0]["message"]
    assert "KNOWN_NC_EXPOSURE" in conflicts[0]["message"]  # the fix is in the message


def test_an_acknowledged_nc_exposure_is_a_warning_not_a_conflict(commons):
    slug = min(lane.KNOWN_NC_EXPOSURE)
    cartridge(commons, slug, declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W},
              nested={"vendor/upstream/LICENSE": CC_BY_NC_SA})
    assert findings(slug, "CONFLICT") == []
    warnings = findings(slug, "WARNING")
    assert len(warnings) == 1
    assert lane.KNOWN_NC_EXPOSURE[slug] in warnings[0]["message"]


def test_a_cartridge_root_licence_is_not_reported_twice_as_nested(commons):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT})
    assert findings("gears", "NESTED") == []


def test_the_nested_walk_never_reads_repository_internals(commons):
    directory = cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT})
    git = directory / ".git"
    git.mkdir()
    (git / "COPYING").write_text(GPL3, encoding="utf-8")
    assert lane.nested_license_files(directory) == {}


def test_the_nested_walk_is_depth_bounded(commons):
    directory = cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT})
    shallow = directory / "a" / "b" / "c" / "d"
    shallow.mkdir(parents=True)
    (shallow / "LICENSE").write_text(MIT, encoding="utf-8")
    deep = directory / "a" / "b" / "c" / "d" / "e"
    deep.mkdir(parents=True)
    (deep / "LICENSE").write_text(GPL3, encoding="utf-8")

    found = lane.nested_license_files(directory)
    assert "a/b/c/d/LICENSE" in found
    assert "a/b/c/d/e/LICENSE" not in found


# --- the softer severities -------------------------------------------------

def test_a_declared_cartridge_needs_no_licence_file_of_its_own(commons, tmp_path):
    """Since RFC 0038 P2 no cartridge is published as its own repo.

    They all live in madfam-org/solid-hyperobjects and are covered by its root
    LICENSE plus their own declared commons_license, so a missing LICENSE file
    is not a finding when a licence IS declared. A stale .gitmodules entry must
    not resurrect the old severity — this script no longer reads it.
    """
    gitmodules(tmp_path, "gears")
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0")
    assert findings("gears") == []


def test_an_in_repo_cartridge_needs_no_licence_file_of_its_own(commons, tmp_path):
    gitmodules(tmp_path, "elsewhere")
    cartridge(commons, "inline", declared="CERN-OHL-W-2.0")
    assert findings("inline") == []


def test_an_in_repo_cartridge_with_neither_declaration_nor_file_is_metadata(commons):
    cartridge(commons, "inline")
    assert any("declares no commons_license and ships no LICENSE file" in f["message"]
               for f in findings("inline", "METADATA"))


def test_declaring_one_licence_while_shipping_another_is_a_mismatch(commons):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": CERN_W})
    mismatches = findings("gears", "MISMATCH")
    assert len(mismatches) == 1
    assert "declares MIT but ships CERN-OHL-W-2.0" in mismatches[0]["message"]


def test_a_licence_declared_under_project_license_is_read(commons):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT},
              field="project.license")
    assert findings("gears") == []


def test_a_licence_declared_at_the_top_level_is_read(commons):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT},
              field="license")
    assert findings("gears") == []


def test_findings_are_attributed_to_the_cartridge_that_produced_them(commons):
    cartridge(commons, "aaa", declared="MIT", licenses={"LICENSE": CERN_W})
    cartridge(commons, "zzz", declared="CERN-OHL-W-2.0", licenses={"LICENSE": GPL3})
    by_slug = {f["slug"]: f["message"] for f in lane.audit()}
    assert "declares MIT" in by_slug["aaa"]
    assert "copyleft" in by_slug["zzz"]


# --- the severity ladder ---------------------------------------------------

def test_strict_gates_on_a_conflict(commons, monkeypatch):
    cartridge(commons, "fork", declared="CERN-OHL-W-2.0", licenses={"LICENSE": GPL3})
    assert run(monkeypatch, "--strict") == 1


def test_strict_does_not_gate_on_a_mismatch_alone(commons, monkeypatch):
    """The metadata backlog must not block every unrelated build."""
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": CERN_W})
    assert run(monkeypatch, "--strict") == 0


def test_strict_all_gates_on_a_mismatch(commons, monkeypatch):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": CERN_W})
    assert run(monkeypatch, "--strict-all") == 1


def test_strict_all_gates_on_a_metadata_finding(commons, monkeypatch):
    cartridge(commons, "inline")
    assert run(monkeypatch, "--strict-all") == 1


def test_strict_all_does_not_gate_on_an_acknowledged_nc_exposure(commons, monkeypatch):
    """Acknowledgement is the mechanism for staying green; blocking voids it."""
    slug = min(lane.KNOWN_NC_EXPOSURE)
    cartridge(commons, slug, declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W},
              nested={"vendor/upstream/LICENSE": CC_BY_NC_SA})
    assert run(monkeypatch, "--strict-all") == 0


def test_strict_all_does_not_gate_on_an_informational_nested_licence(commons, monkeypatch):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT},
              nested={"vendor/BOSL2/LICENSE": MIT})
    assert run(monkeypatch, "--strict-all") == 0


def test_a_clean_commons_passes_both_gates(commons, monkeypatch):
    cartridge(commons, "gears", declared="CERN-OHL-W-2.0", licenses={"LICENSE": CERN_W})
    assert run(monkeypatch, "--strict") == 0
    assert run(monkeypatch, "--strict-all") == 0


def test_the_report_prints_nested_findings_under_their_own_heading(commons, monkeypatch, capsys):
    cartridge(commons, "gears", declared="MIT", licenses={"LICENSE": MIT},
              nested={"vendor/BOSL2/LICENSE": MIT})
    run(monkeypatch)
    out = capsys.readouterr().out
    assert "Nested third-party licenses" in out
    assert "1 with nested third-party licenses" in out
