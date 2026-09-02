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
def fs_app(projects, static_dir, monkeypatch):
    """The app on its default store, with two artifacts already rendered."""
    (static_dir / ARTIFACT).write_bytes(MESH)
    (static_dir / PRIVATE_ARTIFACT).write_bytes(MESH)
    monkeypatch.setattr(Config, "STATIC_DIR", static_dir)
    monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "fs")
    store = FilesystemArtifactStore()
    set_artifact_store(store)

    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    return application, store


@pytest.fixture
def fs_client(fs_app):
    return fs_app[0].test_client()


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

    Both rules, in the same order `app.py` created them at the time: Flask's
    built-in `static` endpoint (from `Flask(__name__)` with the static folder
    pointing at the same directory, which is how production was wired) *and*
    the app's own explicit view with the `Cache-Control` it set. The built-in
    rule wins the tie, so this reference reproduces what production actually
    served — which is what the current app must still match, now that the
    ambiguity is resolved in favour of one store-backed rule.
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

    def test_one_rule_answers_static_and_it_goes_through_the_store(self, fs_app):
        """Two rules used to answer `/static/<path>`, and the wrong one won.

        `Flask(__name__)` registers a `static` endpoint for that URL and
        `app.py` registers its own `serve_static` view for it; Werkzeug
        resolves the tie in registration order, so the built-in rule won and
        `serve_static` never ran — which is why the header it meant to set
        never applied. `app.py` already knew the pair was ambiguous: that is
        exactly why #78's private-project gate is a `before_request` hook
        rather than a check inside the view.

        There is now one rule, on both backends, and it reads through the
        store. Production does not move: under the default store that view
        delegates to `send_from_directory`, which is what the built-in rule
        did — the response above is compared header-for-header to prove it.
        """
        application, _store = fs_app
        assert "static" not in application.view_functions
        assert application.static_folder is None

    def test_artifacts_are_still_served_no_cache(self, fs_client):
        """Werkzeug's `send_file` default, and what production has always sent."""
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

    def test_caching_is_the_same_on_both_backends(self, s3_client, fs_client):
        """Flipping the flag must not change how cacheable an artifact is.

        An earlier cut of this branch let the object-store path send
        `public, max-age=3600` — the header the app's shadowed view had always
        meant to set — while the filesystem path kept Werkzeug's `no-cache`.
        That made the same artifact shared-cacheable on one deployment and not
        the other, which is a security property (a private project's render
        sitting in an intermediary) hanging off a storage flag. Both send
        `no-cache`; #78's gate downgrades that to `private, no-store` for a
        private project, again on both.
        """
        assert s3_client.get(f"/static/{ARTIFACT}").headers["Cache-Control"] == "no-cache"
        assert fs_client.get(f"/static/{ARTIFACT}").headers["Cache-Control"] == "no-cache"

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

    def test_a_stray_local_file_cannot_shadow_the_download_route_either(
        self, s3_client, static_dir
    ):
        """The download route reads the store, not the pod's disk."""
        (static_dir / f"{PUBLIC_SLUG}_preview_stale_body.stl").write_bytes(b"stale")
        got = s3_client.get(
            f"/api/projects/{PUBLIC_SLUG}/download/stl/{PUBLIC_SLUG}_preview_stale_body.stl"
        )
        assert got.status_code == 404

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


# ──────────────────────────────────────────────
# 3. Conditional and ranged requests, identically on both backends
# ──────────────────────────────────────────────


@pytest.fixture(params=["fs", "s3"])
def backend(request):
    """A client and its store, once per backend.

    Resolved lazily: both app fixtures install a process-wide store, so asking
    for them together would leave whichever ran last in charge of a client
    built against the other.
    """
    app_fixture = "fs_app" if request.param == "fs" else "s3_app"
    application, store = request.getfixturevalue(app_fixture)
    return application.test_client(), store, request.param


