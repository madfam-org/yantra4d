"""Tests for the CDG compatibility graph derivation + endpoints.

Uses the `_isolate_config` autouse fixture (conftest) to point CARTRIDGES_DIRS at a
tmp_path; each test writes only the manifests it needs. The module cache is dropped in
setup.
"""
import json

import pytest

from services.core.compatibility_graph import (
    get_graph,
    invalidate_graph,
    normalize_family,
    works_with,
)


@pytest.fixture(autouse=True)
def _fresh_graph():
    invalidate_graph()
    yield
    invalidate_graph()


def _write(tmp_path, slug, interfaces, *, domain="industrial", unlisted=False):
    """Write a manifest whose hyperobject.cdg_interfaces = the given list."""
    d = tmp_path / slug
    d.mkdir(exist_ok=True)
    manifest = {
        "project": {"slug": slug, "name": slug.title(), "unlisted": unlisted},
        "hyperobject": {
            "is_hyperobject": True,
            "domain": domain,
            "cdg_interfaces": interfaces,
        },
    }
    (d / "project.json").write_text(json.dumps(manifest))
    return d


def _iface(geometry_type, standard, label="iface"):
    return {"id": standard, "label": label, "geometry_type": geometry_type,
            "standard": standard, "parameters": []}


# ── normalization ─────────────────────────────────────────────────────────────
def test_normalize_family_variants_collapse():
    # different free-text strings for the same family collapse to one key
    assert normalize_family("ASME B1.1 1/4-20 UNC") == "unc-1/4-20"
    assert normalize_family("ASME 1/4-20") == "unc-1/4-20"
    assert normalize_family("VESA MIS-D/E/F (FDMI)") == "vesa"
    assert normalize_family("Gridfinity (42mm module, 7mm Z-unit)") == "gridfinity"
    assert normalize_family("NEMA 17/23/34") == "nema-stepper"


def test_normalize_family_internal_and_unknown():
    assert normalize_family("internal") is None
    assert normalize_family("") is None
    assert normalize_family("something totally bespoke xyz") is None


# ── edge derivation ───────────────────────────────────────────────────────────
def test_bolt_pattern_self_mates(tmp_path):
    _write(tmp_path, "plate-a", [_iface("bolt_pattern", "ASME B1.1 1/4-20 UNC")])
    _write(tmp_path, "plate-b", [_iface("bolt_pattern", "ASME 1/4-20")])
    g = get_graph()
    assert g["edge_count"] == 1
    e = g["edges"][0]
    assert {e["a"], e["b"]} == {"plate-a", "plate-b"}
    assert e["kind"] == "mates_with"
    assert e["family"] == "unc-1/4-20"


def test_socket_thread_complementary_mate(tmp_path):
    _write(tmp_path, "bottle", [_iface("thread", "PCO 1881")])
    _write(tmp_path, "cap", [_iface("socket", "PCO 1881 neck")])
    g = get_graph()
    assert g["edge_count"] == 1
    assert g["edges"][0]["kind"] == "mates_with"
    assert g["edges"][0]["family"] == "pco-1881"


def test_grid_is_same_family_not_mates(tmp_path):
    _write(tmp_path, "bin", [_iface("grid", "Gridfinity 42mm")])
    _write(tmp_path, "base", [_iface("grid", "Gridfinity (42mm module)")])
    g = get_graph()
    assert g["edge_count"] == 1
    assert g["edges"][0]["kind"] == "same_family"


def test_no_edge_across_different_families(tmp_path):
    _write(tmp_path, "vesa-thing", [_iface("bolt_pattern", "VESA MIS-D")])
    _write(tmp_path, "nema-thing", [_iface("bolt_pattern", "NEMA 17")])
    assert get_graph()["edge_count"] == 0


def test_incompatible_geometry_same_family_no_edge(tmp_path):
    # two 'surface' interfaces of the same family don't mate (surface not self-mating)
    _write(tmp_path, "a", [_iface("surface", "VESA MIS-D")])
    _write(tmp_path, "b", [_iface("surface", "VESA MIS-D")])
    assert get_graph()["edge_count"] == 0


def test_internal_standard_ignored(tmp_path):
    _write(tmp_path, "a", [_iface("bolt_pattern", "internal")])
    _write(tmp_path, "b", [_iface("bolt_pattern", "internal")])
    g = get_graph()
    assert g["node_count"] == 0  # nothing with a real family
    assert g["edge_count"] == 0


def test_unlisted_excluded(tmp_path):
    _write(tmp_path, "shown", [_iface("bolt_pattern", "1/4-20")])
    _write(tmp_path, "hidden", [_iface("bolt_pattern", "1/4-20")], unlisted=True)
    g = get_graph()
    assert {n["slug"] for n in g["nodes"]} == {"shown"}
    assert g["edge_count"] == 0


def test_degree_and_hub_ordering(tmp_path):
    # a hub that mates with three leaves via the same family
    _write(tmp_path, "hub", [_iface("bolt_pattern", "1/4-20")])
    for leaf in ("leaf-a", "leaf-b", "leaf-c"):
        _write(tmp_path, leaf, [_iface("bolt_pattern", "1/4-20")])
    g = get_graph()
    # hub + 3 leaves all pairwise share the family → complete graph K4 = 6 edges
    assert g["edge_count"] == 6
    # every node degree 3
    assert all(n["degree"] == 3 for n in g["nodes"])


def test_works_with_groups_reasons(tmp_path):
    _write(tmp_path, "arca", [
        _iface("bolt_pattern", "ASME B1.1 1/4-20 UNC"),
        _iface("profile", "Arca-Swiss 38mm"),
    ])
    _write(tmp_path, "clamp", [_iface("socket", "Arca-Swiss clamp")])
    _write(tmp_path, "post", [_iface("bolt_pattern", "1/4-20")])
    w = works_with("arca")
    assert w["slug"] == "arca"
    partners = {p["slug"]: p for p in w["partners"]}
    # clamp mates via arca-swiss (socket↔profile); post mates via 1/4-20 (bolt↔bolt)
    assert "clamp" in partners and "post" in partners
    assert partners["clamp"]["reasons"][0]["family"] == "arca-swiss"
    assert partners["post"]["reasons"][0]["family"] == "unc-1/4-20"
    assert partners["clamp"]["thumbnail"] == "/projects/clamp.svg"


def test_caching_rebuilds_on_change(tmp_path):
    _write(tmp_path, "a", [_iface("bolt_pattern", "1/4-20")])
    assert get_graph()["node_count"] == 1
    _write(tmp_path, "b", [_iface("bolt_pattern", "1/4-20")])
    assert get_graph()["node_count"] == 2  # signature changed → rebuilt


# ── endpoints ─────────────────────────────────────────────────────────────────
def test_endpoints(tmp_path):
    _write(tmp_path, "plate-a", [_iface("bolt_pattern", "1/4-20")])
    _write(tmp_path, "plate-b", [_iface("bolt_pattern", "1/4-20")])
    from app import create_app
    client = create_app().test_client()

    r = client.get("/api/catalog/graph")
    assert r.status_code == 200
    assert r.get_json()["edge_count"] == 1

    r = client.get("/api/catalog/plate-a/works-with")
    assert r.status_code == 200
    body = r.get_json()
    assert body["count"] == 1
    assert body["partners"][0]["slug"] == "plate-b"

    r = client.get("/api/catalog/families")
    assert r.status_code == 200
    fams = r.get_json()["families"]
    assert any(f["family"] == "unc-1/4-20" for f in fams)
