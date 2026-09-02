"""The render worker's write path, on both backends.

What matters here is that the *observable* result of a render — the `/static/`
URL the studio is handed and the cache entry that lets the next request skip
the render — is identical whether the artifact landed on the pod's disk or in a
bucket. That identity is what keeps #78's private-project gate and the download
route's access checks applying unchanged: both read the artifact's name, and
the name does not move.
"""
import json
import sys
from pathlib import Path

import pytest

from services.engine.render_cache import RenderCache
from services.storage import FilesystemArtifactStore

WORKER_DIR = Path(__file__).resolve().parents[3] / "worker"
if str(WORKER_DIR) not in sys.path:
    sys.path.insert(0, str(WORKER_DIR))

# Imported after the sys.path line above, which is what makes it importable.
import render_worker

PART = "body"
SLUG = "gridfinity"
PREFIX = f"{SLUG}_preview_9f2c1a_"
ARTIFACT = f"{PREFIX}{PART}.stl"
GLB = f"{PREFIX}{PART}.glb"
MESH = b"solid body\nendsolid body\n"


@pytest.fixture
def staging(tmp_path, monkeypatch):
    """Where the render engines write. The store may or may not be this."""
    staging_dir = tmp_path / "render-output"
    staging_dir.mkdir()
    monkeypatch.setattr(render_worker, "STATIC_FOLDER", str(staging_dir))
    return staging_dir


class _FakeManifest:
    """The slice of a project manifest the worker's engine branches read."""

    def __init__(self):
        self.project = {"hyperobject": {"implicit_field": {}}}


@pytest.fixture
def events(monkeypatch):
    """Capture what the worker publishes back to the API."""
    published = []
    monkeypatch.setattr(
        render_worker, "_publish_job_event",
        lambda job_id, payload, emit_final=False: published.append(payload),
    )
    monkeypatch.setattr(render_worker, "_set_active_job", lambda *a, **k: None)
    monkeypatch.setattr(render_worker, "_clear_active_job", lambda *a: None)
    monkeypatch.setattr(render_worker, "_is_cancelled", lambda job_id: False)
    # Enough manifest for every engine branch: the implicit engine reads its
    # field configuration off it, the others never touch it.
    monkeypatch.setattr(render_worker, "get_manifest", lambda slug: _FakeManifest())
    return published


@pytest.fixture
def rendering(staging, monkeypatch):
    """An OpenSCAD render that succeeds, plus a GLB companion conversion."""
    def fake_render(cmd, scad_path=None, is_cancelled=None):
        Path(staging / ARTIFACT).write_bytes(MESH)
        return True, "render ok"

    def fake_stl_to_glb(src, dst):
        Path(dst).write_bytes(b"glTF\x02")
        return True

    monkeypatch.setattr(render_worker, "run_openscad_render", fake_render)
    monkeypatch.setattr(render_worker, "build_openscad_command", lambda *a, **k: ["true"])
    monkeypatch.setattr(render_worker, "stl_to_glb", fake_stl_to_glb)
    monkeypatch.setattr(render_worker, "convert_mesh", lambda *a, **k: False)
    return staging


def _task(staging):
    return {
        "job_id": "job-1",
        "engine": "openscad",
        "part": PART,
        "scad_path": "/projects/gridfinity/main.scad",
        "output_path": str(staging / ARTIFACT),
        "export_format": "stl",
        "payload": {
            "project_slug": SLUG,
            "params": {"width": 42},
            "mode_map": {PART: 0},
            "stl_prefix": PREFIX,
            "scad_filename": "main.scad",
            "scad_content_hash": "abc123",
        },
    }


def _part_done(published):
    done = [e for e in published if e.get("event") == "part_done"]
    assert len(done) == 1, published
    return done[0]


