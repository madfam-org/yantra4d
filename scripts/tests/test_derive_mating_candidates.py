"""Tests for the CDG mating-candidate derivation.

Run standalone (there is no root pytest config; the backend suite's coverage gate is
rooted at apps/api and does not own scripts/):

    python3 -m pytest scripts/tests -q

The rule-shape tests build SYNTHETIC cartridge trees in tmp_path, because the
properties under test — a symmetric role pair collapsing to one rule, a one-sided
declaration never reaching the top tier, an unknown standard producing nothing at all —
must hold for inputs the commons does not happen to contain today. Two tests
deliberately run against the REAL repository instead: one asserts the committed
artifact is current, the other asserts `--check` fails closed, and neither can be
faked by a fixture.

Standards used in fixtures are real strings that `normalize_family` resolves (VESA,
Gridfinity, 1/4-20 UNC); the derivation is deliberately anchored to the live graph's
normalizer, so inventing a family here would test nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "qa"))

import derive_mating_candidates as derive  # noqa: E402

VESA = "VESA 100 x 100"
GRIDFINITY = "Gridfinity 42 mm"
QUARTER20 = "ASME B1.1 1/4-20 UNC"
UNKNOWN = "Bespoke Widget Coupling Spec 7"


# ──────────────────────────────────────────────────────────────────────────────
# fixture helpers
# ──────────────────────────────────────────────────────────────────────────────

def write_cartridge(projects: Path, slug: str, interfaces: list[dict], **project) -> None:
    """Write a minimal but structurally real project.json for one synthetic cartridge."""
    directory = projects / slug
    directory.mkdir(parents=True, exist_ok=True)
    manifest = {
        "project": {"slug": slug, "name": {"en": slug}, **project},
        "hyperobject": {"domain": "industrial", "cdg_interfaces": interfaces},
    }
    (directory / "project.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8",
    )


def iface(iface_id: str, role: str, standard: str, **extra) -> dict:
    return {"id": iface_id, "label": {"en": iface_id}, "geometry_type": role,
            "standard": standard, "parameters": [f"{iface_id}_d"], **extra}


def build(projects: Path, gitmodules: Path | None = None,
          bridge_snapshot: Path | None = None) -> dict:
    """Run the whole derivation over a synthetic tree, with no bridge/catalog inputs."""
    return derive.build_artifact(
        projects_dir=projects,
        gitmodules=gitmodules if gitmodules is not None else projects / "absent.gitmodules",
        bridge_snapshot=bridge_snapshot or projects / "absent-bridge.json",
        commons_catalog=projects / "absent-catalog.json",
    )


def rule_by_id(artifact: dict, rule_id: str) -> dict | None:
    for rule in artifact["rules"]:
        if rule["rule_id"] == rule_id:
            return rule
    return None


@pytest.fixture
def projects(tmp_path: Path) -> Path:
    directory = tmp_path / "projects"
    directory.mkdir()
    return directory


# ──────────────────────────────────────────────────────────────────────────────
# what gets excluded
# ──────────────────────────────────────────────────────────────────────────────

def test_unknown_standards_produce_no_rule_and_are_tallied(projects: Path):
    """A standard the normalizer does not recognise can never become a mating rule."""
    write_cartridge(projects, "widget-a", [iface("port", "socket", UNKNOWN)])
    write_cartridge(projects, "widget-b", [iface("plug", "profile", UNKNOWN)])
    # one real family so the run has something to emit and does not bail out
    write_cartridge(projects, "screen-a", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "screen-b", [iface("vesa", "bolt_pattern", VESA)])

    artifact = build(projects)

    assert all(UNKNOWN not in rule["evidence"]["standards_observed"]
               for rule in artifact["rules"])
    assert artifact["inputs"]["interfaces_declared"] == 4
    assert artifact["inputs"]["interfaces_with_resolved_family"] == 2
    rejected = artifact["rejected_interfaces"]
    assert rejected["counts"]["standard_unrecognized"] == 2
    assert rejected["unrecognized_standards"] == [{"standard": UNKNOWN, "interfaces": 2}]


def test_internal_and_absent_standards_are_excluded_separately(projects: Path):
    """`internal` is private geometry and `none` is no claim — neither is a shared standard."""
    write_cartridge(projects, "part-a", [
        iface("private", "socket", "internal"),
        iface("private_variant", "profile", "internal (2 / 3 / 4 mm tube ID)"),
        iface("unclaimed", "snap", "none"),
        iface("vesa", "bolt_pattern", VESA),
    ])
    write_cartridge(projects, "part-b", [iface("vesa", "bolt_pattern", VESA)])

    artifact = build(projects)

    counts = artifact["rejected_interfaces"]["counts"]
    assert counts["standard_internal"] == 2
    assert counts["standard_absent"] == 1
    assert "standard_unrecognized" not in counts
    assert [r["rule_id"] for r in artifact["rules"]] == ["vesa:bolt_pattern+bolt_pattern"]


def test_unlisted_cartridges_are_not_scanned(projects: Path):
    write_cartridge(projects, "listed-a", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "listed-b", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "hidden", [iface("vesa", "bolt_pattern", VESA)], unlisted=True)

    artifact = build(projects)

    assert artifact["inputs"]["cartridges_scanned"] == 2
    assert rule_by_id(artifact, "vesa:bolt_pattern+bolt_pattern")["claimed_pairs"] == 1


def test_submodule_and_private_cartridges_are_never_read(projects: Path, tmp_path: Path):
    """The input boundary holds even when the private manifests ARE on disk.

    CI checks out submodules recursively and a developer usually does not; if presence
    on disk decided the input set, the committed artifact would be unreproducible and
    client-private geometry would leak into a published file.
    """
    write_cartridge(projects, "public-a", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "public-b", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "vendored-sub", [iface("secret_sub", "bolt_pattern", VESA)])
    write_cartridge(projects, "tablaco", [iface("secret_client", "bolt_pattern", VESA)])

    gitmodules = tmp_path / ".gitmodules"
    gitmodules.write_text(
        '[submodule "projects/vendored-sub"]\n'
        "\tpath = projects/vendored-sub\n"
        "\turl = https://example.invalid/vendored-sub.git\n"
        '[submodule "libs/some-lib"]\n'
        "\tpath = libs/some-lib\n"
        "\turl = https://example.invalid/some-lib.git\n",
        encoding="utf-8",
    )

    artifact = build(projects, gitmodules=gitmodules)
    payload = derive.serialize(artifact)

    assert artifact["inputs"]["cartridges_scanned"] == 2
    for forbidden in ("vendored-sub", "tablaco", "secret_sub", "secret_client"):
        assert forbidden not in payload


# ──────────────────────────────────────────────────────────────────────────────
# rule shape
# ──────────────────────────────────────────────────────────────────────────────

def test_symmetric_roles_collapse_to_one_rule_over_unordered_pairs(projects: Path):
    """A<->A is ONE rule claiming C(n,2) pairs, not n^2 and not two mirrored rules."""
    for slug in ("bin-a", "bin-b", "bin-c"):
        write_cartridge(projects, slug, [iface("grid", "grid", GRIDFINITY)])

    artifact = build(projects)

    assert [r["rule_id"] for r in artifact["rules"]] == ["gridfinity:grid+grid"]
    rule = artifact["rules"][0]
    assert rule["symmetric"] is True
    assert rule["members"]["objects_role_a"] == 3
    assert rule["members"]["objects_role_b"] == 3
    assert rule["members"]["objects_total"] == 3
    assert rule["claimed_pairs"] == 3  # C(3,2), not 9 and not 6


def test_an_object_pairing_only_with_itself_claims_nothing(projects: Path):
    """One cartridge declaring both sides of its own joint is not a mating rule."""
    write_cartridge(projects, "solo", [
        iface("male", "profile", VESA),
        iface("female", "socket", VESA),
    ])
    write_cartridge(projects, "screen-a", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "screen-b", [iface("vesa", "bolt_pattern", VESA)])

    artifact = build(projects)

    assert rule_by_id(artifact, "vesa:profile+socket") is None
    assert rule_by_id(artifact, "vesa:bolt_pattern+bolt_pattern") is not None


def test_rules_are_confined_to_a_single_standard_family(projects: Path):
    """Sharing a role across two families is not evidence of anything."""
    write_cartridge(projects, "screen-a", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "screen-b", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "camera-a", [iface("tripod", "bolt_pattern", QUARTER20)])
    write_cartridge(projects, "camera-b", [iface("tripod", "bolt_pattern", QUARTER20)])

    artifact = build(projects)

    families = {r["family"] for r in artifact["rules"]}
    assert families == {"vesa", "unc-1/4-20"}
    for rule in artifact["rules"]:
        assert rule["claimed_pairs"] == 1  # never crosses the two families


# ──────────────────────────────────────────────────────────────────────────────
# confidence tiers
# ──────────────────────────────────────────────────────────────────────────────

def test_two_author_declarations_on_a_two_sided_pair_are_corroborated(projects: Path):
    write_cartridge(projects, "clamp-a", [
        iface("dovetail", "socket", QUARTER20, compatible_with=["plate-a"])])
    write_cartridge(projects, "clamp-b", [
        iface("dovetail", "socket", QUARTER20, compatible_with=["plate-b"])])
    write_cartridge(projects, "plate-a", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "plate-b", [iface("stud", "profile", QUARTER20)])

    rule = rule_by_id(build(projects), "unc-1/4-20:profile+socket")

    assert rule["confidence"] == "corroborated"
    assert rule["one_sided"] is False
    assert rule["evidence"]["author_declared_pairs"] == 2
    assert "2 author-declared" in rule["reason"]


def test_one_sided_declaration_cannot_reach_the_top_tier(projects: Path):
    """Two authors agree, but one side of the rule has a single object to generalise from."""
    write_cartridge(projects, "hub", [iface("socket", "socket", QUARTER20)])
    write_cartridge(projects, "arm-a", [
        iface("stud", "profile", QUARTER20, compatible_with=["hub"])])
    write_cartridge(projects, "arm-b", [
        iface("stud", "profile", QUARTER20, compatible_with=["hub"])])

    rule = rule_by_id(build(projects), "unc-1/4-20:profile+socket")

    assert rule["evidence"]["author_declared_pairs"] == 2
    assert rule["one_sided"] is True
    assert rule["confidence"] == "plausible"
    assert "single object" in rule["reason"]


def test_co_declaration_without_corroboration_is_speculative(projects: Path):
    """Same family, roles the live graph does not mate, and nobody vouching for it."""
    write_cartridge(projects, "panel-a", [iface("face", "surface", VESA)])
    write_cartridge(projects, "panel-b", [iface("face", "surface", VESA)])
    write_cartridge(projects, "bracket-a", [iface("slot", "pocket", VESA)])
    write_cartridge(projects, "bracket-b", [iface("slot", "pocket", VESA)])

    rule = rule_by_id(build(projects), "vesa:pocket+surface")

    assert rule["confidence"] == "speculative"
    assert rule["evidence"]["author_declared_pairs"] == 0
    assert rule["evidence"]["graph_rule_admits"] is None
    assert "co-declaration only" in rule["reason"]


def test_a_pairing_the_live_graph_already_admits_is_flagged_and_not_counted_as_new(
    projects: Path,
):
    """bolt_pattern<->bolt_pattern is already in the graph's table: zero new edges."""
    write_cartridge(projects, "screen-a", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "screen-b", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "screen-c", [iface("vesa", "bolt_pattern", VESA)])

    rule = rule_by_id(build(projects), "vesa:bolt_pattern+bolt_pattern")

    assert rule["evidence"]["graph_rule_admits"] == "mates_with"
    assert rule["evidence"]["graph_agrees"] is True
    assert rule["claimed_pairs"] == 3
    assert rule["pairs_already_in_graph"] == 3
    assert rule["new_edges"] == 0
    assert rule["confidence"] == "plausible"


