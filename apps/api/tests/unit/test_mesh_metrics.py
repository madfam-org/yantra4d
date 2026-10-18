"""Tests for the mesh-oracle seam (services/engine/mesh_metrics.py).

The default oracle must be today's code paths unchanged; ``both`` must count
every disagreement; a missing or misnamed backend must say so and fall back.
These run without geom-core. tests/unit/test_mesh_oracle_differential.py
compares the two real oracles and skips when the wheel is not installed.
"""
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import numpy as np
import pytest
import trimesh

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.engine import mesh_metrics
from services.engine.mesh_integrity import MeshIntegrity, assess
from services.engine.mesh_metrics import (
    GeomCoreOracle,
    QuoteMetrics,
    TrimeshOracle,
)
from utils.metrics import MESH_ORACLE_PARITY_MISMATCH

# ---------------------------------------------------------------------------
# Synthetic meshes
# ---------------------------------------------------------------------------

def closed_box(extent=20.0):
    return trimesh.creation.box(extents=(extent, extent, extent))


def open_box(extent=20.0):
    m = closed_box(extent)
    return trimesh.Trimesh(vertices=m.vertices, faces=m.faces[2:], process=False)


def two_bodies():
    a = closed_box(10.0)
    b = closed_box(10.0)
    b.apply_translation((30.0, 0.0, 0.0))
    return trimesh.util.concatenate([a, b])


def degenerate():
    """Three triangles with zero area: collinear vertices, nothing enclosed."""
    vertices = np.array([[0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]], dtype=float)
    faces = np.array([[0, 1, 2], [1, 2, 3], [0, 2, 3]])
    return trimesh.Trimesh(vertices=vertices, faces=faces, process=False)


@pytest.fixture(autouse=True)
def _default_mode(monkeypatch):
    monkeypatch.delenv(mesh_metrics.ORACLE_ENV, raising=False)
    mesh_metrics._warned.clear()


def mismatches(metric):
    return MESH_ORACLE_PARITY_MISMATCH.labels(metric=metric)._value.get()


# ---------------------------------------------------------------------------
# TrimeshOracle: today's behaviour
# ---------------------------------------------------------------------------

class TestTrimeshOracle:
    oracle = TrimeshOracle()

    def test_closed_box(self):
        m = closed_box()
        assert self.oracle.volume_mm3(m) == pytest.approx(8000.0)
        assert self.oracle.surface_area_mm2(m) == pytest.approx(2400.0)
        assert self.oracle.bbox_mm(m) == pytest.approx((20.0, 20.0, 20.0))
        assert self.oracle.centroid_mm(m) == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)
        assert self.oracle.body_count(m) == 1
        assert self.oracle.integrity(m).watertight

    def test_open_box_quotes_zero_volume(self):
        m = open_box()
        assert self.oracle.volume_mm3(m) == 0.0
        assert self.oracle.surface_area_mm2(m) == pytest.approx(2400.0 - 400.0)  # one 20x20 face removed
        verdict = self.oracle.integrity(m, scale_hint=20.0)
        assert not verdict.watertight
        assert verdict.boundary_edges > 0

    def test_two_bodies(self):
        m = two_bodies()
        assert self.oracle.body_count(m) == 2
        assert self.oracle.volume_mm3(m) == pytest.approx(2000.0)
        assert self.oracle.bbox_mm(m) == pytest.approx((40.0, 10.0, 10.0))

    def test_degenerate(self):
        m = degenerate()
        assert self.oracle.volume_mm3(m) == 0.0
        assert self.oracle.surface_area_mm2(m) == pytest.approx(0.0)
        assert not self.oracle.integrity(m).watertight

    @pytest.mark.parametrize("make", [closed_box, open_box, two_bodies, degenerate])
    def test_integrity_is_mesh_integrity_assess(self, make):
        """The default oracle IS mesh_integrity.assess — same verdict, same evidence."""
        assert TrimeshOracle().integrity(make(), 20.0) == assess(make(), 20.0)


# ---------------------------------------------------------------------------
# GeomCoreOracle adapter (a fake geom_core_py: no wheel needed)
# ---------------------------------------------------------------------------

class _FakeAnalyzer:
    loaded: ClassVar[list] = []

    def load_stl(self, path):
        data = Path(path).read_bytes()
        _FakeAnalyzer.loaded.append(len(data))
        # Binary STL: 80-byte header + uint32 count + 50 bytes per triangle.
        return len(data) >= 84

    def assess_integrity(self, scale_hint):
        return SimpleNamespace(watertight=True, boundary_edges=0, euler_number=2,
                               winding_consistent=True, volume=8000.0,
                               nonmanifold_edges=0, merge_tolerance=None,
                               inverted=False, notes=[])

    def get_volume(self):
        return 8000.0

    def get_surface_area(self):
        return 2400.0

    def get_bounding_box(self):
        return SimpleNamespace(x=20.0, y=20.0, z=20.0)

    def get_centroid(self):
        return SimpleNamespace(x=0.0, y=0.0, z=0.0)

    def get_body_count(self):
        return 1