class TestValidatorsAndRanges:
    """The half of `/static` that a byte stream does not get for free.

    Under `fs` all of this comes from Werkzeug's `send_file`; under `s3` it is
    implemented over `ArtifactStore.stat` and a ranged `open`. A viewer, a
    resumed `curl -C -` and any CDN in front of the API cannot tell which
    backend is behind them, so neither may these responses.
    """

    def test_a_plain_get_carries_a_validator_and_a_length(self, backend):
        client, _store, _kind = backend
        got = client.get(f"/static/{ARTIFACT}")
        assert got.status_code == 200
        assert got.headers.get("ETag")
        assert got.headers.get("Last-Modified")
        assert got.headers["Content-Length"] == str(len(MESH))
        # And no `Accept-Ranges`: Werkzeug's `send_file` only advertises range
        # support on a response that actually is one, so neither backend does.
        assert "Accept-Ranges" not in got.headers

    def test_the_validator_is_stable_across_requests(self, backend):
        client, _store, _kind = backend
        first = client.get(f"/static/{ARTIFACT}").headers["ETag"]
        assert client.get(f"/static/{ARTIFACT}").headers["ETag"] == first

    def test_if_none_match_revalidates_to_304(self, backend):
        client, _store, _kind = backend
        first = client.get(f"/static/{ARTIFACT}")
        again = client.get(
            f"/static/{ARTIFACT}", headers={"If-None-Match": first.headers["ETag"]}
        )
        assert again.status_code == 304
        assert again.data == b""
        assert again.headers["ETag"] == first.headers["ETag"]

    def test_if_modified_since_revalidates_to_304(self, backend):
        client, _store, _kind = backend
        first = client.get(f"/static/{ARTIFACT}")
        again = client.get(
            f"/static/{ARTIFACT}",
            headers={"If-Modified-Since": first.headers["Last-Modified"]},
        )
        assert again.status_code == 304

    def test_an_older_if_modified_since_still_sends_the_artifact(self, backend):
        client, _store, _kind = backend
        got = client.get(
            f"/static/{ARTIFACT}",
            headers={"If-Modified-Since": "Wed, 21 Oct 2015 07:28:00 GMT"},
        )
        assert got.status_code == 200
        assert got.data == MESH

    def test_a_stale_validator_gets_the_new_bytes(self, backend):
        """A reused artifact name has to invalidate the client's copy."""
        client, store, _kind = backend
        stale = client.get(f"/static/{ARTIFACT}").headers["ETag"]
        store.put_bytes(ARTIFACT, MESH + b"more geometry\n")

        got = client.get(f"/static/{ARTIFACT}", headers={"If-None-Match": stale})

        assert got.status_code == 200
        assert got.data == MESH + b"more geometry\n"
        assert got.headers["ETag"] != stale

    @pytest.mark.parametrize(
        "header,expected",
        [
            ("bytes=0-4", slice(0, 5)),
            ("bytes=5-9", slice(5, 10)),
            ("bytes=10-", slice(10, None)),
            ("bytes=-5", slice(-5, None)),
        ],
    )
    def test_a_range_request_is_a_206_with_those_bytes(self, backend, header, expected):
        client, _store, _kind = backend
        got = client.get(f"/static/{ARTIFACT}", headers={"Range": header})
        assert got.status_code == 206
        assert got.data == MESH[expected]
        assert got.headers["Content-Length"] == str(len(MESH[expected]))
        assert got.headers["Content-Range"].startswith("bytes ")
        assert got.headers["Content-Range"].endswith(f"/{len(MESH)}")
        assert got.headers["Accept-Ranges"] == "bytes"

    def test_an_unsatisfiable_range_is_a_416_naming_the_length(self, backend):
        client, _store, _kind = backend
        got = client.get(f"/static/{ARTIFACT}", headers={"Range": "bytes=9999-10000"})
        assert got.status_code == 416
        assert got.headers["Content-Range"] == f"bytes */{len(MESH)}"

    def test_if_range_with_the_current_validator_serves_the_range(self, backend):
        client, _store, _kind = backend
        etag = client.get(f"/static/{ARTIFACT}").headers["ETag"]
        got = client.get(
            f"/static/{ARTIFACT}", headers={"Range": "bytes=0-4", "If-Range": etag}
        )
        assert got.status_code == 206
        assert got.data == MESH[:5]

    def test_if_range_with_a_stale_validator_resends_the_whole_artifact(self, backend):
        """RFC 9110: the artifact changed under the client, so the range is void."""
        client, _store, _kind = backend
        got = client.get(
            f"/static/{ARTIFACT}",
            headers={"Range": "bytes=0-4", "If-Range": '"not-the-current-one"'},
        )
        assert got.status_code == 200
        assert got.data == MESH

    def test_the_download_route_ranges_too(self, backend):
        client, _store, _kind = backend
        got = client.get(
            f"/api/projects/{PUBLIC_SLUG}/download/stl/{ARTIFACT}",
            headers={"Range": "bytes=0-4"},
        )
        assert got.status_code == 206
        assert got.data == MESH[:5]
        assert got.headers["Content-Disposition"] == f"attachment; filename={ARTIFACT}"

    def test_the_download_route_revalidates_too(self, backend):
        client, _store, _kind = backend
        url = f"/api/projects/{PUBLIC_SLUG}/download/stl/{ARTIFACT}"
        first = client.get(url)
        again = client.get(url, headers={"If-None-Match": first.headers["ETag"]})
        assert again.status_code == 304


class TestPrivateArtifactsRevealNothing:
    """#78/#87's discipline survives the validators being added.

    An ETag is a fingerprint of content. It must never reach a caller who is
    not entitled to that content — and neither must a `Last-Modified`, which
    tells them when a private project was last rendered.
    """

    @pytest.mark.parametrize("headers", [
        {},
        {"If-None-Match": '"anything"'},
        {"Range": "bytes=0-4"},
        {"If-Modified-Since": "Wed, 21 Oct 2015 07:28:00 GMT"},
    ])
    def test_an_unentitled_caller_gets_no_validator_by_any_route(self, backend, headers):
        client, _store, _kind = backend
        refused = client.get(f"/static/{PRIVATE_ARTIFACT}", headers=headers)
        assert refused.status_code == 403
        assert refused.get_json()["error_code"] == "project_locked"
        assert "ETag" not in refused.headers
        assert "Last-Modified" not in refused.headers
        assert "Content-Range" not in refused.headers

    def test_a_conditional_request_cannot_probe_for_existence(self, backend):
        """The refusal is identical whether or not the artifact is there."""
        client, store, _kind = backend
        present = client.get(f"/static/{PRIVATE_ARTIFACT}")
        assert store.delete(PRIVATE_ARTIFACT) is True
        absent = client.get(f"/static/{PRIVATE_ARTIFACT}")

        assert present.status_code == absent.status_code == 403
        assert present.get_json()["error_code"] == absent.get_json()["error_code"]

    def test_no_response_on_either_backend_is_shared_cacheable(self, backend):
        client, _store, _kind = backend
        refused = client.get(f"/static/{PRIVATE_ARTIFACT}")
        assert "public" not in refused.headers.get("Cache-Control", "")


