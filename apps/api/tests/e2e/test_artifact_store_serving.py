"""Serving render artifacts: /static and the download route, on both backends.

Two claims, and the first is the one production depends on:

1. **With the default `fs` store, nothing moved.** The `/static` and download
   responses are compared header-for-header and byte-for-byte against the exact
   Flask calls this change replaced. If the abstraction cost a single header —
   an ETag, a Last-Modified, an Accept-Ranges — this fails.

2. **With an object store, the gates still gate.** Artifacts are streamed
   through the API rather than redirected to, so #78's private-project check on
   `/static` and the access checks on the download route run on every request,
   exactly as they do for files on disk.
"""
import json

import pytest
from flask import Flask, send_file, send_from_directory

from config import Config
from services.storage import FilesystemArtifactStore, S3ArtifactStore, set_artifact_store
from utils.route_helpers import safe_join_path

PUBLIC_SLUG = "open-widget"
PRIVATE_SLUG = "closed-widget"
ARTIFACT = f"{PUBLIC_SLUG}_preview_9f2c1a_body.stl"
PRIVATE_ARTIFACT = f"{PRIVATE_SLUG}_preview_9f2c1a_body.stl"
MESH = b"solid body\nendsolid body\n"

#: The headers the artifact response itself is responsible for. Everything else
#: on a real response — CORS, X-Request-Id, Date — comes from app-wide
#: middleware that predates this change and is identical on every route, so
#: comparing it against a bare reference app would only measure the middleware.
_ARTIFACT_HEADERS = (
    "content-type",
    "content-length",
    "content-disposition",
    "cache-control",
    "etag",
    "last-modified",
    "accept-ranges",
    "content-encoding",
)


def _manifest(slug: str, private: bool) -> dict:
    data = {
        "project": {
            "name": slug, "slug": slug, "version": "1.0.0",
            "thumbnail": "t.png", "tags": [], "difficulty": "beginner",
        },
        "modes": [{
            "id": "single", "scad_file": "main.scad", "label": "S",
            "parts": ["body"], "estimate": {"base_units": 1, "formula": "constant"},
        }],
        "parts": [{"id": "body", "render_mode": 1, "label": "B", "default_color": "#fff"}],
        "parameters": [],
        "estimate_constants": {"base_time": 1, "per_unit": 0.1, "per_part": 0.5},
    }
    if private:
        data["access_control"] = {"view": "private"}
    return data


@pytest.fixture
def projects(tmp_path):
    for slug, private in ((PUBLIC_SLUG, False), (PRIVATE_SLUG, True)):
        project_dir = tmp_path / slug
        project_dir.mkdir()
        (project_dir / "project.json").write_text(json.dumps(_manifest(slug, private)))
        (project_dir / "main.scad").write_text("cube(10);")
    return tmp_path


@pytest.fixture
def static_dir(tmp_path):
    directory = tmp_path / "static"
    directory.mkdir()
    return directory


@pytest.fixture
def fs_client(projects, static_dir, monkeypatch):
    """The app on its default store, with two artifacts already rendered."""
    (static_dir / ARTIFACT).write_bytes(MESH)
    (static_dir / PRIVATE_ARTIFACT).write_bytes(MESH)
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)
    monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "fs")
    set_artifact_store(FilesystemArtifactStore())

    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    application.static_folder = str(static_dir)
    return application.test_client()


@pytest.fixture
def s3_app(projects, static_dir, monkeypatch, fake_s3_client):
    """The app on an object store, with the same two artifacts in the bucket."""
    store = S3ArtifactStore(
        bucket="renders", endpoint_url="http://object-store.test:9000",
        prefix="renders/v1", client=fake_s3_client,
    )
    store.put_bytes(ARTIFACT, MESH)
    store.put_bytes(PRIVATE_ARTIFACT, MESH)
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)
    monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "s3")
    set_artifact_store(store)

    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application, store


@pytest.fixture
def s3_client(s3_app):
    return s3_app[0].test_client()


def _reference_static_client(static_dir):
    """`/static` exactly as it was wired before the artifact store existed.

    Both rules, in the same order `app.py` created them: Flask's built-in
    `static` endpoint (from `Flask(__name__)` with the static folder pointing at
    the same directory, which is how production is wired) *and* the app's own
    explicit view. Registering only one would measure a response the app never
    actually produced — see `test_flasks_builtin_static_rule_is_what_answers`.
    """
    reference = Flask(
        "reference-static", static_folder=str(static_dir), static_url_path="/static"
    )
    reference.config["TESTING"] = True

    @reference.route("/static/<path:filename>")
    def serve_static(filename):
        resp = send_from_directory(str(static_dir), filename)
        resp.headers["Cache-Control"] = "public, max-age=3600"
        return resp

    return reference.test_client()


