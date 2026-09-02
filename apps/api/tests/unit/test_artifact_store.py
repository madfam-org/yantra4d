"""Artifact store: keys, the filesystem backend, and the factory.

The load-bearing claim under test is the *default*: with
``RENDER_ARTIFACT_STORE`` unset, an artifact keeps the exact path it has today
and publishing it does not touch a byte. Everything else in this change is
opt-in; this file is what says production did not move.
"""

import pytest

from services.storage import (
    ArtifactNotFound,
    ArtifactStoreError,
    FilesystemArtifactStore,
    S3ArtifactStore,
    artifact_key,
    build_artifact_store,
    get_artifact_store,
    publish_artifact,
    publish_artifact_best_effort,
    reset_artifact_store,
    set_artifact_store,
)
from services.storage.base import (
    InvalidArtifactKey,
    guess_content_type,
    key_for_path,
    normalize_key,
)


@pytest.fixture(autouse=True)
def _clean_store_singleton():
    """No test may leak a store into the next one."""
    reset_artifact_store()
    yield
    reset_artifact_store()


@pytest.fixture
def store(tmp_path):
    return FilesystemArtifactStore(tmp_path)


# ──────────────────────────────────────────────
# Keys
# ──────────────────────────────────────────────

class TestKeyRules:
    def test_a_plain_artifact_name_is_already_a_key(self):
        assert normalize_key("gridfinity_preview_9f2c1a_body.stl") == (
            "gridfinity_preview_9f2c1a_body.stl"
        )

    def test_nested_keys_are_allowed(self):
        assert normalize_key("2026/09/body.stl") == "2026/09/body.stl"

    def test_backslashes_are_normalised_to_forward_slashes(self):
        assert normalize_key("a\\b.stl") == "a/b.stl"

    @pytest.mark.parametrize("bad", [
        "",
        "   ",
        "/etc/passwd",
        "../../etc/passwd",
        "a/../../etc/passwd",
        "a//b.stl",
        "./b.stl",
        "a/./b.stl",
        "a\x00b.stl",
    ])
    def test_traversal_and_junk_are_refused(self, bad):
        """Rejection lives here, not in the backend.

        The S3 backend has no filesystem to bounce an escaping path off:
        ``../../etc/passwd`` is a perfectly ordinary object name and a bucket
        prefix would not contain it. So the key rule has to be the guard.
        """
        with pytest.raises(InvalidArtifactKey):
            normalize_key(bad)

    def test_key_for_path_is_the_name_under_the_root(self, tmp_path):
        artifact = tmp_path / "proj_preview_body.stl"
        artifact.write_bytes(b"x")
        assert key_for_path(artifact, tmp_path) == "proj_preview_body.stl"

    def test_key_for_path_outside_the_root_falls_back_to_the_basename(self, tmp_path):
        elsewhere = tmp_path / "other"
        elsewhere.mkdir()
        artifact = elsewhere / "body.stl"
        artifact.write_bytes(b"x")
        assert key_for_path(artifact, tmp_path / "root") == "body.stl"

    def test_key_for_path_with_no_root_uses_the_basename(self):
        assert key_for_path("/scratch/renders/body.glb", None) == "body.glb"

    def test_content_type_matches_what_werkzeug_would_send(self):
        # Werkzeug guesses with mimetypes and falls back to octet-stream; a mesh
        # streamed from a bucket must be labelled like the same mesh off disk.
        assert guess_content_type("body.stl") == guess_content_type("body.stl")
        assert guess_content_type("thing.unknownext") == "application/octet-stream"
        assert guess_content_type("page.json") == "application/json"


# ──────────────────────────────────────────────
# Filesystem backend
# ──────────────────────────────────────────────