FAKE_GC = SimpleNamespace(Analyzer=_FakeAnalyzer)


class TestGeomCoreOracleAdapter:
    def test_missing_module_raises(self, monkeypatch):
        monkeypatch.setattr(mesh_metrics, "geom_core_module", lambda: None)
        with pytest.raises(RuntimeError, match="geom-core is not installed"):
            GeomCoreOracle()

    def test_hands_geom_core_a_binary_stl_of_the_mesh(self):
        _FakeAnalyzer.loaded.clear()
        oracle = GeomCoreOracle(FAKE_GC)
        m = closed_box()
        assert oracle.volume_mm3(m) == 8000.0
        assert oracle.surface_area_mm2(m) == 2400.0
        assert oracle.bbox_mm(m) == (20.0, 20.0, 20.0)
        assert oracle.centroid_mm(m) == (0.0, 0.0, 0.0)
        assert oracle.body_count(m) == 1
        # 84 + 50 * 12 triangles: the whole box, as binary STL.
        assert set(_FakeAnalyzer.loaded) == {84 + 50 * len(m.faces)}

    def test_integrity_maps_every_field(self):
        verdict = GeomCoreOracle(FAKE_GC).integrity(closed_box())
        assert verdict == MeshIntegrity(True, 0, 2, True, 8000.0, nonmanifold_edges=0,
                                        merge_tolerance=None, notes=[])

    def test_guards_match_assess_for_non_meshes(self):
        oracle = GeomCoreOracle(FAKE_GC)
        assert oracle.integrity(trimesh.Scene()) == assess(trimesh.Scene())
        empty = trimesh.Trimesh(vertices=np.zeros((0, 3)), faces=np.zeros((0, 3), dtype=int))
        assert oracle.integrity(empty) == assess(empty)

    def test_volume_is_zero_unless_a_closed_solid(self):
        class Open(_FakeAnalyzer):
            def assess_integrity(self, scale_hint):
                r = super().assess_integrity(scale_hint)
                r.watertight = False
                return r
        assert GeomCoreOracle(SimpleNamespace(Analyzer=Open)).volume_mm3(closed_box()) == 0.0

    def test_unparseable_export_raises(self):
        class Refuses(_FakeAnalyzer):
            def load_stl(self, path):
                return False
        with pytest.raises(ValueError, match="could not parse"):
            GeomCoreOracle(SimpleNamespace(Analyzer=Refuses)).surface_area_mm2(closed_box())


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

class TestSelection:
    def test_default_is_trimesh(self):
        assert mesh_metrics.oracle_mode() == "trimesh"
        first, second = mesh_metrics._oracles()
        assert isinstance(first, TrimeshOracle) and second is None

    def test_unknown_mode_logs_an_error_and_uses_trimesh(self, monkeypatch, caplog):
        monkeypatch.setenv("MESH_ORACLE", "manifold")
        with caplog.at_level(logging.ERROR, logger="services.engine.mesh_metrics"):
            assert mesh_metrics.oracle_mode() == "trimesh"
        assert "not one of trimesh|geomcore|both" in caplog.text

    @pytest.mark.parametrize("mode", ["geomcore", "both"])
    def test_missing_wheel_logs_an_error_and_uses_trimesh(self, monkeypatch, caplog, mode):
        monkeypatch.setenv("MESH_ORACLE", mode)
        monkeypatch.setattr(mesh_metrics, "geom_core_module", lambda: None)
        with caplog.at_level(logging.ERROR, logger="services.engine.mesh_metrics"):
            first, second = mesh_metrics._oracles()
        assert isinstance(first, TrimeshOracle) and second is None
        assert "geom-core wheel is not installed" in caplog.text

    def test_geomcore_mode_uses_geomcore(self, monkeypatch):
        monkeypatch.setenv("MESH_ORACLE", "geomcore")
        monkeypatch.setattr(mesh_metrics, "geom_core_module", lambda: FAKE_GC)
        first, second = mesh_metrics._oracles()
        assert isinstance(first, GeomCoreOracle) and second is None

    def test_both_mode_keeps_trimesh_authoritative(self, monkeypatch):
        monkeypatch.setenv("MESH_ORACLE", "both")
        monkeypatch.setattr(mesh_metrics, "geom_core_module", lambda: FAKE_GC)
        first, second = mesh_metrics._oracles()
        assert isinstance(first, TrimeshOracle) and isinstance(second, GeomCoreOracle)


# ---------------------------------------------------------------------------
# Parity (both): an injected oracle that disagrees
# ---------------------------------------------------------------------------

class _Disagrees(TrimeshOracle):
    name = "fake"

    def volume_mm3(self, mesh):
        return super().volume_mm3(mesh) + 1.0

    def integrity(self, mesh, scale_hint=None):
        v = super().integrity(mesh, scale_hint)
        v.boundary_edges += 3
        return v


class _Raises(TrimeshOracle):
    def surface_area_mm2(self, mesh):
        raise ValueError("boom")