def _reference_download_client(static_dir):
    """The download route's artifact branch exactly as it read before."""
    reference = Flask("reference-download")
    reference.config["TESTING"] = True

    @reference.route("/dl/<path:filename>")
    def download(filename):
        safe_path = safe_join_path(str(static_dir), filename)
        return send_file(safe_path, as_attachment=True, download_name=filename)

    return reference.test_client()


def _comparable(headers):
    lowered = {k.lower(): v for k, v in headers.items()}
    return {name: lowered.get(name) for name in _ARTIFACT_HEADERS}


# ──────────────────────────────────────────────
# 1. The default backend did not move
# ──────────────────────────────────────────────

class TestFilesystemDefaultIsByteIdentical:
    def test_static_response_matches_send_from_directory_exactly(self, fs_client, static_dir):
        got = fs_client.get(f"/static/{ARTIFACT}")
        expected = _reference_static_client(static_dir).get(f"/static/{ARTIFACT}")

        assert got.status_code == expected.status_code == 200
        assert got.data == expected.data == MESH
        assert _comparable(got.headers) == _comparable(expected.headers)
        # Spelled out, because these are what a generic byte stream would lose:
        assert got.headers["Content-Type"] == expected.headers["Content-Type"]
        assert got.headers.get("ETag")
        assert got.headers.get("Last-Modified")
        assert got.headers["Content-Length"] == str(len(MESH))

    def test_flasks_builtin_static_rule_is_what_answers(self, fs_client):
        """A pre-existing fact this change had to preserve rather than fix.

        `Flask(__name__)` registers a `static` endpoint for `/static/<path>`,
        and `app.py` registers its own `serve_static` view for the very same
        URL. Werkzeug resolves the tie in registration order, so the built-in
        rule wins and `serve_static` never runs in production — which means its
        `Cache-Control: public, max-age=3600` never applies either. Artifacts
        are served `no-cache`, from Werkzeug's `send_file` default.

        `app.py` already knew the two rules were ambiguous: that is exactly why
        the private-project gate added in #78 is a `before_request` hook rather
        than a check inside the view. Nothing here changes which rule wins on
        the filesystem backend; this test pins the behaviour so a later change
        to that dead view cannot silently alter what production sends.
        """
        got = fs_client.get(f"/static/{ARTIFACT}")
        assert got.headers["Cache-Control"] == "no-cache"

    def test_conditional_requests_still_revalidate(self, fs_client):
        first = fs_client.get(f"/static/{ARTIFACT}")
        again = fs_client.get(
            f"/static/{ARTIFACT}", headers={"If-None-Match": first.headers["ETag"]}
        )
        assert again.status_code == 304

    def test_range_requests_still_work(self, fs_client):
        partial = fs_client.get(f"/static/{ARTIFACT}", headers={"Range": "bytes=0-4"})
        assert partial.status_code == 206
        assert partial.data == MESH[:5]

    def test_a_missing_artifact_is_still_the_apps_json_404(self, fs_client):
        missing = fs_client.get("/static/never-rendered.stl")
        assert missing.status_code == 404
        assert missing.get_json()["status"] == "error"

    def test_download_response_matches_send_file_exactly(self, fs_client, static_dir):
        got = fs_client.get(f"/api/projects/{PUBLIC_SLUG}/download/stl/{ARTIFACT}")
        expected = _reference_download_client(static_dir).get(f"/dl/{ARTIFACT}")

        assert got.status_code == expected.status_code == 200
        assert got.data == expected.data == MESH
        assert _comparable(got.headers) == _comparable(expected.headers)
        assert got.headers["Content-Disposition"] == f"attachment; filename={ARTIFACT}"

    def test_the_private_gate_still_refuses(self, fs_client):
        refused = fs_client.get(f"/static/{PRIVATE_ARTIFACT}")
        assert refused.status_code == 403
        assert refused.get_json()["error_code"] == "project_locked"


# ──────────────────────────────────────────────
# 2. The object backend serves through the same gates
# ──────────────────────────────────────────────

