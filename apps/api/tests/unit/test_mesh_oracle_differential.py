"""Differential test: geom-core against today's trimesh path, on the same meshes.

Skipped unless the geom-core wheel is installed (``geom_core_py`` importable).
CI's ``mesh-oracle-differential`` job installs the Linux wheel from the
geom-core GitHub Release and runs this file with ``MESH_ORACLE=both``.

A difference here is either a geom-core bug or a documented, deliberate
difference (see services/engine/mesh_metrics.py); each such case is asserted
explicitly below rather than loosened into a tolerance.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

pytest.importorskip("geom_core_py", reason="geom-core wheel not installed")

from services.engine import mesh_metrics
from services.engine.mesh_metrics import INTEGRITY_FIELDS, GeomCoreOracle, TrimeshOracle
from utils.metrics import MESH_ORACLE_PARITY_MISMATCH

REPO = Path(__file__).resolve().parents[4]


def _box(extent=20.0):
    return trimesh.creation.box(extents=(extent, extent, extent))


def _open_box():
    m = _box()
    return trimesh.Trimesh(vertices=m.vertices, faces=m.faces[2:], process=False)


def _two_bodies():
    a, b = _box(10.0), _box(10.0)
    b.apply_translation((30.0, 0.0, 0.0))
    return trimesh.util.concatenate([a, b])


def _degenerate():
    vertices = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=float)
    return trimesh.Trimesh(vertices=vertices, faces=np.array([[0, 1, 2], [1, 2, 3], [0, 2, 3]]),
                           process=False)


def _shared_face(merge=True):
    """Two boxes touching on a face: gridfinity's signature, closed but
    non-manifold once the coincident vertices are welded (as an STL load does)."""
    a, b = _box(10.0), _box(10.0)
    b.apply_translation((10.0, 0.0, 0.0))
    glued = trimesh.util.concatenate([a, b])
    if merge:
        glued.merge_vertices()
    return glued


SYNTHETIC = {
    "closed_box": (_box, True),
    "tiny_box": (lambda: _box(0.5), True),
    "large_box": (lambda: _box(400.0), True),
    "icosphere": (lambda: trimesh.creation.icosphere(subdivisions=3, radius=10.0), True),
    "torus": (lambda: trimesh.creation.torus(major_radius=20.0, minor_radius=5.0), True),
    "two_bodies": (_two_bodies, True),
    "open_box": (_open_box, False),
    "degenerate": (_degenerate, False),
    "shared_face": (_shared_face, False),
}

#: Reference exports committed in the commons (present when the `projects`
#: submodule is checked out, as CI does).
REFERENCE_STLS = sorted(p for p in (REPO / "projects").glob("*/exports/*.stl")
                        if p.stat().st_size < 3_000_000)


def _close(a, b):
    return all(math.isclose(x, y, rel_tol=1e-6, abs_tol=1e-6) for x, y in zip(a, b))


def _cases():
    for name, (make, solid) in SYNTHETIC.items():
        yield pytest.param(make, solid, id=name)
    for path in REFERENCE_STLS:
        yield pytest.param(lambda p=path: trimesh.load(str(p), force="mesh"), None,
                           id=str(path.relative_to(REPO / "projects")))


@pytest.fixture
def oracles():
    return TrimeshOracle(), GeomCoreOracle()


@pytest.mark.parametrize("make,solid", list(_cases()))
def test_quote_metrics_agree(oracles, make, solid):
    tm, gc = oracles
    mesh = make()
    assert math.isclose(tm.volume_mm3(mesh), gc.volume_mm3(mesh), rel_tol=1e-6, abs_tol=1e-6)
    assert math.isclose(tm.surface_area_mm2(mesh), gc.surface_area_mm2(mesh), rel_tol=1e-6)
    assert _close(tm.bbox_mm(mesh), gc.bbox_mm(mesh))
    if solid is not None:
        assert (tm.volume_mm3(mesh) > 0) == solid


@pytest.mark.parametrize("make,solid", list(_cases()))
def test_integrity_verdicts_agree(oracles, make, solid):
    tm, gc = oracles
    mesh = make()
    hint = float(max(mesh.extents)) if len(mesh.faces) else None
    a, b = tm.integrity(mesh, hint), gc.integrity(mesh, hint)
    for field_name in INTEGRITY_FIELDS:
        va, vb = getattr(a, field_name), getattr(b, field_name)
        if isinstance(va, float):
            assert math.isclose(va, vb, rel_tol=1e-6, abs_tol=1e-6), field_name
        else:
            assert va == vb, field_name


@pytest.mark.parametrize("name", ["closed_box", "icosphere", "torus", "two_bodies"])
def test_centroid_and_body_count_agree_on_solids(oracles, name):
    tm, gc = oracles
    mesh = SYNTHETIC[name][0]()
    assert tm.body_count(mesh) == gc.body_count(mesh)
    assert all(math.isclose(x, y, abs_tol=1e-6) for x, y in zip(tm.centroid_mm(mesh), gc.centroid_mm(mesh)))


def test_centroid_differs_on_open_meshes_by_design(oracles):
    """An open surface has no volumetric centroid; the two report different
    non-answers (trimesh: flux-integral centre, geom-core: its own sum). No
    caller reads a centroid of an open mesh; asserted so a change is noticed."""
    tm, gc = oracles
    assert not _close(tm.centroid_mm(_open_box()), gc.centroid_mm(_open_box()))


def test_unwelded_soup_same_verdict(oracles):
    """STL triangle soup: trimesh assess seals it with a tolerance merge, geom-core
    welds exact duplicates on load. Same verdict, different evidence (documented)."""
    tm, gc = oracles
    box = _box()
    soup = trimesh.Trimesh(vertices=box.vertices[box.faces].reshape(-1, 3),
                           faces=np.arange(len(box.faces) * 3).reshape(-1, 3), process=False)
    a, b = tm.integrity(soup, 20.0), gc.integrity(soup, 20.0)
    assert a.watertight and b.watertight
    assert a.volume == pytest.approx(b.volume)


def test_unmerged_touching_bodies_differ_by_design(oracles):
    """In memory, two shells that touch but were never welded are two closed
    bodies to trimesh; geom-core welds exact duplicates on load and sees the
    non-manifold contact. Production loads files through trimesh.load, which
    welds first, so the two agree there (``shared_face`` above). Documented in
    mesh_metrics.py; asserted so a change on either side is noticed."""
    tm, gc = oracles
    mesh = _shared_face(merge=False)
    assert tm.integrity(mesh, 20.0).watertight
    verdict = gc.integrity(mesh, 20.0)
    assert not verdict.watertight and verdict.nonmanifold_edges > 0


def test_both_mode_records_no_mismatch_on_closed_solids(monkeypatch):
    monkeypatch.setenv("MESH_ORACLE", "both")
    names = ["volume_mm3", "surface_area_mm2", "bbox_mm"] + [f"integrity.{f}" for f in INTEGRITY_FIELDS]
    before = {n: MESH_ORACLE_PARITY_MISMATCH.labels(metric=n)._value.get() for n in names}
    for name in ("closed_box", "icosphere", "torus", "two_bodies"):
        mesh = SYNTHETIC[name][0]()
        mesh_metrics.quote_metrics(mesh, slug=name)
        mesh_metrics.integrity(mesh, slug=name)
    after = {n: MESH_ORACLE_PARITY_MISMATCH.labels(metric=n)._value.get() for n in names}
    assert after == before
