"""The read side of the artifact store, on both backends.

Every question the API used to ask the filesystem about a render artifact —
what is in the directory, how old is this file, give me a byte range, give me a
path I can hand to a subprocess — is asked of the store here, and asked
identically of both backends. That symmetry is the whole point: the moment
`fs` and `s3` answer one of them differently, a route works on one deployment
and not on the other, and the difference shows up as a missing render rather
than as an error anyone can trace.
"""
import os
import time

import pytest

from services.storage import (
    ArtifactNotFound,
    FilesystemArtifactStore,
    local_artifact,
)

MESH = b"solid body\n" + b"x" * 100 + b"\nendsolid body\n"


@pytest.fixture(params=["fs", "s3"])
def store(request, tmp_path, s3_store):
    """The same tests, once per backend."""
    return FilesystemArtifactStore(tmp_path) if request.param == "fs" else s3_store


@pytest.fixture
def backend(store):
    return store.kind


# ──────────────────────────────────────────────
# stat
# ──────────────────────────────────────────────

class TestStat:
    def test_a_stored_artifact_reports_its_size_and_age(self, store):
        before = time.time()
        store.put_bytes("body.stl", MESH)

        info = store.stat("body.stl")

        assert info is not None
        assert info.key == "body.stl"
        assert info.size == len(MESH)
        # Within a generous window either side: S3 timestamps have second
        # resolution and may round down past the moment of the call.
        assert before - 2 <= info.modified_at <= time.time() + 2

    def test_a_missing_artifact_has_no_stat(self, store):
        assert store.stat("never-rendered.stl") is None

    def test_exists_and_size_agree_with_stat(self, store):
        store.put_bytes("body.stl", MESH)
        assert store.exists("body.stl") is True
        assert store.size("body.stl") == len(MESH)
        assert store.exists("gone.stl") is False
        assert store.size("gone.stl") is None

    def test_a_traversing_key_has_no_stat(self, store):
        assert store.stat("../../etc/passwd") is None


# ──────────────────────────────────────────────
# list
# ──────────────────────────────────────────────

class TestListing:
    def test_an_empty_store_lists_nothing(self, store):
        assert store.list() == []

    def test_every_stored_artifact_is_listed_in_key_order(self, store):
        for name in ("c.stl", "a.stl", "b.glb"):
            store.put_bytes(name, MESH)

        assert [info.key for info in store.list()] == ["a.stl", "b.glb", "c.stl"]
        assert all(info.size == len(MESH) for info in store.list())

    def test_the_prefix_narrows_the_listing(self, store):
        store.put_bytes("gridfinity_preview_1_body.stl", MESH)
        store.put_bytes("gridfinity_preview_2_lid.stl", MESH)
        store.put_bytes("otherproject_preview_1_body.stl", MESH)

        keys = [info.key for info in store.list("gridfinity_preview_")]
        assert keys == ["gridfinity_preview_1_body.stl", "gridfinity_preview_2_lid.stl"]

    def test_a_nested_key_is_listed_by_both_backends(self, store):
        """Neither backend may quietly hide part of the store.

        Nothing writes a nested key today, but `normalize_key` accepts one, and
        a backend that skipped it would leave artifacts the GC could never
        collect and the lookup could never find — on one deployment only.
        """
        store.put_bytes("2026/09/body.stl", MESH)
        assert [info.key for info in store.list()] == ["2026/09/body.stl"]

    def test_a_deleted_artifact_leaves_the_listing(self, store):
        store.put_bytes("body.stl", MESH)
        assert store.delete("body.stl") is True
        assert store.list() == []

    def test_listing_pages_through_everything(self, store):
        """More artifacts than one page: the GC has to see all of them."""
        names = [f"part{i:02d}.stl" for i in range(7)]
        for name in names:
            store.put_bytes(name, MESH)
        assert [info.key for info in store.list()] == sorted(names)


# ──────────────────────────────────────────────
# ranged reads
# ──────────────────────────────────────────────

class TestRangedReads:
    def test_a_whole_read_is_unchanged(self, store):
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl")
        try:
            assert body.read() == MESH
        finally:
            body.close()

    @pytest.mark.parametrize("start,end", [(0, 5), (5, 20), (10, len(MESH))])
    def test_a_bounded_range_returns_exactly_those_bytes(self, store, start, end):
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl", start=start, end=end)
        try:
            assert body.read() == MESH[start:end]
        finally:
            body.close()

    def test_an_open_ended_range_runs_to_the_end(self, store):
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl", start=len(MESH) - 4)
        try:
            assert body.read() == MESH[-4:]
        finally:
            body.close()

    def test_a_range_read_stops_at_the_end_of_the_range(self, store):
        """Reading past the range must yield nothing, not the next bytes."""
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl", start=0, end=4)
        try:
            assert body.read(2) == MESH[:2]
            assert body.read(64) == MESH[2:4]
            assert body.read(64) == b""
        finally:
            body.close()

    def test_a_missing_artifact_still_raises(self, store):
        with pytest.raises(ArtifactNotFound):
            store.open("never-rendered.stl", start=0, end=4)


# ──────────────────────────────────────────────
# materialising a real file
# ──────────────────────────────────────────────

class TestLocalArtifact:
    def test_the_block_gets_a_readable_file(self, store):
        store.put_bytes("body.stl", MESH)
        with local_artifact("body.stl", store=store) as path:
            assert path is not None
            assert path.read_bytes() == MESH

    def test_a_missing_artifact_yields_none(self, store):
        with local_artifact("never-rendered.stl", store=store) as path:
            assert path is None

    def test_a_traversing_key_yields_none(self, store):
        with local_artifact("../../etc/passwd", store=store) as path:
            assert path is None

    def test_the_filesystem_backend_hands_over_the_artifact_itself(self, tmp_path):
        """No copy: the path is the artifact, exactly as the old code had it."""
        fs_store = FilesystemArtifactStore(tmp_path)
        fs_store.put_bytes("body.stl", MESH)
        with local_artifact("body.stl", store=fs_store) as path:
            assert path == tmp_path / "body.stl"
        # And it is still there afterwards.
        assert (tmp_path / "body.stl").read_bytes() == MESH

    def test_an_object_store_copy_is_removed_afterwards(self, s3_store):
        """A long-lived API pod must not accumulate downloaded meshes."""
        s3_store.put_bytes("body.stl", MESH)
        with local_artifact("body.stl", store=s3_store) as path:
            staged = path
            assert staged.read_bytes() == MESH
        assert not staged.exists()

    def test_the_copy_is_removed_even_when_the_block_raises(self, s3_store):
        s3_store.put_bytes("body.stl", MESH)
        staged = None
        with pytest.raises(RuntimeError), local_artifact("body.stl", store=s3_store) as path:
            staged = path
            raise RuntimeError("analysis blew up")
        assert staged is not None
        assert not os.path.exists(staged)

    def test_the_copy_keeps_the_suffix_mesh_loaders_dispatch_on(self, s3_store):
        """trimesh picks its loader from the extension, so the copy must keep it."""
        s3_store.put_bytes("body.glb", MESH)
        with local_artifact("body.glb", store=s3_store) as path:
            assert path.suffix == ".glb"
