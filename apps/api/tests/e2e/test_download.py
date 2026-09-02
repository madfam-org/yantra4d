"""Tests for download endpoints."""
import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def tmp_projects(tmp_path):
    """Create a temp project dir with a manifest and files."""
    project_dir = tmp_path / "test-project"
    project_dir.mkdir()

    manifest = {
        "project": {"thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner", "name": "Test", "slug": "test-project", "version": "1.0.0"},
        "modes": [{"id": "single", "scad_file": "main.scad", "label": "Single", "parts": ["body"], "estimate": {"base_units": 1, "formula": "constant"}}],
        "parts": [{"id": "body", "render_mode": 1, "label": "Body", "default_color": "#FF0000"}],
        "parameters": [],
        "estimate_constants": {"base_time": 1, "per_unit": 0.1, "per_part": 0.5},
    }
    (project_dir / "project.json").write_text(json.dumps(manifest))
    (project_dir / "main.scad").write_text("cube(10);")

    exports_dir = project_dir / "exports"
    exports_dir.mkdir()
    (exports_dir / "test.stl").write_bytes(b"solid test\nendsolid")
    (exports_dir / "test.3mf").write_bytes(b"solid test\nendsolid")
    (exports_dir / "test.off").write_bytes(b"test off mesh")
    # Premium-only formats per tiers.json: guest/essentials must not retrieve
    # these even when the artifact filename is known.
    (exports_dir / "test.step").write_bytes(b"ISO-10303-21;")
    (exports_dir / "test.glb").write_bytes(b"glTF binary")

    return tmp_path


@contextmanager
def auth_client(tmp_projects, tier=None):
    """Client on an AUTH_ENABLED app, optionally carrying a token for `tier`.

    Yields ``(client, headers)``. ``tier=None`` is an anonymous caller, which
    ``resolve_tier`` seats on ``guest``.
    """
    claims = None
    if tier is not None:
        claims = {
            "sub": "user123",
            "iss": "https://auth.madfam.io",
            "exp": 9999999999,
            "yantra4d_tier": tier,
        }

    with patch("config.Config.PROJECTS_DIR", tmp_projects), \
         patch("config.Config.STATIC_DIR", tmp_projects / "static"), \
         patch("config.Config.AUTH_ENABLED", True):
        (tmp_projects / "static").mkdir(exist_ok=True)
        application = create_app()
        application.config["TESTING"] = True

        import manifest as manifest_mod
        manifest_mod.manifest_service._manifest_cache.clear()

        if claims is None:
            yield application.test_client(), {}
        else:
            with patch("middleware.auth.decode_token", return_value=claims):
                yield application.test_client(), {"Authorization": "Bearer token"}


@pytest.fixture
def app(tmp_projects):
    with patch("config.Config.PROJECTS_DIR", tmp_projects), \
         patch("config.Config.STATIC_DIR", tmp_projects / "static"), \
         patch("config.Config.AUTH_ENABLED", False):
        (tmp_projects / "static").mkdir(exist_ok=True)
        application = create_app()
        application.config["TESTING"] = True
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


class TestStlDownload:
    def test_returns_file_when_public(self, client):
        resp = client.get("/api/projects/test-project/download/stl/test.stl")
        assert resp.status_code == 200

    def test_returns_401_when_gated_no_token(self, tmp_projects):
        """When download_stl requires auth and no token is present."""
        manifest_path = tmp_projects / "test-project" / "project.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["access_control"] = {"download_stl": "authenticated"}
        manifest_path.write_text(json.dumps(manifest))

        with patch("config.Config.PROJECTS_DIR", tmp_projects), \
             patch("config.Config.STATIC_DIR", tmp_projects / "static"), \
             patch("config.Config.AUTH_ENABLED", True):
            app = create_app()
            app.config["TESTING"] = True
            client = app.test_client()
            # Clear manifest cache
            import manifest as m
            m._manifest_cache.clear()

            resp = client.get("/api/projects/test-project/download/stl/test.stl")
            assert resp.status_code == 401

    def test_rejects_path_traversal(self, client):
        # Flask routing sanitizes .. in URL path segments → 404
        resp = client.get("/api/projects/test-project/download/stl/../../../etc/passwd")
        assert resp.status_code == 404

    def test_returns_404_for_missing_file(self, client):
        resp = client.get("/api/projects/test-project/download/stl/nonexistent.stl")
        assert resp.status_code == 404


