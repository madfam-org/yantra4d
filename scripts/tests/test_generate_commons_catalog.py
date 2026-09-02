"""Tests for the Hyperobjects Commons catalog generator.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests/test_generate_commons_catalog.py -q

``scripts/qa/generate_commons_catalog.py --check`` is a blocking step of the
``manifest-sync`` job, and the artifacts it generates are PUBLISHED: the JSON
catalogue and COMMONS.md ship from a public repo. Two of its decisions are
therefore not cosmetic:

  - ``NOT_COMMONS`` — a client engagement must never acquire a catalogue entry,
    which would advertise a private repo, its name and a clone command for it.
    Exclusion is by explicit slug, because an inferred rule (no readable
    LICENSE) would include exactly the entries that must never appear.
  - ``KNOWN_NC_EXPOSURE`` — a cartridge vendoring NonCommercial upstream files
    must not be presented as cleanly commercial, so its entry carries
    ``license_exposure`` and its markdown row is daggered.

The third decision worth pinning is ``_engine_support``: a CQ-only cartridge
declares ``scad_file`` pointing at its .py source as a placeholder, so a
declared filename proves nothing and the kernel has to be resolved from what is
actually on disk. Getting that wrong misreports dual-engine counts, which the
README, COMMONS.md and the value-extraction audit all quote.

Fixtures are synthetic cartridge trees in tmp_path; the last two tests check
the committed artifacts only when the commons is actually checked out.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import generate_commons_catalog as lane  # noqa: E402


def cartridge(projects: Path, slug: str, manifest: dict, files=()) -> Path:
    directory = projects / slug
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "project.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in files:
        (directory / name).write_text("// geometry\n", encoding="utf-8")
    return directory


@pytest.fixture
def commons(tmp_path, monkeypatch):
    """An empty repo skeleton with the module's paths repointed at it."""
    projects = tmp_path / "projects"
    projects.mkdir()
    monkeypatch.setattr(lane, "REPO", tmp_path)
    monkeypatch.setattr(lane, "PROJECTS", projects)
    monkeypatch.setattr(lane, "CATALOG_JSON", tmp_path / "docs" / "commons-catalog.json")
    monkeypatch.setattr(lane, "CATALOG_MD", tmp_path / "COMMONS.md")
    monkeypatch.setattr(lane, "README_MD", tmp_path / "README.md")
    return projects


def run(monkeypatch, *args) -> int:
    monkeypatch.setattr(sys, "argv", ["generate_commons_catalog.py", *args])
    return lane.main()


def slugs(catalog: dict) -> list[str]:
    return [c["slug"] for c in catalog["cartridges"]]


# --- client-private work stays out of a published catalogue ---------------

def test_excluded_cartridges_never_get_an_entry(commons):
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    for slug in lane.CLIENT_PRIVATE:
        cartridge(commons, slug, {"project": {"name": slug}})
    assert slugs(lane.build_catalog()) == ["gears"]


def test_an_excluded_cartridge_is_not_merely_unlabelled_but_absent(commons):
    """No name, no clone command, no domain — nothing about it is published."""
    slug = min(lane.CLIENT_PRIVATE)
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    cartridge(commons, slug, {"project": {"name": "Confidential"}})
    payload = json.dumps(lane.build_catalog())
    assert slug not in payload
    assert "Confidential" not in payload


def test_every_exclusion_carries_a_stated_reason(commons):
    assert lane.CLIENT_PRIVATE == set(lane.NOT_COMMONS)
    for slug, reason in lane.NOT_COMMONS.items():
        assert reason.strip(), f"{slug} is excluded without a stated reason"


def test_the_exclusion_set_matches_the_licence_auditor():
    """Both lanes must agree, or one publishes what the other forbids."""
    sys.path.insert(0, str(REPO / "scripts" / "qa"))
    import check_licenses

    assert lane.CLIENT_PRIVATE == check_licenses.CLIENT_PRIVATE
    assert lane.NOT_COMMONS == check_licenses.NOT_COMMONS
    assert set(lane.KNOWN_NC_EXPOSURE) == set(check_licenses.KNOWN_NC_EXPOSURE)


