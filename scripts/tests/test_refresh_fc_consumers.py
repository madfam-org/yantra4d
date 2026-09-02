"""Tests for the Fashion Cabinet consumers back-edge lane.

Run standalone (there is no root pytest config; the backend suite's coverage
gate is rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests -q

Everything here runs against the REAL vendored snapshot and the REAL manifests
in this repo. Synthetic fixtures would keep passing while the actual commons
drifted underneath them, which is the failure this lane exists to prevent — so
the fixtures are *mutations* of the committed snapshot instead: one parameter
renamed, one slug pointed at nothing, one file reformatted.

No test asserts a specific FC consumer or a specific cartridge is present; the
suite pins the *rule*, not the current membership of the bridge.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import refresh_fc_consumers as lane  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# helpers
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def committed() -> dict:
    if not lane.SNAPSHOT.exists():
        pytest.fail(f"vendored snapshot missing: {lane.SNAPSHOT}")
    return json.loads(lane.SNAPSHOT.read_text(encoding="utf-8"))


def _first_linked(document: dict) -> tuple[str, dict]:
    """The first (yantra4d slug, consumer entry) pair in stable order."""
    for slug, entry, linked in lane.consumer_claims(document):
        if linked and lane.driven_parameters(entry):
            return slug, entry
    pytest.fail("the vendored snapshot carries no linked consumer with parameters")


def _write(path: Path, snapshot: dict) -> Path:
    path.write_text(lane.canonical(snapshot), encoding="utf-8")
    return path


def _check(path: Path) -> int:
    return lane.main(["--check", "--snapshot", str(path)])


# ──────────────────────────────────────────────────────────────────────────────
# the committed artifact
# ──────────────────────────────────────────────────────────────────────────────

def test_committed_snapshot_passes(capsys):
    assert lane.main(["--check"]) == 0
    out = capsys.readouterr().out
    assert "every linked fashion-cabinet claim resolves" in out
    assert "parameter references checked" in out


def test_committed_snapshot_is_canonical(committed):
    """The file on disk is exactly what the script would re-serialise."""
    assert lane.SNAPSHOT.read_text(encoding="utf-8") == lane.canonical(committed)


def test_pin_names_an_immutable_commit(committed):
    pin = committed["pin"]
    assert pin["source_repo"] == lane.SOURCE_REPO
    assert pin["source_path"] == lane.SOURCE_PATH
    assert lane.SHA_RE.match(pin["source_commit"])
    assert committed["document"]["schema_version"] == lane.SUPPORTED_SCHEMA


# ──────────────────────────────────────────────────────────────────────────────
# fail-closed: this is the point of the lane
# ──────────────────────────────────────────────────────────────────────────────

def test_missing_parameter_fails_and_names_consumer_slug_and_param(committed, tmp_path, capsys):
    """A yantra4d parameter rename that breaks a cabinet object must be red here."""
    snapshot = copy.deepcopy(committed)
    slug, entry = _first_linked(snapshot["document"])
    fc_slug = entry["slug"]
    real_param = lane.driven_parameters(entry)[0]
    renamed = f"{real_param}_renamed_by_a_test"
    entry["drives"] = [renamed if p == real_param else p for p in entry.get("drives", [])]
    entry["params_map"] = {
        (renamed if key == real_param else key): value
        for key, value in (entry.get("params_map") or {}).items()
    }

    assert _check(_write(tmp_path / "snap.json", snapshot)) == 1
    out = capsys.readouterr().out
    assert fc_slug in out
    assert slug in out
    assert renamed in out
    assert "does not declare" in out


def test_unknown_target_slug_fails(committed, tmp_path, capsys):
    snapshot = copy.deepcopy(committed)
    consumers = snapshot["document"]["consumers"]
    slug, entry = _first_linked(snapshot["document"])
    consumers["not-a-cartridge-in-this-repo"] = [copy.deepcopy(entry)]

    assert _check(_write(tmp_path / "snap.json", snapshot)) == 1
    out = capsys.readouterr().out
    assert "not-a-cartridge-in-this-repo" in out
    assert entry["slug"] in out
    assert "does not exist in this repo" in out


def test_hand_edited_snapshot_fails(committed, tmp_path, capsys):
    """A reformat (or any write not made by this script) is caught."""
    path = tmp_path / "snap.json"
    path.write_text(json.dumps(committed, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")

    assert _check(path) == 1
    assert "not in canonical form" in capsys.readouterr().out


def test_missing_pin_fails(committed, tmp_path, capsys):
    snapshot = copy.deepcopy(committed)
    snapshot["pin"]["source_commit"] = "main"

    assert _check(_write(tmp_path / "snap.json", snapshot)) == 1
    assert "40-character commit sha" in capsys.readouterr().out


def test_breaking_schema_version_fails(committed, tmp_path, capsys):
    """Guarantee 5: a breaking back-edge change bumps schema_version. Stop, don't guess."""
    snapshot = copy.deepcopy(committed)
    snapshot["document"]["schema_version"] = "yantra4d_consumers_v2"

    assert _check(_write(tmp_path / "snap.json", snapshot)) == 1
    assert "breaking change" in capsys.readouterr().out


