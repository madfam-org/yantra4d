"""
Unit tests for render_orchestrator utilities.

Focuses on the _post_render_convert helper which was fixed to return
separate url (download) and viewer_url (GLB) fields rather than replacing
the STL path with the GLB path unconditionally.
"""
from unittest.mock import patch

import pytest

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

        def fake_stl_to_glb(src, dst):
            if not stl_to_glb_succeeds:
                return False
            with open(dst, "w") as f:
                f.write("GLB")
            return True

        def fake_convert_mesh(src, dst):
            if not convert_mesh_succeeds:
                return False
            with open(dst, "w") as f:
                f.write("CONV")
            return True

        with patch("services.engine.render_orchestrator.stl_to_glb") as mock_glb, \
             patch("services.engine.render_orchestrator.convert_mesh") as mock_conv:

            mock_glb.side_effect = fake_stl_to_glb
            mock_conv.side_effect = fake_convert_mesh

            result = _post_render_convert(
                output_path, output_filename, part, stl_prefix,
                actual_format, export_format,
            )

        return result

    def test_stl_request_returns_stl_url_not_glb(self, tmp_path):
        """Core fix: when export_format='stl', url must point to the .stl file."""
        _serve_path, serve_filename, _viewer_filename = self._call(
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
            _serve_path, _serve_filename, viewer_filename = _post_render_convert(
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
    from services.engine import render_orchestrator

    class _FakeRedis:
        def get(self, _key):
            return None

    monkeypatch.setattr(render_orchestrator, "r", _FakeRedis())
    assert not render_orchestrator.is_render_worker_available()


def test_render_worker_available_with_recent_heartbeat(monkeypatch):
    """Render worker becomes available when heartbeat timestamp is fresh."""
    import time

    from services.engine import render_orchestrator

    class _FakeRedis:
        def get(self, _key):
            return str(int(time.time()))

    monkeypatch.setattr(render_orchestrator, "r", _FakeRedis())
    monkeypatch.setattr(render_orchestrator, "RENDER_WORKER_HEARTBEAT_TTL_SECONDS", 10)
    assert render_orchestrator.is_render_worker_available()


def test_render_worker_status_includes_queue_and_active_jobs(monkeypatch):
    """Render worker status includes operational queue depth and active job count."""
    import json
    import time

    from services.engine import render_orchestrator

    now = int(time.time())

    class _FakeRedis:
        """Two active jobs, both holding a fresh lease."""

        def get(self, key):
            if key.startswith(render_orchestrator.ACTIVE_RENDER_META_PREFIX):
                job_id = key[len(render_orchestrator.ACTIVE_RENDER_META_PREFIX):]
                return json.dumps({"job_id": job_id, "started_at": now - 3})
            return str(now - 3)

        def llen(self, _key):
            return 7

        def scard(self, _key):
            return 2

        def smembers(self, _key):
            return {"job-a", "job-b"}

    monkeypatch.setattr(render_orchestrator, "r", _FakeRedis())
    monkeypatch.setattr(render_orchestrator, "RENDER_WORKER_HEARTBEAT_TTL_SECONDS", 10)

    status = render_orchestrator.get_render_worker_status()
    assert status["available"] is True
    assert status["age_seconds"] >= 3
    assert status["queue_depth"] == 7
    assert status["active_jobs"] == 2


def test_render_parts_sync_rejects_when_worker_unavailable(monkeypatch):
    """Sync rendering should reject quickly if no worker heartbeat is available."""
    from services.engine import render_orchestrator

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

    from services.engine import render_orchestrator

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
    assert len(events) == 3
    # The stream now opens by handing the client its cancellation identity.
    assert events[0]["event"] == "job"
    assert events[0]["job_ids"] == []
    assert events[1]["event"] == "error"
    assert events[1]["part"] == "body"
    assert events[2]["event"] == "complete"


# ---------------------------------------------------------------------------
# Payload contract: documented shape is
#   {mode, parameters, parts, export_format?, project?}
# The implementation has been silently tolerant of two deviations:
#   1. flattened parameters (params at the top level, no 'parameters' key)
#   2. a missing 'mode' (silently renders manifest.modes[0] with HTTP 200)
# Both now log a structured deprecation warning by default, and return a
# RenderPayloadError when RENDER_STRICT_PAYLOAD is enabled.
# ---------------------------------------------------------------------------

def _payload_error_cls():
    """Resolve RenderPayloadError lazily (sys.path is set up by conftest)."""
    from services.engine.render_orchestrator import RenderPayloadError
    return RenderPayloadError


class _ContractMockManifest:
    """Minimal manifest double mirroring the pattern in tests/e2e/test_render_api.py."""

    def __init__(self):
        self.slug = "contract-project"
        self.engine = "openscad"
        self.modes = [
            {"id": "unit", "parts": ["body"], "scad_file": "unit.scad"},
            {"id": "assembly", "parts": ["body", "lid"], "scad_file": "assembly.scad"},
        ]
        self.parts = [{"id": "body", "render_mode": 0}, {"id": "lid", "render_mode": 1}]
        self.parameters = []

    def mode_engine(self, mode_id=None):
        return self.engine

    def get_scad_file_for_mode(self, mode_id):
        for mode in self.modes:
            if mode["id"] == mode_id:
                return mode["scad_file"]
        return None

    def get_parts_for_mode(self, mode_id):
        for mode in self.modes:
            if mode["id"] == mode_id:
                return mode["parts"]
        return []

    def get_parts_map(self):
        return {"unit.scad": ["body"], "assembly.scad": ["body", "lid"]}

    def get_allowed_files(self):
        return {"unit.scad": "unit_path", "assembly.scad": "assembly_path"}

    def get_mode_map(self):
        return {"body": 0, "lid": 1}

    def get_static_stl_map(self):
        return {}


@pytest.fixture
def contract_env(monkeypatch):
    """Patch the orchestrator's manifest/params/hash seams for payload-shape tests."""
    monkeypatch.setattr(
        "services.engine.render_orchestrator.get_manifest",
        lambda *args: _ContractMockManifest(),
    )
    # validate_params echoes its input so tests can observe which container was used.
    monkeypatch.setattr(
        "services.engine.render_orchestrator.validate_params",
        lambda raw, *args: dict(raw),
    )
    monkeypatch.setattr(
        "services.engine.render_orchestrator.compute_scad_hash",
        lambda *args: "deadbeef",
    )
    # Default state: strict mode off, regardless of the ambient environment.
    monkeypatch.delenv("RENDER_STRICT_PAYLOAD", raising=False)


class TestPayloadContractLenientDefault:
    """Default behavior must stay byte-for-byte unchanged — only louder in the logs."""

    def test_flattened_params_still_render(self, contract_env, caplog):
        """A flat payload keeps working, but logs a deprecation warning."""
        from services.engine.render_orchestrator import extract_render_payload

        with caplog.at_level("WARNING"):
            payload = extract_render_payload(
                {"project": "contract-project", "mode": "unit", "size": 20}
            )

        assert not isinstance(payload, _payload_error_cls())
        assert payload["params"]["size"] == 20
        assert any("no 'parameters' key" in rec.message for rec in caplog.records)

    def test_flat_deprecation_warning_names_project_and_origin(self, contract_env, caplog):
        """The warning must carry the project slug and the caller's route."""
        from services.engine.render_orchestrator import extract_render_payload

        with caplog.at_level("WARNING"):
            extract_render_payload({"project": "contract-project", "mode": "unit", "size": 20})

        rendered = "\n".join(rec.getMessage() for rec in caplog.records)
        assert "contract-project" in rendered
        assert "origin=" in rendered

    def test_nested_params_emit_no_deprecation_warning(self, contract_env, caplog):
        """The documented shape is the quiet path."""
        from services.engine.render_orchestrator import extract_render_payload

        with caplog.at_level("WARNING"):
            payload = extract_render_payload(
                {"project": "contract-project", "mode": "unit", "parameters": {"size": 20}}
            )

        assert payload["params"] == {"size": 20}
        assert not any("no 'parameters' key" in rec.message for rec in caplog.records)

    def test_missing_mode_still_renders_first_mode(self, contract_env, caplog):
        """Absent mode keeps falling through to modes[0], but logs a warning."""
        from services.engine.render_orchestrator import extract_render_payload

        with caplog.at_level("WARNING"):
            payload = extract_render_payload(
                {"project": "contract-project", "parameters": {"size": 20}}
            )

        assert payload["mode"] == "unit"
        assert payload["scad_filename"] == "unit.scad"
        assert any("no 'mode' supplied" in rec.message for rec in caplog.records)

    def test_explicit_mode_emits_no_mode_warning(self, contract_env, caplog):
        """An explicit mode is the quiet path."""
        from services.engine.render_orchestrator import extract_render_payload

        with caplog.at_level("WARNING"):
            payload = extract_render_payload(
                {"project": "contract-project", "mode": "assembly", "parameters": {"size": 20}}
            )

        assert payload["mode"] == "assembly"
        assert not any("no 'mode' supplied" in rec.message for rec in caplog.records)

    def test_present_but_unknown_mode_still_errors(self, contract_env):
        """Unknown mode keeps its existing 400 path — unchanged by this work."""
        from services.engine.render_orchestrator import extract_render_payload

        result = extract_render_payload(
            {"project": "contract-project", "mode": "nope", "parameters": {}}
        )
        assert isinstance(result, _payload_error_cls())
        assert "Invalid mode id" in result.message

    def test_flat_and_nested_param_hashes_diverge(self, contract_env):
        """Documents the cache-key divergence that motivated this hardening."""
        from services.engine.render_orchestrator import extract_render_payload

        flat = extract_render_payload(
            {"project": "contract-project", "mode": "unit", "size": 20}
        )
        nested = extract_render_payload(
            {"project": "contract-project", "mode": "unit", "parameters": {"size": 20}}
        )
        # The flat form folds 'project'/'mode' into the parameter map, so the
        # resulting stl_prefix (param_hash) is NOT the same as the nested form's.
        assert flat["stl_prefix"] != nested["stl_prefix"]

    def test_flat_payload_no_longer_drops_target_material(self, contract_env, monkeypatch):
        """Flat callers now reach material compensation instead of silently losing it."""
        seen = {}
        monkeypatch.setattr(
            "services.engine.render_orchestrator._inject_material_compensations",
            lambda params, mat: seen.setdefault("mat", mat),
        )

        from services.engine.render_orchestrator import extract_render_payload

        extract_render_payload(
            {"project": "contract-project", "mode": "unit", "target_material": "pla"}
        )
        assert seen.get("mat") == "pla"

    def test_nested_target_material_still_injected(self, contract_env, monkeypatch):
        """The nested path keeps its existing behavior."""
        seen = {}
        monkeypatch.setattr(
            "services.engine.render_orchestrator._inject_material_compensations",
            lambda params, mat: seen.setdefault("mat", mat),
        )

        from services.engine.render_orchestrator import extract_render_payload

        extract_render_payload({
            "project": "contract-project",
            "mode": "unit",
            "parameters": {"size": 20, "target_material": "petg"},
        })
        assert seen.get("mat") == "petg"


class TestPayloadContractStrictMode:
    """RENDER_STRICT_PAYLOAD=true turns both tolerated shapes into 400s."""

    def test_flattened_params_rejected(self, contract_env, monkeypatch):
        monkeypatch.setenv("RENDER_STRICT_PAYLOAD", "true")
        from services.engine.render_orchestrator import extract_render_payload

        result = extract_render_payload(
            {"project": "contract-project", "mode": "unit", "size": 20}
        )
        assert isinstance(result, _payload_error_cls())
        assert "'parameters'" in result.message
        assert "RENDER_STRICT_PAYLOAD" in result.message

    def test_missing_mode_rejected(self, contract_env, monkeypatch):
        monkeypatch.setenv("RENDER_STRICT_PAYLOAD", "true")
        from services.engine.render_orchestrator import extract_render_payload

        result = extract_render_payload(
            {"project": "contract-project", "parameters": {"size": 20}}
        )
        assert isinstance(result, _payload_error_cls())
        assert "'mode'" in result.message
        assert "unit" in result.message  # names the mode it refused to assume

    def test_documented_shape_accepted_under_strict(self, contract_env, monkeypatch):
        """Strict mode must not reject the contract it is enforcing."""
        monkeypatch.setenv("RENDER_STRICT_PAYLOAD", "true")
        from services.engine.render_orchestrator import extract_render_payload

        payload = extract_render_payload({
            "project": "contract-project",
            "mode": "assembly",
            "parameters": {"size": 20},
            "parts": ["body", "lid"],
            "export_format": "stl",
        })
        assert not isinstance(payload, _payload_error_cls())
        assert payload["mode"] == "assembly"
        assert payload["params"] == {"size": 20}

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on"])
    def test_truthy_flag_values_enable_strict(self, contract_env, monkeypatch, value):
        monkeypatch.setenv("RENDER_STRICT_PAYLOAD", value)
        from services.engine.render_orchestrator import extract_render_payload

        result = extract_render_payload({"project": "contract-project", "mode": "unit", "size": 1})
        assert isinstance(result, _payload_error_cls())

    @pytest.mark.parametrize("value", ["", "0", "false", "off", "no"])
    def test_falsy_flag_values_keep_lenient_default(self, contract_env, monkeypatch, value):
        monkeypatch.setenv("RENDER_STRICT_PAYLOAD", value)
        from services.engine.render_orchestrator import extract_render_payload

        payload = extract_render_payload({"project": "contract-project", "mode": "unit", "size": 1})
        assert not isinstance(payload, _payload_error_cls())


# ---------------------------------------------------------------------------
# SSE per-part deadline
# ---------------------------------------------------------------------------

def test_stream_part_timeout_default_is_180():
    """Default raised 120 -> 180 for cold made-to-measure loft headroom."""
    from services.engine import render_orchestrator

    assert render_orchestrator.RENDER_STREAM_PART_TIMEOUT_SECONDS == 180


def test_stream_part_timeout_is_env_tunable(monkeypatch):
    """RENDER_STREAM_PART_TIMEOUT_SECONDS overrides the default at import time."""
    import importlib

    monkeypatch.setenv("RENDER_STREAM_PART_TIMEOUT_SECONDS", "240")
    from services.engine import render_orchestrator

    reloaded = importlib.reload(render_orchestrator)
    try:
        assert reloaded.RENDER_STREAM_PART_TIMEOUT_SECONDS == 240
    finally:
        monkeypatch.delenv("RENDER_STREAM_PART_TIMEOUT_SECONDS", raising=False)
        importlib.reload(render_orchestrator)


def test_stream_part_timeout_stays_under_subprocess_ceiling():
    """The stream deadline must not exceed the subprocess ceiling it waits on."""
    from services.engine import render_orchestrator

    assert render_orchestrator.RENDER_STREAM_PART_TIMEOUT_SECONDS < 300
