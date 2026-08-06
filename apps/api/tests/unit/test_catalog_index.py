"""Tests for the faceted catalog index + /api/catalog/search endpoint.

The `_isolate_config` autouse fixture (tests/conftest.py) repoints
Config.CARTRIDGES_DIRS at a fresh tmp_path per test, so each test builds the
catalog over only the manifests it writes. The module-level cache is dropped in
setup via invalidate_catalog().
"""
import json

import pytest

from services.core.catalog_index import (
    get_catalog,
    invalidate_catalog,
    search_catalog,
)


@pytest.fixture(autouse=True)
def _fresh_catalog():
    invalidate_catalog()
    yield
    invalidate_catalog()


_DEFAULT_MATERIAL_AWARENESS = {
    "tolerance_by_material": True,
    "shrinkage_compensation": False,
    "recycled_material_toggle": False,
}


def _write(tmp_path, slug, *, domain="household", difficulty="beginner",
           engine="cadquery", geometry_type="socket", standard="ISO 1234",
           is_hyperobject=True, tags=None, modes=None, unlisted=False,
           name=None, material_awareness="__default__"):
    """Write a minimal manifest with the fields the catalog reads.

    `material_awareness` mirrors the real manifest shape: a dict of boolean
    capability flags. Pass a custom dict to vary the flags, or None to omit the
    block entirely (as ~15 real manifests do).
    """
    d = tmp_path / slug
    d.mkdir(exist_ok=True)
    ma = _DEFAULT_MATERIAL_AWARENESS if material_awareness == "__default__" else material_awareness
    hyperobject = {
        "is_hyperobject": is_hyperobject,
        "domain": domain,
        "cdg_interfaces": [
            {"geometry_type": geometry_type, "standard": standard, "name": "iface"}
        ],
    }
    if ma is not None:
        hyperobject["material_awareness"] = ma
    manifest = {
        "project": {
            "slug": slug,
            "name": name or {"en": slug.replace("-", " ").title(), "es": slug},
            "description": {"en": f"{slug} description", "es": f"{slug} descripción"},
            "engine": engine,
            "difficulty": difficulty,
            "tags": tags if tags is not None else ["commons", slug.split("-")[0]],
            "unlisted": unlisted,
        },
        "hyperobject": hyperobject,
        "modes": modes if modes is not None else [
            {"id": "a", "parts": ["a"]},
            {"id": "b", "parts": ["b"]},
        ],
        "parts": [{"id": "a"}, {"id": "b"}],
        "parameters": [],
    }
    (d / "project.json").write_text(json.dumps(manifest))
    return d


def test_empty_catalog(tmp_path):
    cat = get_catalog()
    assert cat["count"] == 0
    assert cat["records"] == []
    assert cat["facets"]["domain"] == []


def test_build_and_record_shape(tmp_path):
    _write(tmp_path, "vesa-mount", domain="industrial", difficulty="intermediate",
           geometry_type="bolt_pattern", standard="VESA 75/100",
           tags=["mount", "vesa"])
    cat = get_catalog()
    assert cat["count"] == 1
    rec = cat["records"][0]
    assert rec["slug"] == "vesa-mount"
    assert rec["domain"] == "industrial"
    assert rec["difficulty"] == "intermediate"
    assert rec["engine"] == "cadquery"
    assert rec["geometry_types"] == ["bolt_pattern"]
    assert rec["standards"] == ["VESA 75/100"]
    assert rec["is_hyperobject"] is True
    assert rec["mode_count"] == 2
    assert rec["thumbnail"] == "/projects/vesa-mount.svg"
    assert rec["name"] == "Vesa Mount"


def test_caching_and_invalidation(tmp_path):
    _write(tmp_path, "one")
    assert get_catalog()["count"] == 1
    # add a manifest; signature (count + mtime) changes → rebuild picks it up
    _write(tmp_path, "two")
    assert get_catalog()["count"] == 2


def test_dual_engine_detection(tmp_path):
    _write(tmp_path, "flagship", engine="cadquery", modes=[
        {"id": "cq", "parts": ["cq"]},
        {"id": "scad", "parts": ["scad"], "engine": "openscad"},
    ])
    rec = get_catalog()["records"][0]
    assert rec["dual_engine"] is True


def test_text_search_and_semantics(tmp_path):
    _write(tmp_path, "nema-bracket", geometry_type="bolt_pattern", standard="NEMA 17",
           tags=["nema", "motor"])
    _write(tmp_path, "vesa-plate", geometry_type="bolt_pattern", standard="VESA 75/100",
           tags=["vesa"])
    # single term
    res = search_catalog(q="nema")
    assert [r["slug"] for r in res["results"]] == ["nema-bracket"]
    # AND semantics: both terms must appear
    assert search_catalog(q="nema vesa")["total"] == 0
    assert search_catalog(q="bracket motor")["total"] == 1


def test_facet_filters(tmp_path):
    _write(tmp_path, "a-med", domain="medical", difficulty="beginner",
           geometry_type="socket", standard="Luer")
    _write(tmp_path, "b-ind", domain="industrial", difficulty="advanced",
           geometry_type="thread", standard="ISO 261")
    _write(tmp_path, "c-med", domain="medical", difficulty="advanced",
           geometry_type="socket", standard="Luer")
    assert search_catalog(domain="medical")["total"] == 2
    assert search_catalog(domain="medical", difficulty="advanced")["total"] == 1
    assert search_catalog(geometry_type="socket")["total"] == 2
    assert search_catalog(standard="Luer")["total"] == 2
    assert search_catalog(engine="cadquery")["total"] == 3