def test_compatible_with_links_to_out_of_scope_slugs_are_counted_not_paired(
    projects: Path, tmp_path: Path,
):
    write_cartridge(projects, "screen-a", [
        iface("vesa", "bolt_pattern", VESA, compatible_with=["screen-b", "vendored-sub"])])
    write_cartridge(projects, "screen-b", [iface("vesa", "bolt_pattern", VESA)])
    write_cartridge(projects, "vendored-sub", [iface("vesa", "bolt_pattern", VESA)])
    gitmodules = tmp_path / ".gitmodules"
    gitmodules.write_text(
        '[submodule "projects/vendored-sub"]\n\tpath = projects/vendored-sub\n'
        "\turl = https://example.invalid/vendored-sub.git\n", encoding="utf-8",
    )

    artifact = build(projects, gitmodules=gitmodules)

    assert artifact["inputs"]["author_declared_pairs_in_scope"] == 1
    assert artifact["inputs"]["author_declared_links_out_of_scope"] == 1


def test_examples_lead_with_author_declared_pairs(projects: Path):
    write_cartridge(projects, "aaa-plate", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "zzz-plate", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "clamp-a", [
        iface("jaw", "socket", QUARTER20, compatible_with=["zzz-plate"])])
    write_cartridge(projects, "clamp-b", [iface("jaw", "socket", QUARTER20)])

    rule = rule_by_id(build(projects), "unc-1/4-20:profile+socket")

    assert rule["examples"][0]["author_declared"] is True
    assert {rule["examples"][0]["a"], rule["examples"][0]["b"]} == {"zzz-plate", "clamp-a"}
    assert [e["author_declared"] for e in rule["examples"]] == sorted(
        (e["author_declared"] for e in rule["examples"]), reverse=True,
    )


