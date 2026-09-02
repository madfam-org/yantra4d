"""Finding a project's latest render, on both backends.

The three routes that answer "analyse / price / simulate the thing I just
rendered" used to glob the static directory. Under an object store that glob
matches nothing and the user is told to render a model they already rendered.
These pin the replacement, including the tie-break the glob version got for
free from a stable sort — which matters more against S3, where `LastModified`
has second resolution and a mesh and its GLB companion routinely share a
timestamp.
"""
import pytest

from services.engine.render_artifacts import (
    MESH_EXTENSIONS,
    find_latest_render_key,
    render_key_prefix,
)
from services.storage import FilesystemArtifactStore

SLUG = "gridfinity"


@pytest.fixture(params=["fs", "s3"])
def store(request, tmp_path, s3_store):
    return FilesystemArtifactStore(tmp_path) if request.param == "fs" else s3_store


def _touch(store, key, mtime=None, monkeypatch=None):
    store.put_bytes(key, b"mesh")
    if mtime is not None:
        _set_mtime(store, key, mtime)
    return key


def _set_mtime(store, key, mtime):
    """Backdate an artifact on whichever backend holds it."""
    root = store.local_root()
    if root is not None:
        import os
        os.utime(root / key, (mtime, mtime))
        return
    import datetime
    entry = store.client.objects[(store.bucket, store.object_key(key))]
    entry["last_modified"] = datetime.datetime.fromtimestamp(mtime, datetime.UTC)


class TestPrefix:
    def test_the_prefix_is_the_name_renders_actually_carry(self):
        assert render_key_prefix(SLUG) == "gridfinity_preview_"


class TestFindLatest:
    def test_nothing_rendered_is_none(self, store):
        assert find_latest_render_key(SLUG, store=store) is None

    def test_another_projects_render_is_not_this_ones(self, store):
        _touch(store, "otherproject_preview_1_body.stl")
        assert find_latest_render_key(SLUG, store=store) is None

    def test_the_only_render_is_the_latest(self, store):
        key = _touch(store, f"{SLUG}_preview_abc_body.stl")
        assert find_latest_render_key(SLUG, store=store) == key

    def test_the_newest_render_wins(self, store):
        _touch(store, f"{SLUG}_preview_old_body.stl", mtime=1_000_000)
        newest = _touch(store, f"{SLUG}_preview_new_body.stl", mtime=2_000_000)
        assert find_latest_render_key(SLUG, store=store) == newest

    def test_a_tie_prefers_the_viewer_format(self, store):
        """A render and its GLB companion are written milliseconds apart.

        On S3 that is the *same* second, so without a deterministic tie-break
        the analysis routes would pick the STL or the GLB at random from one
        request to the next.
        """
        _touch(store, f"{SLUG}_preview_abc_body.stl", mtime=1_700_000_000)
        _touch(store, f"{SLUG}_preview_abc_body.glb", mtime=1_700_000_000)
        assert find_latest_render_key(SLUG, store=store) == f"{SLUG}_preview_abc_body.glb"

    def test_formats_outside_the_list_are_ignored(self, store):
        _touch(store, f"{SLUG}_preview_abc_body.step", mtime=2_000_000)
        mesh = _touch(store, f"{SLUG}_preview_abc_body.stl", mtime=1_000_000)
        assert find_latest_render_key(SLUG, store=store) == mesh

    def test_the_caller_may_narrow_the_formats(self, store):
        _touch(store, f"{SLUG}_preview_abc_body.glb", mtime=2_000_000)
        stl = _touch(store, f"{SLUG}_preview_abc_body.stl", mtime=1_000_000)
        assert find_latest_render_key(SLUG, (".stl",), store=store) == stl

    def test_the_default_format_order_is_the_shared_one(self):
        assert MESH_EXTENSIONS == (".glb", ".stl", ".3mf")
