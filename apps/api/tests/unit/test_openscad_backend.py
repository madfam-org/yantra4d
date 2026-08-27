"""Tests for OpenSCAD geometry-backend probing and selection.

Both probe outcomes are covered with mocks so the suite is meaningful on any
runner: one where the installed OpenSCAD advertises --backend (2023+) and one
where it does not (older release builds). See test_render_cache_backend.py for
the cache-key half of this change.
"""
from unittest.mock import MagicMock, patch

import pytest

from services.engine import openscad


@pytest.fixture(autouse=True)
def _clean_probe(monkeypatch):
    """Each test gets a fresh probe and a default (auto) backend env."""
    monkeypatch.delenv("YANTRA4D_OPENSCAD_BACKEND", raising=False)
    openscad.reset_backend_probe()
    yield
    openscad.reset_backend_probe()


def _fake_run(help_text: str, version: str = "OpenSCAD version 2026.02.13"):
    """Build a subprocess.run stub answering --version then --help."""
    def _run(cmd, **kwargs):
        if "--version" in cmd:
            return MagicMock(stdout=version, stderr="")
        return MagicMock(stdout=help_text, stderr="")
    return _run


HELP_WITH_BACKEND = (
    "  --backend arg   3D rendering backend to use: 'CGAL' (old/slow) or "
    "'Manifold' (new/fast)\n"
)
HELP_WITHOUT_BACKEND = "  --render arg    for full geometry evaluation\n"


# ---------------------------------------------------------------------------
# Probe: binary DOES support --backend
# ---------------------------------------------------------------------------
class TestProbeSupported:
    @pytest.fixture(autouse=True)
    def _patch(self, monkeypatch):
        monkeypatch.setattr(openscad.subprocess, "run", _fake_run(HELP_WITH_BACKEND))

    def test_probe_reports_supported(self):
        probe = openscad.get_backend_probe()
        assert probe["supported"] is True
        assert "2026.02.13" in probe["version"]

    def test_auto_selects_manifold(self):
        assert openscad.effective_backend() == "Manifold"

    def test_explicit_cgal_is_honoured(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_OPENSCAD_BACKEND", "cgal")
        assert openscad.effective_backend() == "CGAL"

    def test_explicit_manifold_is_honoured(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_OPENSCAD_BACKEND", "manifold")
        assert openscad.effective_backend() == "Manifold"

    def test_unknown_env_value_falls_back_to_auto(self, monkeypatch):
        monkeypatch.setenv("YANTRA4D_OPENSCAD_BACKEND", "quantum")
        assert openscad.effective_backend() == "Manifold"

    def test_command_carries_backend_flag(self, monkeypatch):
        monkeypatch.setattr("config.Config.OPENSCAD_PATH", "openscad")
        cmd = openscad.build_openscad_command("/out.stl", "/in.scad", {})
        assert "--backend=Manifold" in cmd

    def test_probe_runs_once_and_is_cached(self):
        with patch.object(
            openscad, "_probe_openscad_backend",
            wraps=openscad._probe_openscad_backend
        ) as spy:
            openscad.reset_backend_probe()
            openscad.get_backend_probe()
            openscad.get_backend_probe()
            openscad.effective_backend()
            # A subprocess probe per render would spend the win it delivers.
            assert spy.call_count == 1


# ---------------------------------------------------------------------------
# Probe: binary does NOT support --backend
# ---------------------------------------------------------------------------
class TestProbeUnsupported:
    @pytest.fixture(autouse=True)
    def _patch(self, monkeypatch):
        monkeypatch.setattr(
            openscad.subprocess, "run",
            _fake_run(HELP_WITHOUT_BACKEND, "OpenSCAD version 2021.01"),
        )

    def test_probe_reports_unsupported(self):
        assert openscad.get_backend_probe()["supported"] is False

    def test_no_backend_selected(self):
        assert openscad.effective_backend() is None

    def test_explicit_request_degrades_rather_than_breaking(self, monkeypatch):
        # Passing a flag this binary rejects would abort every render.
        monkeypatch.setenv("YANTRA4D_OPENSCAD_BACKEND", "manifold")
        assert openscad.effective_backend() is None

    def test_command_is_byte_identical_to_before(self, monkeypatch):
        monkeypatch.setattr("config.Config.OPENSCAD_PATH", "openscad")
        cmd = openscad.build_openscad_command("/out.stl", "/in.scad", {"size": 10})
        assert not any("--backend" in a for a in cmd)
        assert cmd == ["openscad", "-o", "/out.stl", "-D", "size=10", "/in.scad"]


# ---------------------------------------------------------------------------
# Probe failure must never break rendering
# ---------------------------------------------------------------------------
class TestProbeFailure:
    def test_missing_binary_degrades_to_no_flag(self, monkeypatch):
        def _boom(cmd, **kwargs):
            raise FileNotFoundError("openscad: no such file")
        monkeypatch.setattr(openscad.subprocess, "run", _boom)
        assert openscad.get_backend_probe()["supported"] is False
        assert openscad.effective_backend() is None

    def test_probe_timeout_degrades_to_no_flag(self, monkeypatch):
        import subprocess as sp

        def _slow(cmd, **kwargs):
            raise sp.TimeoutExpired(cmd, 15)
        monkeypatch.setattr(openscad.subprocess, "run", _slow)
        assert openscad.effective_backend() is None


# ---------------------------------------------------------------------------
# Positional contract the rest of the codebase depends on
# ---------------------------------------------------------------------------
class TestCommandShapeUnchanged:
    """run_render extracts the output path by scanning for -o, and
    tests/integration/test_openscad_service.py asserts cmd[1]/cmd[2]/cmd[-1].
    The backend flag must not disturb any of that."""

    @pytest.fixture(autouse=True)
    def _patch(self, monkeypatch):
        monkeypatch.setattr(openscad.subprocess, "run", _fake_run(HELP_WITH_BACKEND))
        monkeypatch.setattr("config.Config.OPENSCAD_PATH", "openscad")

    def test_output_flag_stays_at_index_one(self):
        cmd = openscad.build_openscad_command("/out.stl", "/in.scad", {"a": 1})
        assert cmd[1] == "-o"
        assert cmd[2] == "/out.stl"
        assert cmd[-1] == "/in.scad"

    def test_params_still_present(self):
        cmd = openscad.build_openscad_command("/out.stl", "/in.scad", {"a": 1}, mode_id=2)
        assert "a=1" in cmd
        assert "render_mode=2" in cmd
