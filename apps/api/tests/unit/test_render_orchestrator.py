"""
Unit tests for render_orchestrator utilities.

Focuses on the _post_render_convert helper which was fixed to return
separate url (download) and viewer_url (GLB) fields rather than replacing
the STL path with the GLB path unconditionally.
"""
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# _post_render_convert
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_static_folder(tmp_path, monkeypatch):
    """Redirect STATIC_FOLDER to a tmp dir so file writes land safely."""
    monkeypatch.setattr(
        "services.engine.render_orchestrator.STATIC_FOLDER",
        str(tmp_path),
    )
    return tmp_path


def _make_stl(path: str) -> None:
    """Write a minimal ASCII STL so os.path.getsize works."""
    with open(path, "w") as f:
        f.write("solid test\nendsolid test\n")


class TestPostRenderConvert:
    """Tests for _post_render_convert — the STL/GLB separation fix."""

    def _call(self, tmp_path, output_filename, actual_format, export_format,
              stl_to_glb_succeeds=True, convert_mesh_succeeds=True):
        from services.engine.render_orchestrator import _post_render_convert

        output_path = str(tmp_path / output_filename)
        _make_stl(output_path)

        stl_prefix = "pfx_"
        part = "body"

        with patch("services.engine.render_orchestrator.stl_to_glb") as mock_glb, \
             patch("services.engine.render_orchestrator.convert_mesh") as mock_conv:

            mock_glb.side_effect = lambda src, dst: (
                (open(dst, "w").write("GLB"), True)[1]
                if stl_to_glb_succeeds else False
            )
            mock_conv.side_effect = lambda src, dst: (
                (open(dst, "w").write("CONV"), True)[1]
                if convert_mesh_succeeds else False
            )

            result = _post_render_convert(
                output_path, output_filename, part, stl_prefix,
                actual_format, export_format,
            )

        return result

    def test_stl_request_returns_stl_url_not_glb(self, tmp_path):
        """Core fix: when export_format='stl', url must point to the .stl file."""
        serve_path, serve_filename, viewer_filename = self._call(
            tmp_path,
            output_filename="pfx_body.stl",
            actual_format="stl",
            export_format="stl",
        )
        assert serve_filename.endswith(".stl"), (
            f"url should be .stl, got: {serve_filename}"
        )

    def test_stl_request_populates_viewer_filename(self, tmp_path):
        """When export_format='stl' and GLB conversion succeeds, viewer_filename is set."""
        _, _, viewer_filename = self._call(
            tmp_path,
            output_filename="pfx_body.stl",
            actual_format="stl",
            export_format="stl",
            stl_to_glb_succeeds=True,
        )
        assert viewer_filename is not None
        assert viewer_filename.endswith(".glb"), (
            f"viewer_filename should be .glb, got: {viewer_filename}"
        )

    def test_stl_request_viewer_filename_none_when_glb_fails(self, tmp_path):
        """When GLB conversion fails, viewer_filename is None (no broken viewer URL)."""
        _, _, viewer_filename = self._call(
            tmp_path,
            output_filename="pfx_body.stl",
            actual_format="stl",
            export_format="stl",
            stl_to_glb_succeeds=False,
        )
        assert viewer_filename is None

    def test_non_stl_format_no_glb_conversion(self, tmp_path):
        """For non-stl export_format (e.g. 3mf), no GLB conversion is attempted."""
        output_filename = "pfx_body.3mf"
        _make_stl(str(tmp_path / output_filename))

        with patch("services.engine.render_orchestrator.stl_to_glb") as mock_glb, \
             patch("services.engine.render_orchestrator.convert_mesh") as mock_conv:
            mock_conv.return_value = True
            mock_glb.return_value = True

            from services.engine.render_orchestrator import _post_render_convert
            serve_path, serve_filename, viewer_filename = _post_render_convert(
                str(tmp_path / output_filename), output_filename, "body",
                "pfx_", "3mf", "3mf",
            )

        mock_glb.assert_not_called()
        assert viewer_filename is None

    def test_returns_three_values(self, tmp_path):
        """Return type is always a 3-tuple (serve_path, serve_filename, viewer_filename)."""
        result = self._call(
            tmp_path,
            output_filename="pfx_body.stl",
            actual_format="stl",
            export_format="stl",
        )
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_glb_format_passthrough(self, tmp_path):
        """Explicit glb export_format: no secondary GLB conversion (already GLB)."""
        output_filename = "pfx_body.glb"
        _make_stl(str(tmp_path / output_filename))

        with patch("services.engine.render_orchestrator.stl_to_glb") as mock_glb, \
             patch("services.engine.render_orchestrator.convert_mesh"):

            from services.engine.render_orchestrator import _post_render_convert
            _, serve_filename, viewer_filename = _post_render_convert(
                str(tmp_path / output_filename), output_filename, "body",
                "pfx_", "glb", "glb",
            )

        mock_glb.assert_not_called()
        assert viewer_filename is None
        assert serve_filename.endswith(".glb")