class TestFilesystemBackendIsUnchanged:
    """The default path: today's file, at today's location, with today's URL."""

    def test_the_artifact_stays_exactly_where_the_render_put_it(
        self, rendering, events, monkeypatch
    ):
        store = FilesystemArtifactStore(rendering)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))

        render_worker.process_sync_task(_task(rendering))

        # The render wrote here, and publishing left it here.
        artifact = rendering / ARTIFACT
        assert artifact.is_file()
        assert artifact.read_bytes() == MESH
        assert (rendering / GLB).is_file()

    def test_the_urls_are_the_ones_it_always_published(self, rendering, events, monkeypatch):
        store = FilesystemArtifactStore(rendering)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))

        render_worker.process_sync_task(_task(rendering))

        done = _part_done(events)
        assert done["url"] == f"/static/{ARTIFACT}"
        assert done["viewer_url"] == f"/static/{GLB}"
        assert done["size_bytes"] == len(MESH)

    def test_publishing_does_not_rewrite_the_file(self, rendering, events, monkeypatch):
        """Byte-for-byte, inode and mtime included.

        The static directory is a volume with a hard sizeLimit and a GC that
        sorts by mtime; a copy-on-publish would double the bytes and reorder
        the collection queue.
        """
        store = FilesystemArtifactStore(rendering)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))

        # Pre-place the artifact so we can compare identity across the publish.
        (rendering / ARTIFACT).write_bytes(MESH)
        before = (rendering / ARTIFACT).stat()

        monkeypatch.setattr(
            render_worker, "run_openscad_render",
            lambda cmd, scad_path=None, is_cancelled=None: (True, "reused"),
        )
        render_worker.process_sync_task(_task(rendering))

        after = (rendering / ARTIFACT).stat()
        assert (after.st_ino, after.st_mtime_ns, after.st_size) == (
            before.st_ino, before.st_mtime_ns, before.st_size
        )