# ──────────────────────────────────────────────────────────────────────────────
# cross-commons bridge evidence
# ──────────────────────────────────────────────────────────────────────────────

def test_bridge_evidence_comes_only_from_the_pinned_snapshot(projects: Path, tmp_path: Path):
    """A sibling checkout must never decide the artifact — only the committed snapshot can.

    The bridge index lives in the fashion-cabinet repository, which CI does not have. If
    it were read directly, the same commons would derive two different artifacts and the
    --check gate would fail in CI for a reason that has nothing to do with the commons.
    """
    write_cartridge(projects, "strap-a", [iface("slot", "rail", QUARTER20)])
    write_cartridge(projects, "strap-b", [iface("slot", "rail", QUARTER20)])
    snapshot = tmp_path / "bridge.json"
    snapshot.write_text(
        json.dumps({"schema_version": derive.BRIDGE_SNAPSHOT_SCHEMA,
                    "consumers": {"strap-a": 4, "unrelated": 99}}),
        encoding="utf-8",
    )

    without = rule_by_id(build(projects), "unc-1/4-20:rail+rail")
    with_snapshot = rule_by_id(build(projects, bridge_snapshot=snapshot),
                               "unc-1/4-20:rail+rail")

    assert without["evidence"]["bridge_objects"] == 0
    assert without["evidence"]["bridge_consumers"] == 0
    assert with_snapshot["evidence"]["bridge_objects"] == 1
    assert with_snapshot["evidence"]["bridge_consumers"] == 4  # "unrelated" is not a member