# --- NonCommercial exposure is surfaced, never hidden ----------------------

def test_a_known_nc_cartridge_carries_license_exposure(commons):
    slug = min(lane.KNOWN_NC_EXPOSURE)
    cartridge(commons, slug, {"project": {"name": slug},
                              "hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    entry = lane.build_catalog()["cartridges"][0]
    assert entry["license_exposure"] == lane.KNOWN_NC_EXPOSURE[slug]


def test_an_ordinary_cartridge_carries_no_exposure_field(commons):
    cartridge(commons, "gears", {"project": {"name": "Gears"},
                                 "hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    assert "license_exposure" not in lane.build_catalog()["cartridges"][0]


def test_the_markdown_daggers_an_exposed_licence_and_explains_the_dagger(commons):
    slug = min(lane.KNOWN_NC_EXPOSURE)
    cartridge(commons, slug, {"project": {"name": slug},
                              "hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    markdown = lane.render_markdown(lane.build_catalog())
    assert "CERN-OHL-W-2.0 †" in markdown
    assert "NonCommercial" in markdown


def test_the_dagger_footnote_is_absent_when_nothing_is_exposed(commons):
    cartridge(commons, "gears", {"project": {"name": "Gears"},
                                 "hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    assert "†" not in lane.render_markdown(lane.build_catalog())


# --- engine resolution: files on disk, not declared filenames -------------

def test_a_declared_scad_file_that_does_not_exist_is_not_an_openscad_mode(commons):
    """CQ-only cartridges declare scad_file as a placeholder for their .py."""
    directory = cartridge(commons, "cq-only", {
        "project": {"name": "CQ only"},
        "modes": [{"id": "main", "scad_file": "main.py", "cq_file": "main.py"}],
    }, files=["main.py"])
    engines, dual = lane._engine_support(
        json.loads((directory / "project.json").read_text()), directory)
    assert engines == ["cadquery"]
    assert dual is False


def test_a_cq_file_is_inferred_from_a_scad_file_only_when_the_py_exists(commons):
    manifest = {"project": {"name": "Pair"},
                "modes": [{"id": "main", "scad_file": "main.scad"}]}
    scad_only = cartridge(commons, "scad-only", manifest, files=["main.scad"])
    assert lane._engine_support(manifest, scad_only) == (["openscad"], False)

    both = cartridge(commons, "both", manifest, files=["main.scad", "main.py"])
    assert lane._engine_support(manifest, both) == (["cadquery", "openscad"], True)


def test_dual_engine_spans_modes_rather_than_requiring_one_mode_to_hold_both(commons):
    manifest = {"project": {"name": "Split"}, "modes": [
        {"id": "legacy", "scad_file": "legacy.scad"},
        {"id": "exact", "cq_file": "exact.py"},
    ]}
    directory = cartridge(commons, "split", manifest, files=["legacy.scad", "exact.py"])
    engines, dual = lane._engine_support(manifest, directory)
    assert dual is True
    assert engines == ["cadquery", "openscad"]


def test_a_per_mode_engine_declaration_needs_real_source_behind_it(commons):
    """A mode naming an engine but shipping nothing must not inflate the count."""
    manifest = {"project": {"name": "Empty"}, "modes": [
        {"id": "ghost", "engine": "cadquery", "scad_file": "ghost.scad"},
    ]}
    directory = cartridge(commons, "ghost", manifest)
    assert lane._engine_support(manifest, directory) == (["openscad"], False)


def test_a_cartridge_declaring_no_engine_defaults_to_openscad(commons):
    directory = cartridge(commons, "bare", {"project": {"name": "Bare"}})
    assert lane._engine_support({"project": {}}, directory) == (["openscad"], False)


def test_modes_given_as_a_mapping_are_read_too(commons):
    manifest = {"project": {"name": "Mapping"},
                "modes": {"main": {"id": "main", "scad_file": "main.scad"}}}
    directory = cartridge(commons, "mapping", manifest, files=["main.scad"])
    assert lane._engine_support(manifest, directory) == (["openscad"], False)


def test_dual_engine_count_is_what_the_counts_block_reports(commons):
    cartridge(commons, "dual", {"project": {"name": "Dual"}, "modes": [
        {"id": "m", "scad_file": "m.scad"}]}, files=["m.scad", "m.py"])
    cartridge(commons, "single", {"project": {"name": "Single"}, "modes": [
        {"id": "m", "scad_file": "m.scad"}]}, files=["m.scad"])
    assert lane.build_catalog()["counts"]["dual_engine"] == 1


# --- licence and interface mapping ----------------------------------------

def test_a_licence_is_read_from_any_of_the_three_conventions(commons):
    cartridge(commons, "a", {"hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    cartridge(commons, "b", {"project": {"license": "MIT"}})
    cartridge(commons, "c", {"license": "GPL-3.0"})
    licences = {e["slug"]: e["commons_license"] for e in lane.build_catalog()["cartridges"]}
    assert licences == {"a": "CERN-OHL-W-2.0", "b": "MIT", "c": "GPL-3.0"}


def test_an_unlicensed_cartridge_is_counted_as_unlicensed(commons):
    cartridge(commons, "bare", {"project": {"name": "Bare"}})
    catalog = lane.build_catalog()
    assert catalog["cartridges"][0]["commons_license"] is None
    assert catalog["counts"]["with_commons_license"] == 0


def test_a_localised_interface_label_is_flattened_to_a_string(commons):
    cartridge(commons, "iface", {"hyperobject": {"cdg_interfaces": [
        {"id": "bore", "label": {"es": "Perforación", "en": "Bore"},
         "geometry_type": "cylinder", "standard": "ISO 286", "parameters": ["d"]},
    ]}})
    iface = lane.build_catalog()["cartridges"][0]["cdg_interfaces"][0]
    assert iface["label"] == "Bore"


def test_a_label_with_no_english_falls_back_to_the_first_translation(commons):
    cartridge(commons, "iface", {"hyperobject": {"cdg_interfaces": [
        {"id": "bore", "label": {"es": "Perforación"}, "geometry_type": "cylinder"},
    ]}})
    assert lane.build_catalog()["cartridges"][0]["cdg_interfaces"][0]["label"] == "Perforación"


def test_internal_standards_are_not_published_as_external_ones(commons):
    cartridge(commons, "iface", {"hyperobject": {"cdg_interfaces": [
        {"id": "a", "standard": "ISO 286"},
        {"id": "b", "standard": "internal"},
    ]}})
    assert lane.build_catalog()["cartridges"][0]["standards"] == ["ISO 286"]


def test_parameter_ids_are_published_alongside_the_count(commons):
    cartridge(commons, "p", {"parameters": [
        {"id": "width"}, {"id": "height"}, {"no_id": True}, "not-a-dict"]})
    entry = lane.build_catalog()["cartridges"][0]
    assert entry["parameter_ids"] == ["width", "height"]
    assert entry["parameters"] == 4


# --- clone instructions ----------------------------------------------------

def test_a_submodule_cartridge_clones_from_its_own_repo(commons, monkeypatch):
    (commons.parent / ".gitmodules").write_text(
        '[submodule "projects/gears"]\n'
        "\tpath = projects/gears\n"
        "\turl = https://github.com/madfam-org/gears.git\n", encoding="utf-8")
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    clone = lane.build_catalog()["cartridges"][0]["clone"]
    assert clone["kind"] == "submodule"
    assert clone["command"] == "git clone https://github.com/madfam-org/gears.git"


def test_an_in_repo_cartridge_gets_a_sparse_checkout_command(commons):
    cartridge(commons, "inline", {"project": {"name": "Inline"}})
    clone = lane.build_catalog()["cartridges"][0]["clone"]
    assert clone["kind"] == "sparse"
    assert "sparse-checkout set projects/inline" in clone["command"]


# --- the drift gate --------------------------------------------------------

def test_an_empty_commons_refuses_to_overwrite_the_catalogue(commons, monkeypatch, capsys):
    """A partial checkout must not be able to publish an empty catalogue."""
    assert run(monkeypatch) == 1
    assert "refusing to write an empty catalog" in capsys.readouterr().out
    assert not lane.CATALOG_JSON.exists()


def test_write_then_check_is_clean(commons, monkeypatch):
    cartridge(commons, "gears", {"project": {"name": "Gears"},
                                 "hyperobject": {"domain": "mechanical"}})
    lane.README_MD.write_text(
        f"# Yantra4D\n\n{lane.README_BEGIN}\nstale\n{lane.README_END}\n", encoding="utf-8")
    assert run(monkeypatch) == 0
    assert run(monkeypatch, "--check") == 0


def test_check_fails_when_a_cartridge_was_added_but_not_regenerated(commons, monkeypatch, capsys):
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    run(monkeypatch)
    cartridge(commons, "maze", {"project": {"name": "Maze"}})
    assert run(monkeypatch, "--check") == 1
    out = capsys.readouterr().out
    assert "stale" in out
    assert "generate_commons_catalog.py" in out  # the fix is in the message


def test_check_fails_when_only_the_markdown_was_hand_edited(commons, monkeypatch, capsys):
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    run(monkeypatch)
    lane.CATALOG_MD.write_text(
        lane.CATALOG_MD.read_text(encoding="utf-8") + "hand edit\n", encoding="utf-8")
    assert run(monkeypatch, "--check") == 1
    assert "COMMONS.md" in capsys.readouterr().out


def test_check_fails_when_only_the_readme_counts_are_stale(commons, monkeypatch, capsys):
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    lane.README_MD.write_text(
        f"# Yantra4D\n\n{lane.README_BEGIN}\n| Cartridges | 999 |\n{lane.README_END}\n",
        encoding="utf-8")
    run(monkeypatch)
    lane.README_MD.write_text(
        f"# Yantra4D\n\n{lane.README_BEGIN}\n| Cartridges | 999 |\n{lane.README_END}\n",
        encoding="utf-8")
    assert run(monkeypatch, "--check") == 1
    assert "README.md" in capsys.readouterr().out


# --- the README counts block ----------------------------------------------

def test_readme_counts_are_rewritten_in_place_leaving_the_rest_alone(commons):
    cartridge(commons, "gears", {"project": {"name": "Gears"},
                                 "hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    current = f"head\n{lane.README_BEGIN}\nold\n{lane.README_END}\ntail\n"
    fresh = lane.render_readme(lane.build_catalog(), current)
    assert fresh.startswith("head\n")
    assert fresh.endswith("tail\n")
    assert "old" not in fresh
    assert "| Cartridges | 1 |" in fresh
    assert "| Licensed CERN-OHL-W-2.0 | 1 of 1 |" in fresh


def test_a_readme_without_markers_is_returned_untouched(commons):
    cartridge(commons, "gears", {"project": {"name": "Gears"}})
    current = "# Yantra4D\n\nno markers here\n"
    assert lane.render_readme(lane.build_catalog(), current) == current


def test_readme_cern_row_counts_only_cern_licences(commons):
    cartridge(commons, "a", {"hyperobject": {"commons_license": "CERN-OHL-W-2.0"}})
    cartridge(commons, "b", {"hyperobject": {"commons_license": "CERN-OHL-S-2.0"}})
    cartridge(commons, "c", {"hyperobject": {"commons_license": "MIT"}})
    cartridge(commons, "d", {"project": {"name": "D"}})
    fresh = lane.render_readme(
        lane.build_catalog(), f"{lane.README_BEGIN}\n{lane.README_END}")
    assert "| Licensed CERN-OHL-W-2.0 | 2 of 4 |" in fresh


# --- the committed artifacts ----------------------------------------------

def test_the_committed_catalogue_excludes_every_client_private_slug():
    catalog_path = REPO / "docs" / "commons-catalog.json"
    if not catalog_path.exists():
        pytest.skip("docs/commons-catalog.json is not present in this checkout")
    published = {c["slug"] for c in
                 json.loads(catalog_path.read_text(encoding="utf-8"))["cartridges"]}
    assert published & lane.CLIENT_PRIVATE == set()