class TestParity:
    def test_mismatch_increments_the_counter_and_returns_trimesh(self, caplog):
        before = mismatches("volume_mm3")
        area_before = mismatches("surface_area_mm2")
        with caplog.at_level(logging.INFO, logger="services.engine.mesh_metrics"):
            result = mesh_metrics.quote_metrics(closed_box(), slug="box",
                                                primary=TrimeshOracle(), secondary=_Disagrees())
        assert result == QuoteMetrics(pytest.approx(8000.0), pytest.approx(2400.0),
                                      pytest.approx((20.0, 20.0, 20.0)))
        assert mismatches("volume_mm3") == before + 1
        assert mismatches("surface_area_mm2") == area_before  # agreed: not counted
        record = next(r for r in caplog.records if '"metric": "volume_mm3"' in r.getMessage())
        assert record.levelno == logging.WARNING
        for key in ('"slug": "box"', '"mode": "both"', '"trimesh": 8000.0',
                    '"geomcore": 8001.0', '"delta": 1.0', '"match": false'):
            assert key in record.getMessage()

    def test_integrity_mismatch_is_counted_per_field(self):
        before = mismatches("integrity.boundary_edges")
        steady = mismatches("integrity.watertight")
        verdict = mesh_metrics.integrity(open_box(), 20.0, slug="open",
                                         primary=TrimeshOracle(), secondary=_Disagrees())
        assert verdict == assess(open_box(), 20.0)
        assert mismatches("integrity.boundary_edges") == before + 1
        assert mismatches("integrity.watertight") == steady

    def test_a_failing_secondary_is_a_mismatch_not_a_crash(self):
        before = mismatches("surface_area_mm2")
        result = mesh_metrics.quote_metrics(closed_box(), primary=TrimeshOracle(), secondary=_Raises())
        assert result.surface_area_mm2 == pytest.approx(2400.0)
        assert mismatches("surface_area_mm2") == before + 1

    def test_agreement_within_tolerance(self):
        assert mesh_metrics.record_parity("s", "m", 8000.0, 8000.0 * (1 + 1e-9))
        assert mesh_metrics.record_parity("s", "m", (1.0, 2.0), [1.0, 2.0])
        assert not mesh_metrics.record_parity("s", "m", True, False)
        assert not mesh_metrics.record_parity("s", "m", None, 2)


# ---------------------------------------------------------------------------
# Render completion and the Cotiza export
# ---------------------------------------------------------------------------

class TestObserveRender:
    def test_default_mode_does_not_load_the_mesh(self, monkeypatch, tmp_path):
        def explode(*a, **kw):
            raise AssertionError("trimesh.load must not run under MESH_ORACLE=trimesh")
        monkeypatch.setattr(mesh_metrics.trimesh, "load", explode)
        assert mesh_metrics.observe_render(str(tmp_path / "x.stl"), slug="s", part="p") is None

    def test_both_mode_assesses_and_records(self, monkeypatch, tmp_path):
        path = tmp_path / "box.stl"
        closed_box().export(path)
        monkeypatch.setenv("MESH_ORACLE", "both")
        monkeypatch.setattr(mesh_metrics, "_geomcore_or_none", lambda: _Disagrees())
        before = mismatches("integrity.boundary_edges")
        verdict = mesh_metrics.observe_render(str(path), slug="s", part="p")
        assert verdict.watertight
        assert mismatches("integrity.boundary_edges") == before + 1

    def test_unreadable_render_is_logged_not_raised(self, monkeypatch, tmp_path, caplog):
        monkeypatch.setenv("MESH_ORACLE", "geomcore")
        monkeypatch.setattr(mesh_metrics, "geom_core_module", lambda: FAKE_GC)
        with caplog.at_level(logging.WARNING, logger="services.engine.mesh_metrics"):
            assert mesh_metrics.observe_render(str(tmp_path / "missing.stl"), slug="s") is None
        assert "skipped" in caplog.text


class TestCotizaExportThroughTheSeam:
    def test_both_mode_sends_trimesh_numbers_and_counts_disagreement(self, monkeypatch, tmp_path):
        from routes.integrations.cotiza_export import _extract_geometry_metrics

        path = tmp_path / "box.stl"
        closed_box().export(path)
        monkeypatch.setenv("MESH_ORACLE", "both")
        monkeypatch.setattr(mesh_metrics, "_geomcore_or_none", lambda: _Disagrees())
        before = mismatches("volume_mm3")
        result = _extract_geometry_metrics(str(path), slug="box")
        assert result == {"volume_cm3": 8.0, "surface_area_cm2": 24.0,
                          "bounding_box_mm": {"x": 20.0, "y": 20.0, "z": 20.0}}
        assert mismatches("volume_mm3") == before + 1

    def test_default_mode_matches_the_pre_seam_formula(self, tmp_path):
        from routes.integrations.cotiza_export import _extract_geometry_metrics

        path = tmp_path / "open.stl"
        open_box().export(path)
        m = trimesh.load(str(path), force="mesh")
        result = _extract_geometry_metrics(str(path))
        assert result["volume_cm3"] == round((abs(m.volume) if m.is_volume else 0.0) / 1000.0, 4)
        assert result["surface_area_cm2"] == round(m.area / 100.0, 4)