class TestScadDownload:
    def test_returns_file_when_public_and_allowed(self, client):
        resp = client.get("/api/projects/test-project/download/scad/main.scad")
        assert resp.status_code == 200

    def test_rejects_path_traversal(self, client):
        # Flask routing sanitizes .. in URL path segments → 404
        resp = client.get("/api/projects/test-project/download/scad/../../etc/passwd")
        assert resp.status_code == 404

    def test_rejects_unlisted_file(self, client):
        resp = client.get("/api/projects/test-project/download/scad/secret.scad")
        assert resp.status_code == 403


class TestRenderFormatDownload:
    def test_returns_supported_format_file(self, tmp_projects):
        """A tier that may export 3mf can retrieve a 3mf artifact."""
        with auth_client(tmp_projects, tier="essentials") as (client, headers):
            resp = client.get("/api/projects/test-project/download/3mf/test.3mf", headers=headers)
            assert resp.status_code == 200

    def test_rejects_unsupported_format(self, client):
        resp = client.get("/api/projects/test-project/download/stlx/test.stl")
        assert resp.status_code == 400

    def test_rejects_filename_extension_mismatch(self, client):
        resp = client.get("/api/projects/test-project/download/stl/test.3mf")
        assert resp.status_code == 400

    def test_uses_format_specific_access_control_when_present(self, tmp_projects):
        manifest_path = tmp_projects / "test-project" / "project.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["access_control"] = {"download_3mf": "authenticated"}
        manifest_path.write_text(json.dumps(manifest))

        with patch("config.Config.PROJECTS_DIR", tmp_projects), \
             patch("config.Config.STATIC_DIR", tmp_projects / "static"), \
             patch("config.Config.AUTH_ENABLED", True):
            app = create_app()
            app.config["TESTING"] = True
            client = app.test_client()
            import manifest as m
            m._manifest_cache.clear()

            resp = client.get("/api/projects/test-project/download/3mf/test.3mf")
            assert resp.status_code == 401


class TestRenderFormatTierGate:
    """Retrieval-time export-format gating.

    Generation is gated in routes/engine/render.py, but rendered artifacts sit
    in the exports/static dirs under a predictable name for the 24 h render-GC
    window. Without this gate a guest who knows a filename could pull a `step`
    or `glb` export the tier never permitted them to produce.
    """

    def test_guest_cannot_download_premium_format(self, tmp_projects):
        with auth_client(tmp_projects) as (client, headers):
            resp = client.get("/api/projects/test-project/download/step/test.step", headers=headers)
            assert resp.status_code == 403
            body = resp.get_json()
            assert "step" in body["error"]
            assert "Pro" in body["error"]

    def test_pro_can_download_premium_format(self, tmp_projects):
        with auth_client(tmp_projects, tier="pro") as (client, headers):
            resp = client.get("/api/projects/test-project/download/step/test.step", headers=headers)
            assert resp.status_code == 200

    def test_guest_can_download_stl(self, tmp_projects):
        """`stl` is in the guest export_formats list and must stay open."""
        with auth_client(tmp_projects) as (client, headers):
            resp = client.get("/api/projects/test-project/download/stl/test.stl", headers=headers)
            assert resp.status_code == 200

    def test_guest_cannot_download_glb_via_generic_route(self, tmp_projects):
        with auth_client(tmp_projects) as (client, headers):
            resp = client.get("/api/projects/test-project/download/glb/test.glb", headers=headers)
            assert resp.status_code == 403

    def test_essentials_cannot_download_pro_only_format(self, tmp_projects):
        """essentials exports stl/3mf/obj — `off` is pro and above."""
        with auth_client(tmp_projects, tier="essentials") as (client, headers):
            resp = client.get("/api/projects/test-project/download/off/test.off", headers=headers)
            assert resp.status_code == 403

    def test_scad_download_is_not_tier_gated(self, tmp_projects):
        """SCAD is source, not an export format; the manifest allowlist gates it."""
        with auth_client(tmp_projects) as (client, headers):
            resp = client.get("/api/projects/test-project/download/scad/main.scad", headers=headers)
            assert resp.status_code == 200

    def test_tier_gate_runs_after_access_control(self, tmp_projects):
        """An access_control 401 still wins over the tier 403 for anonymous callers."""
        manifest_path = tmp_projects / "test-project" / "project.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["access_control"] = {"download_step": "authenticated"}
        manifest_path.write_text(json.dumps(manifest))

        with auth_client(tmp_projects) as (client, headers):
            resp = client.get("/api/projects/test-project/download/step/test.step", headers=headers)
            assert resp.status_code == 401

    def test_missing_premium_artifact_is_403_not_404(self, tmp_projects):
        """The gate must not leak whether a premium artifact exists."""
        with auth_client(tmp_projects) as (client, headers):
            resp = client.get("/api/projects/test-project/download/step/nope.step", headers=headers)
            assert resp.status_code == 403