def test_committed_bridge_snapshot_is_well_formed():
    snapshot = json.loads(derive.BRIDGE_SNAPSHOT.read_text(encoding="utf-8"))

    assert snapshot["schema_version"] == derive.BRIDGE_SNAPSHOT_SCHEMA
    assert snapshot["source"]["repo"] == "fashion-cabinet"
    assert snapshot["consumers"]
    assert all(isinstance(v, int) and v >= 0 for v in snapshot["consumers"].values())


# ──────────────────────────────────────────────────────────────────────────────
# projection
# ──────────────────────────────────────────────────────────────────────────────

def test_projection_is_cumulative_and_never_double_counts(projects: Path):
    write_cartridge(projects, "clamp-a", [
        iface("jaw", "socket", QUARTER20, compatible_with=["plate-a"])])
    write_cartridge(projects, "clamp-b", [
        iface("jaw", "socket", QUARTER20, compatible_with=["plate-b"])])
    write_cartridge(projects, "plate-a", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "plate-b", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "rail-a", [iface("slot", "rail", QUARTER20)])
    write_cartridge(projects, "rail-b", [iface("slot", "rail", QUARTER20)])

    artifact = build(projects)
    projection = artifact["projection"]
    baseline = artifact["graph_baseline"]

    assert [t["tranche"] for t in projection] == list(derive.TIER_ORDER)
    edges = [baseline["edges"]] + [t["edges_after"] for t in projection]
    assert edges == sorted(edges), "cumulative edge count must never decrease"
    for tranche in projection:
        # every pair is a pair of the 6 objects, so the union can never exceed C(6,2)
        assert tranche["edges_after"] <= 15
        assert tranche["density_pct_over_graph_nodes"] <= 100.0
    total_new = sum(t["new_edges_in_tranche"] for t in projection)
    assert baseline["edges"] + total_new == projection[-1]["edges_after"]