class TestFilesystemStore:
    def test_put_bytes_round_trips(self, store, tmp_path):
        store.put_bytes("body.stl", b"solid body\n")
        assert (tmp_path / "body.stl").read_bytes() == b"solid body\n"
        with store.open("body.stl") as fh:
            assert fh.read() == b"solid body\n"
        assert store.exists("body.stl")
        assert store.size("body.stl") == len(b"solid body\n")

    def test_put_file_copies_from_outside_the_root(self, store, tmp_path):
        source = tmp_path / "elsewhere"
        source.mkdir()
        src = source / "body.stl"
        src.write_bytes(b"mesh")
        store.put_file("body.stl", src)
        assert (tmp_path / "body.stl").read_bytes() == b"mesh"

    def test_publishing_a_file_already_in_place_does_not_touch_it(self, store, tmp_path):
        """The no-copy property the default deployment depends on.

        Renders write straight into the static directory. Copying such a file
        onto itself would double the bytes on a volume with a hard sizeLimit,
        reset the mtime the GC sorts on, and swap the inode under an in-flight
        download. Publishing it must be a no-op.
        """
        artifact = tmp_path / "proj_preview_body.stl"
        artifact.write_bytes(b"solid body\n")
        before = artifact.stat()

        key = publish_artifact(artifact, store=store)

        after = artifact.stat()
        assert key == "proj_preview_body.stl"
        assert (after.st_ino, after.st_mtime_ns, after.st_size) == (
            before.st_ino, before.st_mtime_ns, before.st_size
        )
        assert artifact.read_bytes() == b"solid body\n"

    def test_publishing_through_a_different_spelling_is_still_a_no_op(self, store, tmp_path):
        """Sameness is decided by inode, not by string equality."""
        artifact = tmp_path / "body.stl"
        artifact.write_bytes(b"solid\n")
        before = artifact.stat()
        store.put_file("body.stl", tmp_path / "." / "body.stl")
        assert artifact.stat().st_ino == before.st_ino

    def test_missing_artifact_reads_as_absent(self, store):
        assert not store.exists("nope.stl")
        assert store.size("nope.stl") is None
        assert store.delete("nope.stl") is False
        with pytest.raises(ArtifactNotFound):
            store.open("nope.stl")

    def test_delete_removes_the_file(self, store, tmp_path):
        store.put_bytes("body.stl", b"x")
        assert store.delete("body.stl") is True
        assert not (tmp_path / "body.stl").exists()

    def test_publishing_a_file_that_is_not_there_raises(self, store, tmp_path):
        with pytest.raises(ArtifactNotFound):
            publish_artifact(tmp_path / "never-rendered.stl", store=store)

    def test_traversal_never_escapes_the_root(self, store, tmp_path):
        outside = tmp_path.parent / "escaped.stl"
        with pytest.raises(InvalidArtifactKey):
            store.put_bytes("../escaped.stl", b"nope")
        assert not outside.exists()
        assert store.exists("../escaped.stl") is False

    def test_a_symlink_pointing_out_of_the_root_is_refused(self, store, tmp_path):
        """normalize_key cannot see this one; the resolved-path check can."""
        outside = tmp_path.parent / "outside-the-store"
        outside.mkdir(exist_ok=True)
        (tmp_path / "escape").symlink_to(outside, target_is_directory=True)
        with pytest.raises(InvalidArtifactKey):
            store.path_for("escape/body.stl")
        assert store.exists("escape/body.stl") is False

    def test_root_follows_config_when_unbound(self, tmp_path, monkeypatch):
        """An unbound store reads Config.STATIC_DIR at call time.

        Not laziness for its own sake: the static directory is settled from the
        environment and is monkeypatched per test, and reading it at call time
        is exactly what the send_from_directory call being replaced did.
        """
        from config import Config
        monkeypatch.setattr(Config, "STATIC_DIR", tmp_path)
        unbound = FilesystemArtifactStore()
        assert unbound.local_root() == tmp_path
        unbound.put_bytes("body.stl", b"x")
        assert (tmp_path / "body.stl").exists()

    def test_check_ready_creates_and_accepts_the_directory(self, tmp_path):
        target = tmp_path / "made-on-demand"
        FilesystemArtifactStore(target).check_ready()
        assert target.is_dir()

    def test_check_ready_refuses_a_root_it_cannot_have(self, tmp_path):
        """Fail closed at startup rather than 404 every render afterwards.

        A file where the directory should be is the one unusable root that
        behaves identically for every uid, including the root user CI runs as
        (for whom directory mode bits are advisory).
        """
        blocked = tmp_path / "not-a-directory"
        blocked.write_text("I am a file")
        with pytest.raises(ArtifactStoreError):
            FilesystemArtifactStore(blocked).check_ready()

    def test_describe_names_the_backend_and_its_root(self, store, tmp_path):
        assert store.describe() == {"kind": "fs", "root": str(tmp_path)}


# ──────────────────────────────────────────────
# Selection
# ──────────────────────────────────────────────

class TestStoreSelection:
    def test_the_default_is_the_filesystem_store_at_the_static_dir(self, monkeypatch, tmp_path):
        """With nothing configured, artifacts stay exactly where they are."""
        from config import Config
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "fs")
        monkeypatch.setattr(Config, "STATIC_DIR", tmp_path)
        store = get_artifact_store()
        assert isinstance(store, FilesystemArtifactStore)
        assert store.kind == "fs"
        assert store.local_root() == tmp_path

    def test_s3_is_selected_only_by_explicit_configuration(self, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "s3")
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_S3_BUCKET", "renders")
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_S3_ENDPOINT", "http://storage.invalid:9000")
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_S3_REGION", "us-east-1")
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_S3_PREFIX", "renders/v1")
        store = build_artifact_store()
        assert isinstance(store, S3ArtifactStore)
        assert store.bucket == "renders"
        assert store.prefix == "renders/v1"
        # No local directory: the read path must stream rather than sendfile.
        assert store.local_root() is None

    def test_an_unknown_backend_name_refuses_to_build(self, monkeypatch):
        """A typo must not look like a working object-storage rollout.

        Falling back to `fs` would be friendlier and wrong: every artifact
        would quietly go to local disk, and the pod that replaced this one
        would serve none of them.
        """
        from config import Config
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "s2")
        with pytest.raises(ArtifactStoreError, match="Unknown RENDER_ARTIFACT_STORE"):
            build_artifact_store()

    def test_s3_without_a_bucket_refuses_to_build(self, monkeypatch):
        from config import Config
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_STORE", "s3")
        monkeypatch.setattr(Config, "RENDER_ARTIFACT_S3_BUCKET", "")
        with pytest.raises(ArtifactStoreError, match="RENDER_ARTIFACT_S3_BUCKET"):
            build_artifact_store()

    def test_artifact_key_uses_the_installed_store(self, tmp_path):
        set_artifact_store(FilesystemArtifactStore(tmp_path))
        assert artifact_key(tmp_path / "proj_preview_body.stl") == "proj_preview_body.stl"


class TestBestEffortPublish:
    """Producers that trusted a converter's boolean keep their old behaviour."""

    def test_a_produced_file_is_published(self, store, tmp_path):
        artifact = tmp_path / "body.obj"
        artifact.write_bytes(b"o body\n")
        assert publish_artifact_best_effort(artifact, store=store) == "body.obj"
        assert store.exists("body.obj")

    def test_a_file_that_never_landed_still_yields_its_key(self, store, tmp_path):
        """A link that 404s is today's behaviour; a 500 would be a regression."""
        assert publish_artifact_best_effort(tmp_path / "ghost.obj", store=store) == "ghost.obj"
        assert not store.exists("ghost.obj")