def test_material_signal_extraction(tmp_path):
    # object declaring two capabilities
    _write(tmp_path, "adapts", material_awareness={
        "tolerance_by_material": True,
        "shrinkage_compensation": True,
        "recycled_material_toggle": False,
    })
    # object with the block present but all flags false → aware, no capabilities
    _write(tmp_path, "aware-only", material_awareness={
        "tolerance_by_material": False,
        "shrinkage_compensation": False,
    })
    # object with no material_awareness block at all
    _write(tmp_path, "plain-material", material_awareness=None)

    recs = {r["slug"]: r for r in get_catalog()["records"]}

    assert recs["adapts"]["material_aware"] is True
    assert recs["adapts"]["material_capabilities"] == [
        "tolerance_by_material", "shrinkage_compensation"
    ]
    # capability order is stable regardless of dict insertion order
    assert recs["aware-only"]["material_aware"] is True
    assert recs["aware-only"]["material_capabilities"] == []
    assert recs["plain-material"]["material_aware"] is False
    assert recs["plain-material"]["material_capabilities"] == []


def test_material_facet(tmp_path):
    _write(tmp_path, "a", material_awareness={
        "tolerance_by_material": True, "shrinkage_compensation": True,
    })
    _write(tmp_path, "b", material_awareness={"tolerance_by_material": True})
    _write(tmp_path, "c", material_awareness=None)  # contributes nothing to the facet
    facet = {f["value"]: f["count"] for f in get_catalog()["facets"]["material"]}
    assert facet == {"tolerance_by_material": 2, "shrinkage_compensation": 1}


def test_material_filter(tmp_path):
    _write(tmp_path, "tol", material_awareness={"tolerance_by_material": True})
    _write(tmp_path, "shrink", material_awareness={
        "tolerance_by_material": True, "shrinkage_compensation": True,
    })
    _write(tmp_path, "none", material_awareness=None)
    # exact-match capability filter
    assert search_catalog(material="shrinkage_compensation")["total"] == 1
    assert {r["slug"] for r in search_catalog(material="tolerance_by_material")["results"]} == {
        "tol", "shrink"
    }
    # material_aware boolean filter: both blocks present → 2 (the None one excluded)
    aware = search_catalog(material_aware=True)
    assert aware["total"] == 2
    assert {r["slug"] for r in aware["results"]} == {"tol", "shrink"}


def test_material_capability_in_haystack(tmp_path):
    _write(tmp_path, "hay-tol", material_awareness={"recycled_material_toggle": True})
    _write(tmp_path, "hay-plain", material_awareness=None)
    res = search_catalog(q="recycled_material_toggle")
    assert [r["slug"] for r in res["results"]] == ["hay-tol"]


def test_unlisted_excluded(tmp_path):
    _write(tmp_path, "shown")
    _write(tmp_path, "hidden", unlisted=True)
    res = search_catalog()
    assert res["total"] == 1
    assert res["results"][0]["slug"] == "shown"
    # facets ignore unlisted too
    assert get_catalog()["count"] == 2  # catalog holds both
    assert sum(f["count"] for f in res["facets"]["domain"]) == 1


def test_pagination_and_sort(tmp_path):
    for i in range(5):
        _write(tmp_path, f"proj-{i}", name={"en": f"Proj {i}", "es": f"Proj {i}"})
    res = search_catalog(sort="name", limit=2, offset=0)
    assert res["total"] == 5
    assert len(res["results"]) == 2
    assert res["results"][0]["slug"] == "proj-0"
    page2 = search_catalog(sort="name", limit=2, offset=2)
    assert page2["results"][0]["slug"] == "proj-2"


def test_hyperobject_only_filter(tmp_path):
    _write(tmp_path, "ho", is_hyperobject=True)
    _write(tmp_path, "plain", is_hyperobject=False)
    assert search_catalog(hyperobject_only=True)["total"] == 1
    assert search_catalog(hyperobject_only=False)["total"] == 2


def test_post_filter_facets(tmp_path):
    _write(tmp_path, "m1", domain="medical", geometry_type="socket", standard="Luer")
    _write(tmp_path, "m2", domain="medical", geometry_type="thread", standard="ISO 261")
    _write(tmp_path, "i1", domain="industrial", geometry_type="socket", standard="ISO 261")
    # filtering to medical → facet counts reflect only medical rows
    res = search_catalog(domain="medical")
    geo = {f["value"]: f["count"] for f in res["facets"]["geometry_type"]}
    assert geo == {"socket": 1, "thread": 1}


def test_endpoint_search(tmp_path):
    _write(tmp_path, "nema-bracket", geometry_type="bolt_pattern", standard="NEMA 17",
           tags=["nema"])
    from app import create_app
    client = create_app().test_client()
    r = client.get("/api/catalog/search?q=nema&limit=5")
    assert r.status_code == 200
    body = r.get_json()
    assert body["total"] == 1
    assert body["results"][0]["slug"] == "nema-bracket"
    assert "facets" in body
    assert r.headers.get("Cache-Control")


def test_endpoint_facets(tmp_path):
    _write(tmp_path, "a", domain="medical")
    _write(tmp_path, "b", domain="industrial")
    from app import create_app
    client = create_app().test_client()
    r = client.get("/api/catalog/facets")
    assert r.status_code == 200
    body = r.get_json()
    assert body["count"] == 2
    domains = {f["value"] for f in body["facets"]["domain"]}
    assert domains == {"medical", "industrial"}
