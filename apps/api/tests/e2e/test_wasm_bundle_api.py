"""E2E tests for GET /api/projects/<slug>/wasm-bundle.

A temp projects dir and a temp libs dir are staged the way tests/e2e/test_download.py
and test_projects_api.py stage theirs, so the route runs against a real manifest,
a real include graph and a real font on disk — the three things that were missing
when the Studio's worker tried to render in the browser.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

SLUG = "browser-widget"
CQ_SLUG = "server-widget"
PRIVATE_SLUG = "client-widget"


def _manifest(slug, scad_file="main.scad", engine=None, extra_modes=()):
    manifest = {
        "project": {
            "thumbnail": "thumb.png", "tags": ["test"], "difficulty": "beginner",
            "name": slug, "slug": slug, "version": "1.0.0",
        },
        "modes": [{
            "id": "default", "scad_file": scad_file, "label": {"en": "Default"},
            "parts": ["main"], "estimate": {"base_units": 1, "formula": "constant"},
        }, *extra_modes],
        "parts": [{"id": "main", "render_mode": 0, "label": {"en": "Main"},
                   "default_color": "#ffffff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 5, "per_unit": 2, "per_part": 8},
    }
    if engine:
        manifest["project"]["engine"] = engine
    return manifest


@pytest.fixture(autouse=True)
def _clear_bundle_cache():
    """The bundle cache is process-wide; each test gets a cold one."""
    from services.engine.wasm_bundle import invalidate_cache
    invalidate_cache()
    yield
    invalidate_cache()


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """Projects dir, libs dir and shared fonts dir, wired into Config."""
    import os

    from config import Config

    projects = tmp_path / "projects"
    libs = tmp_path / "libs"
    fonts = tmp_path / "shared-fonts"
    for directory in (projects, libs / "BOSL2", fonts):
        directory.mkdir(parents=True)

    # A cartridge that pulls a library the way the commons actually does, and
    # calls text() so the shared font has to travel with it.
    project = projects / SLUG
    (project / "fonts").mkdir(parents=True)
    (project / "main.scad").write_text(
        "include <../../libs/BOSL2/std.scad>\n"
        "use <helper.scad>\n"
        'text("hello");\n'
    )
    (project / "helper.scad").write_text("module helper() { cube(1); }\n")
    (project / "project.json").write_text(json.dumps(_manifest(SLUG)))
    (project / "fonts" / "Cartridge.ttf").write_bytes(b"\x00\x01cartridge-font")

    (libs / "BOSL2" / "std.scad").write_text("include <math.scad>\n")
    (libs / "BOSL2" / "math.scad").write_text("PI2 = 6.28;\n")
    (fonts / "Shared.ttf").write_bytes(b"\x00\x01shared-font")

    # A CadQuery cartridge — no browser kernel exists for it.
    cq = projects / CQ_SLUG
    cq.mkdir()
    (cq / "main.py").write_text("# cadquery\n")
    (cq / "project.json").write_text(
        json.dumps(_manifest(CQ_SLUG, scad_file="main.py", engine="cadquery")),
    )

    # A cartridge that is only private because configuration says so.
    private = projects / PRIVATE_SLUG
    private.mkdir()
    (private / "main.scad").write_text("cube(10);\n")
    (private / "project.json").write_text(json.dumps(_manifest(PRIVATE_SLUG)))

    monkeypatch.setattr(Config, "PROJECTS_DIR", projects)
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [projects])
    monkeypatch.setattr(Config, "SCAD_DIR", projects)
    monkeypatch.setattr(Config, "LIBS_DIR", libs)
    monkeypatch.setattr(Config, "FONTS_DIR", fonts)
    monkeypatch.setattr(Config, "OPENSCADPATH", os.pathsep.join([str(libs), str(projects)]))
    return {"root": tmp_path, "projects": projects, "libs": libs, "project": project}


@pytest.fixture
def client(tree):
    from app import create_app
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    return flask_app.test_client()


def _get(client, slug=SLUG, **kwargs):
    return client.get(f"/api/projects/{slug}/wasm-bundle", **kwargs)


class TestBundleShape:
    def test_200(self, client):
        assert _get(client).status_code == 200

    def test_contract_keys(self, client):
        body = _get(client).get_json()

        assert set(body) == {
            "slug", "engine", "entry_files", "files", "fonts",
            "unsupported", "unresolved", "bytes", "etag",
        }

    def test_slug_and_engine(self, client):
        body = _get(client).get_json()

        assert body["slug"] == SLUG
        assert body["engine"] == "openscad"

    def test_entry_files_are_the_manifest_mode_files(self, client):
        assert _get(client).get_json()["entry_files"] == ["main.scad"]

    def test_cartridge_sources_are_present(self, client):
        files = _get(client).get_json()["files"]

        assert files[f"projects/{SLUG}/main.scad"].startswith("include <../../libs/BOSL2/std.scad>")
        assert f"projects/{SLUG}/helper.scad" in files

    def test_the_library_a_relative_include_reaches_is_present(self, client):
        """The blocker: `include <../../libs/BOSL2/std.scad>` never resolved in the browser."""
        files = _get(client).get_json()["files"]

        assert files["libs/BOSL2/std.scad"] == "include <math.scad>\n"

    def test_transitive_library_includes_are_present(self, client):
        assert "libs/BOSL2/math.scad" in _get(client).get_json()["files"]

    def test_paths_are_posix_and_relative(self, client):
        files = _get(client).get_json()["files"]

        assert all(not p.startswith("/") and "\\" not in p for p in files)

    def test_cartridge_font_travels(self, client):
        import base64

        fonts = _get(client).get_json()["fonts"]

        assert base64.b64decode(fonts[f"projects/{SLUG}/fonts/Cartridge.ttf"]) == b"\x00\x01cartridge-font"

    def test_shared_font_travels_because_a_source_calls_text(self, client):
        assert "fonts/Shared.ttf" in _get(client).get_json()["fonts"]

    def test_fonts_conf_is_emitted(self, client):
        conf = _get(client).get_json()["fonts"]["fonts.conf"]

        assert "<dir>/fonts</dir>" in conf
        assert f"<dir>/projects/{SLUG}/fonts</dir>" in conf

    def test_nothing_unsupported_or_unresolved_for_a_clean_cartridge(self, client):
        body = _get(client).get_json()

        assert body["unsupported"] == []
        assert body["unresolved"] == []

    def test_bytes_counts_everything_the_worker_writes(self, client):
        body = _get(client).get_json()
        source_bytes = sum(len(t.encode()) for t in body["files"].values())
        conf_bytes = len(body["fonts"]["fonts.conf"].encode())

        assert body["bytes"] == (
            source_bytes + conf_bytes
            + len(b"\x00\x01cartridge-font") + len(b"\x00\x01shared-font")
        )

    def test_etag_is_a_sha256(self, client):
        etag = _get(client).get_json()["etag"]

        assert len(etag) == 64


class TestHonestyLists:
    def test_unresolved_include_is_reported(self, client, tree):
        (tree["project"] / "main.scad").write_text("include <ghost.scad>\n")

        body = _get(client).get_json()

        assert body["unresolved"] == [f"projects/{SLUG}/main.scad: ghost.scad"]
        assert body["unsupported"] == ["unresolved_includes"]

    def test_import_of_an_external_mesh_is_reported(self, client, tree):
        (tree["project"] / "main.scad").write_text('import("part.stl");\n')

        assert _get(client).get_json()["unsupported"] == ["import"]

    def test_surface_is_reported(self, client, tree):
        (tree["project"] / "main.scad").write_text('surface(file="height.dat");\n')

        assert _get(client).get_json()["unsupported"] == ["surface"]

    def test_another_cartridge_is_never_bundled(self, client, tree):
        (tree["project"] / "main.scad").write_text(f"include <{CQ_SLUG}/main.py>\n")

        body = _get(client).get_json()

        assert not any(CQ_SLUG in path for path in body["files"])
        assert body["unresolved"] == [f"projects/{SLUG}/main.scad: {CQ_SLUG}/main.py"]

    def test_traversal_out_of_the_tree_is_refused(self, client, tree):
        (tree["root"] / "secret.scad").write_text("// never\n")
        (tree["project"] / "main.scad").write_text("include <../../secret.scad>\n")

        body = _get(client).get_json()

        assert not any("secret" in path for path in body["files"])
        assert body["unresolved"] == [f"projects/{SLUG}/main.scad: ../../secret.scad"]


class TestCaching:
    def test_public_cache_headers(self, client):
        res = _get(client)

        assert res.headers["Cache-Control"] == "public, max-age=300"
        assert res.headers["ETag"] == res.get_json()["etag"]

    def test_304_on_matching_if_none_match(self, client):
        etag = _get(client).headers["ETag"]

        res = _get(client, headers={"If-None-Match": etag})

        assert res.status_code == 304
        assert res.get_data() == b""

    def test_304_carries_the_etag_and_cache_control_back(self, client):
        etag = _get(client).headers["ETag"]

        res = _get(client, headers={"If-None-Match": etag})

        assert res.headers["ETag"] == etag
        assert res.headers["Cache-Control"] == "public, max-age=300"

    def test_stale_if_none_match_gets_the_body(self, client):
        res = _get(client, headers={"If-None-Match": "0" * 64})

        assert res.status_code == 200

    def test_etag_is_stable_across_requests(self, client):
        assert _get(client).headers["ETag"] == _get(client).headers["ETag"]

    def test_editing_a_source_changes_the_etag(self, client, tree):
        import os

        before = _get(client).headers["ETag"]
        path = tree["project"] / "helper.scad"
        path.write_text("module helper() { sphere(1); }\n")
        # mtime resolution on some filesystems is coarser than this test is fast.
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

        assert _get(client).headers["ETag"] != before

    def test_editing_a_library_changes_the_etag(self, client, tree):
        import os

        before = _get(client).headers["ETag"]
        path = tree["libs"] / "BOSL2" / "math.scad"
        path.write_text("PI2 = 6.283185;\n")
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))

        assert _get(client).headers["ETag"] != before

    def test_a_cached_bundle_is_served_without_rereading_disk(self, client, tree, monkeypatch):
        first = _get(client).get_json()

        import services.engine.wasm_bundle as mod

        def _boom(*args, **kwargs):
            raise AssertionError("build_bundle should not run for a cached, unchanged cartridge")

        monkeypatch.setattr(mod, "build_bundle", _boom)

        assert _get(client).get_json()["etag"] == first["etag"]


class TestRefusals:
    def test_unknown_slug_404(self, client):
        res = _get(client, slug="no-such-cartridge")

        assert res.status_code == 404
        assert res.get_json()["error_code"] == "project_not_found"

    def test_malformed_slug_400(self, client):
        assert _get(client, slug="NotASlug!").status_code == 400

    def test_cadquery_project_400(self, client):
        res = _get(client, slug=CQ_SLUG)

        assert res.status_code == 400
        assert res.get_json()["error_code"] == "engine_not_wasm"

    def test_cadquery_project_is_refused_before_any_file_is_read(self, client, monkeypatch):
        import services.engine.wasm_bundle as mod

        def _boom(*args, **kwargs):
            raise AssertionError("a non-OpenSCAD cartridge must never be walked")

        monkeypatch.setattr(mod, "build_bundle", _boom)

        assert _get(client, slug=CQ_SLUG).status_code == 400

    def test_bundle_too_large_413(self, client, monkeypatch):
        import services.engine.wasm_bundle as mod
        monkeypatch.setattr(mod, "MAX_BUNDLE_FILES", 1)

        res = _get(client)

        assert res.status_code == 413
        assert res.get_json()["error_code"] == "bundle_too_large"

    def test_bundle_too_large_reports_the_totals(self, client, monkeypatch):
        import services.engine.wasm_bundle as mod
        monkeypatch.setattr(mod, "MAX_BUNDLE_BYTES", 8)

        body = _get(client).get_json()

        assert body["bytes"] > 8
        assert body["max_bytes"] == 8
        assert body["files"] >= 1
        assert body["max_files"] == mod.MAX_BUNDLE_FILES


class TestPrivateProjects:
    @pytest.fixture(autouse=True)
    def _reset_private_config(self, monkeypatch):
        from services.core.project_access import (
            PRIVATE_PROJECTS_ENV,
            private_project_slugs,
        )
        monkeypatch.delenv(PRIVATE_PROJECTS_ENV, raising=False)
        private_project_slugs()
        yield

    def test_private_slug_is_locked_for_an_anonymous_caller(self, client, monkeypatch):
        from services.core.project_access import PRIVATE_PROJECTS_ENV
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, PRIVATE_SLUG)

        res = _get(client, slug=PRIVATE_SLUG)

        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"
        assert res.get_json()["auth_required"] is True

    def test_a_public_cartridge_is_unaffected(self, client, monkeypatch):
        from services.core.project_access import PRIVATE_PROJECTS_ENV
        monkeypatch.setenv(PRIVATE_PROJECTS_ENV, PRIVATE_SLUG)

        assert _get(client).status_code == 200

    def test_a_manifest_declared_private_cartridge_is_locked(self, client, tree):
        manifest = _manifest(PRIVATE_SLUG)
        manifest["access_control"] = {"view": "private"}
        (tree["projects"] / PRIVATE_SLUG / "project.json").write_text(json.dumps(manifest))
        import manifest as manifest_mod
        manifest_mod.invalidate_cache(PRIVATE_SLUG)

        res = _get(client, slug=PRIVATE_SLUG)

        assert res.status_code == 403
        assert res.get_json()["error_code"] == "project_locked"


class TestDualEngineCartridge:
    """A cartridge with both CadQuery and OpenSCAD modes still gets a bundle —
    for the modes the browser can actually render."""

    @pytest.fixture
    def dual(self, tree):
        slug = "dual-widget"
        project = tree["projects"] / slug
        project.mkdir()
        (project / "main.py").write_text("# cadquery\n")
        (project / "shell.scad").write_text("cube(10);\n")
        manifest = _manifest(
            slug, scad_file="main.py", engine="cadquery",
            extra_modes=[{
                "id": "shell", "scad_file": "shell.scad", "engine": "openscad",
                "label": {"en": "Shell"}, "parts": ["main"],
                "estimate": {"base_units": 1, "formula": "constant"},
            }],
        )
        (project / "project.json").write_text(json.dumps(manifest))
        return slug

    def test_only_the_openscad_modes_are_entry_files(self, client, dual):
        body = _get(client, slug=dual).get_json()

        assert body["entry_files"] == ["shell.scad"]

    def test_the_cadquery_source_is_not_bundled(self, client, dual):
        files = _get(client, slug=dual).get_json()["files"]

        assert not any(path.endswith(".py") for path in files)