def test_author_declared_recall_is_scored_against_the_baseline(projects: Path):
    """The authors' own links are the held-out answer key, never a rule input."""
    write_cartridge(projects, "clamp-a", [
        iface("jaw", "profile", QUARTER20, compatible_with=["plate-a"])])
    write_cartridge(projects, "clamp-b", [
        iface("jaw", "profile", QUARTER20, compatible_with=["plate-b"])])
    write_cartridge(projects, "plate-a", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "plate-b", [iface("stud", "profile", QUARTER20)])

    artifact = build(projects)

    # profile<->profile is NOT in the live graph's table, so the baseline explains none
    rule = rule_by_id(artifact, "unc-1/4-20:profile+profile")
    assert rule["evidence"]["graph_rule_admits"] is None
    assert rule["confidence"] == "corroborated"
    assert artifact["graph_baseline"]["author_declared_pairs_reproduced"] == 0
    assert artifact["graph_baseline"]["author_declared_pairs_missing"] == 2
    assert artifact["graph_baseline"]["author_declared_pairs_without_shared_family"] == 0
    assert artifact["projection"][0]["author_declared_pairs_explained"] == 2
    assert artifact["projection"][0]["author_declared_pairs_explained_pct"] == 100.0


# ──────────────────────────────────────────────────────────────────────────────
# determinism
# ──────────────────────────────────────────────────────────────────────────────

def test_repeated_derivations_are_byte_identical(projects: Path):
    write_cartridge(projects, "clamp-a", [
        iface("jaw", "socket", QUARTER20, compatible_with=["plate-a"])])
    write_cartridge(projects, "plate-a", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "plate-b", [iface("stud", "profile", QUARTER20)])
    write_cartridge(projects, "bin-a", [iface("grid", "grid", GRIDFINITY)])
    write_cartridge(projects, "bin-b", [iface("grid", "grid", GRIDFINITY)])

    assert derive.serialize(build(projects)) == derive.serialize(build(projects))


def test_output_does_not_depend_on_declaration_order(tmp_path: Path):
    """Same commons, different order inside each manifest — identical artifact."""
    forward = tmp_path / "forward"
    reverse = tmp_path / "reverse"
    forward.mkdir()
    reverse.mkdir()
    cartridges = {
        "clamp-a": [iface("jaw", "socket", QUARTER20, compatible_with=["plate-b", "plate-a"]),
                    iface("grid", "grid", GRIDFINITY)],
        "plate-a": [iface("stud", "profile", QUARTER20), iface("grid", "grid", GRIDFINITY)],
        "plate-b": [iface("stud", "profile", QUARTER20), iface("mount", "bolt_pattern", VESA)],
        "screen-a": [iface("mount", "bolt_pattern", VESA), iface("grid", "grid", GRIDFINITY)],
    }
    for slug, interfaces in cartridges.items():
        write_cartridge(forward, slug, interfaces)
    for slug, interfaces in reversed(list(cartridges.items())):
        flipped = list(reversed(interfaces))
        for entry in flipped:
            if "compatible_with" in entry:
                entry["compatible_with"] = list(reversed(entry["compatible_with"]))
        write_cartridge(reverse, slug, flipped)

    assert derive.serialize(build(forward)) == derive.serialize(build(reverse))


# ──────────────────────────────────────────────────────────────────────────────
# the real repository
# ──────────────────────────────────────────────────────────────────────────────

def test_committed_artifact_is_current():
    """The committed proposal must match a fresh derivation from the real manifests."""
    assert derive.OUTPUT.exists(), f"{derive.OUTPUT} has not been generated"
    assert derive.OUTPUT.read_text(encoding="utf-8") == derive.serialize(
        derive.build_artifact()
    ), "docs/interfaces/mating-candidates.json is stale — rerun the generator"


def test_committed_artifact_is_marked_proposed_and_names_no_private_cartridge():
    artifact = json.loads(derive.OUTPUT.read_text(encoding="utf-8"))
    payload = derive.OUTPUT.read_text(encoding="utf-8")

    assert artifact["status"] == "proposed"
    assert "NOT APPLIED" in artifact["_comment"]
    for private in derive.PRIVATE_EXCLUDED:
        assert private not in payload


@pytest.mark.parametrize("mutate", [
    pytest.param(lambda p: p.write_text("{}\n", encoding="utf-8"), id="stale"),
    pytest.param(lambda p: p.unlink(), id="missing"),
])
def test_check_mode_fails_closed(tmp_path: Path, monkeypatch, mutate, capsys):
    target = tmp_path / "mating-candidates.json"
    target.write_text(derive.serialize(derive.build_artifact()), encoding="utf-8")
    monkeypatch.setattr(derive, "OUTPUT", target)
    monkeypatch.setattr(sys, "argv", ["derive_mating_candidates.py", "--check"])

    assert derive.main() == 0
    mutate(target)
    assert derive.main() == 1
    assert "Regenerate with" in capsys.readouterr().out