def test_render_worker_unavailable_when_heartbeat_missing(monkeypatch):
    """Render worker is unavailable when no heartbeat key exists in Redis."""
    import services.engine.render_orchestrator as render_orchestrator

    class _FakeRedis:
        def get(self, _key):
            return None

    monkeypatch.setattr(render_orchestrator, "r", _FakeRedis())
    assert not render_orchestrator.is_render_worker_available()


def test_render_worker_available_with_recent_heartbeat(monkeypatch):
    """Render worker becomes available when heartbeat timestamp is fresh."""
    import time
    import services.engine.render_orchestrator as render_orchestrator

    class _FakeRedis:
        def get(self, _key):
            return str(int(time.time()))

    monkeypatch.setattr(render_orchestrator, "r", _FakeRedis())
    monkeypatch.setattr(render_orchestrator, "RENDER_WORKER_HEARTBEAT_TTL_SECONDS", 10)
    assert render_orchestrator.is_render_worker_available()


def test_render_worker_status_includes_queue_and_active_jobs(monkeypatch):
    """Render worker status includes operational queue depth and active job count."""
    import time
    import services.engine.render_orchestrator as render_orchestrator

    class _FakeRedis:
        def get(self, _key):
            return str(int(time.time()) - 3)

        def llen(self, _key):
            return 7

        def scard(self, _key):
            return 2

    monkeypatch.setattr(render_orchestrator, "r", _FakeRedis())
    monkeypatch.setattr(render_orchestrator, "RENDER_WORKER_HEARTBEAT_TTL_SECONDS", 10)

    status = render_orchestrator.get_render_worker_status()
    assert status["available"] is True
    assert status["age_seconds"] >= 3
    assert status["queue_depth"] == 7
    assert status["active_jobs"] == 2


def test_render_parts_sync_rejects_when_worker_unavailable(monkeypatch):
    """Sync rendering should reject quickly if no worker heartbeat is available."""
    import services.engine.render_orchestrator as render_orchestrator

    monkeypatch.setattr(render_orchestrator, "is_render_worker_available", lambda: False)
    generated_parts, message, cache_stats = render_orchestrator.render_parts_sync(
        {},
        {
            "parts": ["body"],
            "stl_prefix": "test_",
            "export_format": "stl",
            "project_slug": "sample",
            "scad_filename": "sample.scad",
            "params": {},
            "static_stl_map": {},
        },
        "openscad",
        "/tmp/sample.scad",
        "stl",
        "guest",
    )
    assert generated_parts is None
    assert message == "Render worker unavailable or not healthy"
    assert cache_stats == (0, 1)


def test_render_parts_stream_emits_unavailable_error_when_worker_unavailable(monkeypatch):
    """Stream rendering should emit explicit unavailable error and complete events."""
    import json
    import services.engine.render_orchestrator as render_orchestrator

    monkeypatch.setattr(render_orchestrator, "is_render_worker_available", lambda: False)
    stream = render_orchestrator.render_parts_stream(
        {},
        {
            "parts": ["body"],
            "stl_prefix": "test_",
            "export_format": "stl",
            "project_slug": "sample",
            "scad_filename": "sample.scad",
            "params": {},
            "static_stl_map": {},
        },
        "openscad",
        "/tmp/sample.scad",
        "stl",
    )
    events = [json.loads(event.split("data: ", 1)[1].strip()) for event in stream]
    assert len(events) == 2
    assert events[0]["event"] == "error"
    assert events[0]["part"] == "body"
    assert events[1]["event"] == "complete"
