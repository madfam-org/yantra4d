"""Tests for mesh integrity assessment.

The point of these is to prove the detector distinguishes STL float noise from
an actual hole. A watertight check that cannot tell those apart either sends
someone hunting a hole that does not exist, or stays silent about a real one.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.engine.mesh_integrity import assess


def _box(extent=20.0):
    return trimesh.creation.box(extents=(extent, extent, extent))


def _unwelded(mesh):
    """Explode a mesh into loose triangles, the way an STL stores it."""
    return trimesh.Trimesh(
        vertices=mesh.vertices[mesh.faces].reshape(-1, 3),
        faces=np.arange(len(mesh.faces) * 3).reshape(-1, 3),
        process=False,
    )


def _jitter(mesh, magnitude):
    """Perturb every vertex, simulating float rounding in an exported STL."""
    rng = np.random.default_rng(0)
    m = mesh.copy()
    m.vertices = m.vertices + rng.uniform(-magnitude, magnitude, m.vertices.shape)
    return m


class TestClosedGeometry:
    def test_a_box_is_watertight(self):
        r = assess(_box())
        assert r.watertight
        assert r.boundary_edges == 0
        assert r.euler_number == 2
        assert r.volume == pytest.approx(8000.0)

    def test_summary_reads_cleanly(self):
        assert "watertight" in assess(_box()).summary


class TestStlFloatNoise:
    def test_unwelded_triangle_soup_is_recognised_as_closed(self):
        """A closed solid exported as STL arrives unwelded. That is not a hole."""
        soup = _unwelded(_box())
        r = assess(soup, scale_hint=20.0)
        assert r.watertight, r.summary
        assert r.merge_tolerance is not None
        assert any("float precision" in n for n in r.notes)

    def test_sub_micron_jitter_still_reads_as_closed(self):
        jittered = _unwelded(_jitter(_box(), 1e-7))
        r = assess(jittered, scale_hint=20.0)
        assert r.watertight, r.summary

    def test_tolerance_scales_with_the_model(self):
        """A 200mm part and a 2mm part are judged at the same relative precision."""
        for extent in (2.0, 200.0):
            r = assess(_unwelded(_box(extent)), scale_hint=extent)
            assert r.watertight, f"{extent}mm box: {r.summary}"


class TestGenuineHoles:
    def test_a_missing_face_is_reported_as_open(self):
        holed = _box()
        holed.update_faces(np.arange(len(holed.faces)) != 0)  # drop one triangle
        r = assess(holed, scale_hint=20.0)
        assert not r.watertight
        assert r.boundary_edges == 3, r.summary
        assert "does not close" in " ".join(r.notes)

    def test_a_hole_survives_merging(self):
        """Merging must not paper over a real hole."""
        holed = _box()
        holed.update_faces(np.arange(len(holed.faces)) >= 2)  # drop a whole side
        r = assess(_unwelded(holed), scale_hint=20.0)
        assert not r.watertight, r.summary
        assert r.boundary_edges > 0

    def test_an_open_plane_is_not_watertight(self):
        plane = trimesh.Trimesh(
            vertices=[[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]],
            faces=[[0, 1, 2], [0, 2, 3]],
        )
        r = assess(plane)
        assert not r.watertight
        assert r.boundary_edges == 4


class TestNonManifoldGeometry:
    """Closed but self-touching. Distinct from a hole, and fixed differently.

    This is gridfinity's actual signature: zero boundary edges, consistent
    winding, still not watertight. Calling that "not watertight" without saying
    why sends someone hunting a gap that does not exist.
    """

    def _two_boxes_sharing_a_face(self):
        a = trimesh.creation.box(extents=(10, 10, 10))
        b = trimesh.creation.box(extents=(10, 10, 10))
        b.apply_translation((10, 0, 0))
        glued = trimesh.util.concatenate([a, b])
        glued.merge_vertices()
        return glued

    def test_reports_non_manifold_edges_not_a_hole(self):
        r = assess(self._two_boxes_sharing_a_face(), scale_hint=10.0)
        assert not r.watertight
        assert r.boundary_edges == 0, "there is no hole here"
        assert r.nonmanifold_edges > 0
        assert "no holes" in r.summary
        assert "more than two faces" in " ".join(r.notes)

    def test_does_not_confuse_it_with_float_noise(self):
        """Merging must not make a self-touching surface read as sealed."""
        r = assess(_unwelded(self._two_boxes_sharing_a_face()), scale_hint=10.0)
        assert not r.watertight, r.summary

    def test_a_clean_solid_reports_no_non_manifold_edges(self):
        assert assess(_box()).nonmanifold_edges == 0


class TestDegenerateInput:
    def test_empty_mesh(self):
        empty = trimesh.Trimesh(vertices=np.zeros((0, 3)), faces=np.zeros((0, 3), dtype=int))
        r = assess(empty)
        assert not r.watertight
        assert "no faces" in " ".join(r.notes)

    def test_non_mesh_input(self):
        r = assess(trimesh.Scene())
        assert not r.watertight
        assert "not a triangle mesh" in " ".join(r.notes)