class TestObjectBackend:
    def test_the_artifact_is_uploaded_and_the_staging_copy_removed(
        self, rendering, events, monkeypatch, s3_store
    ):
        """Under an object store the local directory is scratch, not the store.

        Nothing collects it in the worker container, and it sits on a volume
        with a hard sizeLimit, so a published file's local copy goes.
        """
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: s3_store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=s3_store))

        render_worker.process_sync_task(_task(rendering))

        assert s3_store.exists(ARTIFACT)
        assert s3_store.exists(GLB)
        with s3_store.open(ARTIFACT) as body:
            assert body.read() == MESH
        assert not (rendering / ARTIFACT).exists()
        assert not (rendering / GLB).exists()

    def test_the_urls_are_identical_to_the_filesystem_ones(
        self, rendering, events, monkeypatch, s3_store
    ):
        """The reason the access gates keep working untouched.

        Both gates key off the artifact's *name* — `artifact_slug_candidates`
        splits `<slug>_preview_<part>.<fmt>` out of the path. Move the bytes,
        keep the name, and neither gate notices.
        """
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: s3_store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=s3_store))

        render_worker.process_sync_task(_task(rendering))

        done = _part_done(events)
        assert done["url"] == f"/static/{ARTIFACT}"
        assert done["viewer_url"] == f"/static/{GLB}"
        assert done["size_bytes"] == len(MESH)

    def test_a_failed_publish_fails_the_render_rather_than_lying(
        self, rendering, events, monkeypatch, s3_store, fake_s3_client
    ):
        """The quiet failure this whole seam exists to prevent.

        Reporting success for an artifact that was never stored hands the
        studio a URL that 404s, and the cache then remembers it.
        """
        from tests.conftest import FakeClientError

        def explode(**_kwargs):
            raise FakeClientError("InternalError", 500, "storage is having a day")

        fake_s3_client.upload_file = explode
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: s3_store)
        cache = RenderCache(store=s3_store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        render_worker.process_sync_task(_task(rendering))

        assert [e.get("event") for e in events] == ["error"]
        assert cache.get(SLUG, "main.scad", {"width": 42}, PART, "stl",
                         scad_content_hash="abc123") is None


class TestCacheKeyRoundTrip:
    """A render's cache entry has to survive being read back by another process."""

    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_the_entry_names_a_key_and_that_key_resolves(
        self, rendering, events, monkeypatch, s3_store, backend
    ):
        store = FilesystemArtifactStore(rendering) if backend == "fs" else s3_store
        cache = RenderCache(store=store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        render_worker.process_sync_task(_task(rendering))

        entry = cache.get(SLUG, "main.scad", {"width": 42}, PART, "stl",
                          scad_content_hash="abc123")
        assert entry is not None
        # A key, not a path: nothing here is only meaningful to the process
        # that happened to run the render.
        assert entry["key"] == ARTIFACT
        assert "path" not in entry
        assert not Path(entry["key"]).is_absolute()
        assert store.exists(entry["key"])
        assert entry["size_bytes"] == len(MESH)

    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_an_entry_whose_artifact_is_gone_is_a_miss(
        self, rendering, events, monkeypatch, s3_store, backend
    ):
        """Migration rule: a key missing from the store is a cache miss.

        That is what makes flipping the flag safe in both directions — entries
        written against the other backend simply do not resolve, and the part
        is rendered again.
        """
        store = FilesystemArtifactStore(rendering) if backend == "fs" else s3_store
        cache = RenderCache(store=store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        render_worker.process_sync_task(_task(rendering))
        assert store.delete(ARTIFACT) is True

        assert cache.get(SLUG, "main.scad", {"width": 42}, PART, "stl",
                         scad_content_hash="abc123") is None


# ──────────────────────────────────────────────
# Every engine, every export format
# ──────────────────────────────────────────────
#
# `_publish_part_artifacts` sits after the engine dispatch and after the
# format conversion, so in principle one test covers all of them. In principle
# is not good enough for the property this branch exists to guarantee: a render
# that succeeds and publishes nowhere hands the studio a URL that 404s, and the
# cache then remembers that URL. Each engine reaches the publish through its
# own branch, each export format through its own conversion path, and a future
# engine added with an early `return` would break exactly one of them.

#: Every engine the worker dispatches, and the function each one's branch calls.
ENGINES = ("openscad", "cadquery", "graph", "implicit")

#: Every format the tiers allow as an export (tiers.json), plus the GLB the
#: viewer gets for free alongside an STL.
EXPORT_FORMATS = ("stl", "3mf", "obj", "step", "glb", "gltf", "off")


def _engine_task(staging, engine, export_format="stl"):
    task = _task(staging)
    task["engine"] = engine
    task["export_format"] = export_format
    task["output_path"] = str(staging / f"{PREFIX}{PART}.{export_format}")
    return task


@pytest.fixture
def every_engine_renders(staging, monkeypatch):
    """Make all four engine branches produce a file at the output path."""
    def writes(output_path):
        Path(output_path).write_bytes(MESH)

    def fake_sync(cmd, scad_path=None, is_cancelled=None):
        # OpenSCAD and CadQuery are handed a command; the output path is the
        # first thing the worker put in it.
        writes(cmd[-1])
        return True, "ok"

    def fake_implicit(output_path, config, params):
        writes(output_path)
        return True, "ok"

    monkeypatch.setattr(render_worker, "build_openscad_command",
                        lambda output_path, *a, **k: ["openscad", output_path])
    monkeypatch.setattr(render_worker, "build_cadquery_command",
                        lambda output_path, *a, **k: ["cq", output_path])
    monkeypatch.setattr(render_worker, "prepare_graph_script", lambda scad, manifest: scad)
    monkeypatch.setattr(render_worker, "run_openscad_render", fake_sync)
    monkeypatch.setattr(render_worker, "run_cadquery_render", fake_sync)
    monkeypatch.setattr(render_worker, "run_implicit_render", fake_implicit)
    monkeypatch.setattr(render_worker, "stl_to_glb",
                        lambda src, dst: (Path(dst).write_bytes(b"glTF\x02"), True)[1])
    monkeypatch.setattr(render_worker, "convert_mesh", lambda *a, **k: False)
    return staging


class TestEveryEngineWritesThroughTheStore:
    @pytest.mark.parametrize("engine", ENGINES)
    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_the_artifact_is_published_and_named_the_same(
        self, every_engine_renders, events, monkeypatch, s3_store, engine, backend
    ):
        staging = every_engine_renders
        store = FilesystemArtifactStore(staging) if backend == "fs" else s3_store
        cache = RenderCache(store=store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        render_worker.process_sync_task(_engine_task(staging, engine))

        done = _part_done(events)
        assert done["url"] == f"/static/{ARTIFACT}"
        assert store.exists(ARTIFACT), f"{engine} on {backend} published nothing"
        with store.open(ARTIFACT) as body:
            assert body.read() == MESH
        assert cache.get(SLUG, "main.scad", {"width": 42}, PART, "stl",
                         scad_content_hash="abc123")["key"] == ARTIFACT

    @pytest.mark.parametrize("engine", ENGINES)
    def test_the_object_backend_keeps_no_local_copy(
        self, every_engine_renders, events, monkeypatch, s3_store, engine
    ):
        """Staging is a volume with a hard sizeLimit and no GC in this container."""
        staging = every_engine_renders
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: s3_store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=s3_store))

        render_worker.process_sync_task(_engine_task(staging, engine))

        assert list(staging.iterdir()) == []

    @pytest.mark.parametrize("engine", ENGINES)
    def test_a_publish_failure_fails_the_render_for_every_engine(
        self, every_engine_renders, events, monkeypatch, s3_store, fake_s3_client, engine
    ):
        from tests.conftest import FakeClientError

        def explode(**_kwargs):
            raise FakeClientError("InternalError", 500, "storage is having a day")

        fake_s3_client.upload_file = explode
        cache = RenderCache(store=s3_store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: s3_store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        render_worker.process_sync_task(_engine_task(every_engine_renders, engine))

        assert [e.get("event") for e in events] == ["error"]
        assert cache.get(SLUG, "main.scad", {"width": 42}, PART, "stl",
                         scad_content_hash="abc123") is None


class TestEveryExportFormatWritesThroughTheStore:
    @pytest.mark.parametrize("export_format", EXPORT_FORMATS)
    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_the_export_is_published_under_its_own_name(
        self, every_engine_renders, events, monkeypatch, s3_store, export_format, backend
    ):
        staging = every_engine_renders
        store = FilesystemArtifactStore(staging) if backend == "fs" else s3_store
        cache = RenderCache(store=store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        render_worker.process_sync_task(
            _engine_task(staging, "openscad", export_format)
        )

        artifact = f"{PREFIX}{PART}.{export_format}"
        done = _part_done(events)
        assert done["url"] == f"/static/{artifact}"
        assert store.exists(artifact), f"{export_format} on {backend} published nothing"
        assert cache.get(SLUG, "main.scad", {"width": 42}, PART, export_format,
                         scad_content_hash="abc123")["key"] == artifact

    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_an_stl_also_publishes_its_viewer_companion(
        self, every_engine_renders, events, monkeypatch, s3_store, backend
    ):
        """The GLB the studio actually loads is a second artifact, not a name."""
        staging = every_engine_renders
        store = FilesystemArtifactStore(staging) if backend == "fs" else s3_store
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))

        render_worker.process_sync_task(_engine_task(staging, "openscad", "stl"))

        done = _part_done(events)
        assert done["viewer_url"] == f"/static/{GLB}"
        assert store.exists(GLB)

    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_a_converted_export_publishes_the_converted_file(
        self, every_engine_renders, events, monkeypatch, s3_store, backend
    ):
        """OpenSCAD renders STL and the converter makes the OBJ.

        The published artifact must be the OBJ the caller asked for, and the
        STL it was made from must not be left behind on an object store — it is
        an intermediate nothing is ever linked to.
        """
        staging = every_engine_renders
        store = FilesystemArtifactStore(staging) if backend == "fs" else s3_store
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", RenderCache(store=store))
        monkeypatch.setattr(
            render_worker, "convert_mesh",
            lambda src, dst, *a, **k: (Path(dst).write_bytes(b"o obj\n"), True)[1],
        )

        task = _engine_task(staging, "openscad", "obj")
        # OpenSCAD cannot emit OBJ, so it renders STL and the worker converts.
        task["output_path"] = str(staging / ARTIFACT)
        render_worker.process_sync_task(task)

        converted = f"{PREFIX}{PART}.obj"
        assert _part_done(events)["url"] == f"/static/{converted}"
        assert store.exists(converted)
        if store.local_root() is None:
            assert not store.exists(ARTIFACT), "the intermediate STL was stored"


class TestTheStreamingPathPublishesToo:
    """`process_stream_task` has its own copy of the publish block."""

    @pytest.mark.parametrize("backend", ["fs", "s3"])
    def test_a_streamed_render_publishes_and_caches(
        self, every_engine_renders, events, monkeypatch, s3_store, backend
    ):
        staging = every_engine_renders
        store = FilesystemArtifactStore(staging) if backend == "fs" else s3_store
        cache = RenderCache(store=store)
        monkeypatch.setattr(render_worker, "get_artifact_store", lambda: store)
        monkeypatch.setattr(render_worker, "render_cache", cache)

        def fake_stream(cmd, *args, **kwargs):
            Path(cmd[-1]).write_bytes(MESH)
            yield json.dumps({"event": "part_done", "part": PART})

        monkeypatch.setattr(render_worker, "stream_openscad_render", fake_stream)

        task = _engine_task(staging, "openscad")
        task.update({"part_index": 0, "num_parts": 1, "part_base": 0, "part_weight": 100})
        render_worker.process_stream_task(task)

        # The raw engine event is relayed as it arrives; the one with a URL is
        # the finalised event the worker publishes after storing the artifact.
        done = next(e for e in reversed(events) if e.get("url"))
        assert done["url"] == f"/static/{ARTIFACT}"
        assert store.exists(ARTIFACT)
        assert cache.get(SLUG, "main.scad", {"width": 42}, PART, "stl",
                         scad_content_hash="abc123")["key"] == ARTIFACT