# ──────────────────────────────────────────────────────────────────────────────
# unlinked claims are reported, never enforced
# ──────────────────────────────────────────────────────────────────────────────

def test_unlinked_claims_never_fail(committed, tmp_path, capsys):
    snapshot = copy.deepcopy(committed)
    document = snapshot["document"]
    document["consumers"]["also-not-a-cartridge"] = [{
        "slug": "some-unbuilt-garment",
        "name": "Some Unbuilt Garment",
        "linked": False,
        "drives": ["a_parameter_that_does_not_exist"],
        "params_map": {"a_parameter_that_does_not_exist": "front_len"},
    }]
    document["wanted"] = list(document.get("wanted") or []) + [{
        "target_slug": "a-solid-nobody-has-built",
        "requesting": ["some-unbuilt-garment"],
        "exists_upstream": False,
        "reason": "co-create target, not built here yet",
    }]

    assert _check(_write(tmp_path / "snap.json", snapshot)) == 0
    out = capsys.readouterr().out
    assert "reported, not enforced" in out
    assert "a-solid-nobody-has-built" in out
    assert "not built here yet" in out


# ──────────────────────────────────────────────────────────────────────────────
# vendoring
# ──────────────────────────────────────────────────────────────────────────────

def test_from_path_vendoring_is_idempotent(committed, tmp_path):
    """Re-vendoring the same source at the same pin reproduces the same bytes."""
    source = tmp_path / "yantra4d-consumers.json"
    source.write_text(json.dumps(committed["document"], indent=2, ensure_ascii=False),
                      encoding="utf-8")
    commit = committed["pin"]["source_commit"]
    out = tmp_path / "vendored.json"

    argv = ["--from-path", str(source), "--pin-commit", commit, "--snapshot", str(out)]
    assert lane.main(argv) == 0
    first = out.read_text(encoding="utf-8")
    assert lane.main(argv) == 0
    assert out.read_text(encoding="utf-8") == first

    # ...and it reproduces the committed artifact byte for byte, which is the
    # only reason `--check`'s canonical-form tripwire means anything.
    assert first == lane.SNAPSHOT.read_text(encoding="utf-8")
    assert _check(out) == 0


def test_from_path_requires_a_pin(committed, tmp_path, capsys):
    source = tmp_path / "yantra4d-consumers.json"
    source.write_text(json.dumps(committed["document"]), encoding="utf-8")

    assert lane.main(["--from-path", str(source), "--snapshot", str(tmp_path / "o.json")]) == 1
    assert "--pin-commit" in capsys.readouterr().out


def test_vendoring_refuses_a_branch_name_as_a_pin(committed, tmp_path, capsys):
    source = tmp_path / "yantra4d-consumers.json"
    source.write_text(json.dumps(committed["document"]), encoding="utf-8")

    assert lane.main(["--from-path", str(source), "--pin-commit", "main",
                      "--snapshot", str(tmp_path / "o.json")]) == 1
    assert "immutable fashion-cabinet commit" in capsys.readouterr().out


def test_vendoring_refuses_an_empty_back_edge(tmp_path, capsys):
    source = tmp_path / "yantra4d-consumers.json"
    source.write_text(json.dumps({"schema_version": lane.SUPPORTED_SCHEMA, "consumers": {}}),
                      encoding="utf-8")

    assert lane.main(["--from-path", str(source), "--pin-commit", "0" * 40,
                      "--snapshot", str(tmp_path / "o.json")]) == 1
    assert "empty back-edge" in capsys.readouterr().out


# ──────────────────────────────────────────────────────────────────────────────
# resolution rules
# ──────────────────────────────────────────────────────────────────────────────

def test_parameters_resolve_from_the_manifest_not_the_catalog(committed):
    """The on-disk manifest wins, so a rename cannot hide behind a stale catalog."""
    slug, _ = _first_linked(committed["document"])
    if not (REPO / "projects" / slug / "project.json").exists():
        pytest.skip(f"{slug} is not checked out (submodule); catalog fallback covers it")
    _, source = lane.target_parameters(slug, lane.load_catalog())
    assert source == f"projects/{slug}/project.json"


def test_catalog_is_the_fallback_for_uncheckedout_cartridges():
    catalog = lane.load_catalog()
    assert catalog, "docs/commons-catalog.json should list cartridges"
    slug = next((s for s in catalog if not (REPO / "projects" / s / "project.json").exists()), None)
    if slug is None:
        pytest.skip("every catalogued cartridge is checked out here — no fallback to exercise")
    ids, source = lane.target_parameters(slug, catalog)
    assert ids is not None and source == "docs/commons-catalog.json"


def test_driven_parameters_unions_drives_and_params_map_keys():
    entry = {"drives": ["a"], "params_map": {"a": "x", "b": "y"}}
    assert lane.driven_parameters(entry) == ["a", "b"]