class TestTheTwoBackendsAnswerTheSameWay:
    """One app, one URL, both stores — compared header for header.

    The class above asserts each backend's behaviour separately, which can
    drift into two correct-looking specifications of different things. This
    swaps the store underneath a single app between requests, so any divergence
    shows up as a diff rather than as two passing tests.

    ETag and Last-Modified are compared for *presence*: their values are
    supposed to differ (S3 hands back the object's MD5, a file's is derived
    from mtime and size), and a test demanding they match would be demanding
    the wrong thing.
    """

    #: Everything the artifact response itself decides.
    SHAPE = (
        "content-type", "content-length", "content-range", "cache-control",
        "accept-ranges", "content-disposition", "content-encoding", "vary",
    )

    @pytest.fixture
    def swap(self, projects, static_dir, monkeypatch, fake_s3_client):
        """A client plus a switch between the two stores.

        The app itself is backend-agnostic — one `/static` rule, resolved
        through `get_artifact_store()` per request — which is what makes this
        comparison possible at all.
        """
        (static_dir / ARTIFACT).write_bytes(MESH)
        (static_dir / PRIVATE_ARTIFACT).write_bytes(MESH)
        monkeypatch.setattr(Config, "STATIC_DIR", static_dir)

        fs_store = FilesystemArtifactStore()
        s3_store = S3ArtifactStore(
            bucket="renders", endpoint_url="http://object-store.test:9000",
            prefix="renders/v1", client=fake_s3_client,
        )
        s3_store.put_bytes(ARTIFACT, MESH)
        s3_store.put_bytes(PRIVATE_ARTIFACT, MESH)

        set_artifact_store(fs_store)
        from app import create_app
        application = create_app()
        application.config["TESTING"] = True
        client = application.test_client()

        def request(**kwargs):
            answers = {}
            for name, store in (("fs", fs_store), ("s3", s3_store)):
                set_artifact_store(store)
                answers[name] = client.get(**kwargs)
            return answers["fs"], answers["s3"]

        return request

    def _shape(self, response):
        lowered = {k.lower(): v for k, v in response.headers.items()}
        return (
            response.status_code,
            {name: lowered.get(name) for name in self.SHAPE},
            "etag" in lowered,
            "last-modified" in lowered,
        )

    def test_a_plain_get_matches(self, swap):
        fs, s3 = swap(path=f"/static/{ARTIFACT}")
        assert fs.data == s3.data == MESH
        assert self._shape(fs) == self._shape(s3)

    def test_a_range_request_matches(self, swap):
        fs, s3 = swap(path=f"/static/{ARTIFACT}", headers={"Range": "bytes=3-11"})
        assert fs.status_code == 206
        assert fs.data == s3.data == MESH[3:12]
        assert self._shape(fs) == self._shape(s3)

    def test_an_unsatisfiable_range_matches(self, swap):
        fs, s3 = swap(path=f"/static/{ARTIFACT}", headers={"Range": "bytes=900-999"})
        assert fs.status_code == 416
        assert fs.headers["Content-Range"] == s3.headers["Content-Range"]
        assert fs.status_code == s3.status_code

    def test_a_revalidation_matches(self, swap):
        """Each backend is handed back *its own* validator, and must 304."""
        fs_first, s3_first = swap(path=f"/static/{ARTIFACT}")
        fs_again, _ = swap(
            path=f"/static/{ARTIFACT}",
            headers={"If-None-Match": fs_first.headers["ETag"]},
        )
        _, s3_again = swap(
            path=f"/static/{ARTIFACT}",
            headers={"If-None-Match": s3_first.headers["ETag"]},
        )
        assert fs_again.status_code == s3_again.status_code == 304
        assert self._shape(fs_again) == self._shape(s3_again)

    def test_a_missing_artifact_matches(self, swap):
        fs, s3 = swap(path="/static/never-rendered.stl")
        assert fs.status_code == s3.status_code == 404
        assert fs.get_json()["status"] == s3.get_json()["status"] == "error"

    def test_the_private_refusal_matches(self, swap):
        fs, s3 = swap(path=f"/static/{PRIVATE_ARTIFACT}")
        assert fs.status_code == s3.status_code == 403
        assert fs.get_json()["error_code"] == s3.get_json()["error_code"]
        assert self._shape(fs) == self._shape(s3)