class TestObjectBackendServing:
    def test_static_streams_the_artifact_out_of_the_store(self, s3_client):
        got = s3_client.get(f"/static/{ARTIFACT}")
        assert got.status_code == 200
        assert got.data == MESH
        assert got.headers["Content-Length"] == str(len(MESH))
        # Same MIME type the filesystem branch would have sent.
        assert got.headers["Content-Type"].startswith("model/stl")

    def test_caching_changes_when_the_backend_does_and_that_is_deliberate(self, s3_client):
        """The one header that differs between the two backends.

        On `fs`, Flask's built-in static rule shadows the app's view (see
        `test_flasks_builtin_static_rule_is_what_answers`) and artifacts go out
        `no-cache`. On an object store that rule does not exist, the app's view
        runs, and its long-intended `public, max-age=3600` finally applies.
        Safe, because artifact names carry the parameter hash — different
        parameters are a different name, so a cached response can never be a
        stale render — and because a *private* project's artifact is still
        stamped `private, no-store` by the gate, which runs after the view.
        Recorded in docs/operations/render-artifact-storage.md so an operator
        flipping the flag is not surprised by it.
        """
        assert s3_client.get(f"/static/{ARTIFACT}").headers["Cache-Control"] == (
            "public, max-age=3600"
        )

    def test_a_private_artifact_is_never_cacheable(self, s3_client, s3_app, monkeypatch):
        """The gate's `private, no-store` outranks the view, on either backend."""
        monkeypatch.setenv("PROJECT_ACCESS_GRANTS", "{}")
        monkeypatch.setattr(Config, "AUTH_ENABLED", False)
        refused = s3_client.get(f"/static/{PRIVATE_ARTIFACT}")
        assert refused.status_code == 403
        assert "public" not in refused.headers.get("Cache-Control", "")

    def test_nothing_is_redirected_to_a_bucket_url(self, s3_client):
        """A 302 to object storage would bypass every check above it."""
        got = s3_client.get(f"/static/{ARTIFACT}")
        assert got.status_code == 200
        assert "Location" not in got.headers
        assert b"object-store.test" not in got.data

    def test_the_private_gate_still_refuses(self, s3_client):
        """#78's gate reads the artifact's name, and the name did not move."""
        refused = s3_client.get(f"/static/{PRIVATE_ARTIFACT}")
        assert refused.status_code == 403
        assert refused.get_json()["error_code"] == "project_locked"

    def test_a_missing_artifact_is_the_apps_json_404(self, s3_client):
        missing = s3_client.get("/static/never-rendered.stl")
        assert missing.status_code == 404
        assert missing.get_json()["status"] == "error"

    def test_a_stray_local_file_cannot_shadow_the_store(self, s3_client, static_dir):
        """Flask's built-in `static` rule answers the same URL this app does.

        Harmless while both read one directory; not harmless once artifacts
        live in a bucket, because the built-in rule would serve whatever
        happened to be on the pod's disk. With a non-filesystem store there is
        no local directory to serve from and that rule is not registered.
        """
        (static_dir / "left-behind.stl").write_bytes(b"stale bytes")
        stale = s3_client.get("/static/left-behind.stl")
        assert stale.status_code == 404

    def test_the_builtin_static_endpoint_is_not_registered(self, s3_app):
        application, _store = s3_app
        assert "static" not in application.view_functions
        assert application.static_folder is None

    def test_download_streams_as_an_attachment(self, s3_client):
        got = s3_client.get(f"/api/projects/{PUBLIC_SLUG}/download/stl/{ARTIFACT}")
        assert got.status_code == 200
        assert got.data == MESH
        assert got.headers["Content-Disposition"] == f"attachment; filename={ARTIFACT}"

    def test_download_refuses_a_private_project(self, s3_client):
        got = s3_client.get(f"/api/projects/{PRIVATE_SLUG}/download/stl/{PRIVATE_ARTIFACT}")
        assert got.status_code == 403
        assert got.get_json()["error_code"] == "project_locked"

    def test_download_404s_when_the_object_is_not_there(self, s3_client):
        got = s3_client.get(f"/api/projects/{PUBLIC_SLUG}/download/stl/never-rendered.stl")
        assert got.status_code == 404

    def test_download_will_not_serve_a_mismatched_format(self, s3_client, s3_app):
        """The requested extension is re-checked against the stored key."""
        _application, store = s3_app
        store.put_bytes(f"{PUBLIC_SLUG}_preview_9f2c1a_body.3mf", b"3mf bytes")
        got = s3_client.get(
            f"/api/projects/{PUBLIC_SLUG}/download/stl/{PUBLIC_SLUG}_preview_9f2c1a_body.3mf"
        )
        assert got.status_code == 400


class TestHealthReportsTheBackend:
    def test_filesystem_default_is_named(self, fs_client):
        body = fs_client.get("/api/health").get_json()
        assert body["artifact_store"] == "fs"
        assert body["checks"]["artifact_store"]["kind"] == "fs"
        assert body["checks"]["artifact_store"]["ok"] is True

    def test_object_backend_is_named_without_leaking_where_it_is(self, s3_client):
        """/api/health is unauthenticated and rate-limit exempt.

        The kind is useful to anyone; the endpoint, bucket and prefix are not
        theirs to know. An operator reads those from the startup log.
        """
        body = s3_client.get("/api/health").get_json()
        assert body["artifact_store"] == "s3"
        rendered = json.dumps(body)
        assert "object-store.test" not in rendered
        assert "renders/v1" not in rendered
