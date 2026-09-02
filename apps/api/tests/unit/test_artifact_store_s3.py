"""S3 artifact backend, against the in-memory endpoint in conftest.

The fake reproduces the boto3 surface `S3ArtifactStore` calls and — the part
that actually decides control flow — the error codes botocore really returns:
``NoSuchKey`` from ``get_object``, the bare ``404`` from ``head_object`` and
``head_bucket``. Those three were confirmed against boto3 driving moto while
this was written.
"""
import pytest

from services.storage import ArtifactNotFound, ArtifactStoreError, S3ArtifactStore
from services.storage.base import InvalidArtifactKey
from tests.conftest import FakeClientError, FakeS3Client


class TestObjectNaming:
    def test_the_prefix_namespaces_every_key(self, s3_store):
        assert s3_store.object_key("proj_preview_body.stl") == (
            "renders/v1/proj_preview_body.stl"
        )

    def test_no_prefix_leaves_the_key_alone(self, fake_s3_client):
        store = S3ArtifactStore(bucket="renders", client=fake_s3_client)
        assert store.object_key("body.stl") == "body.stl"

    def test_a_slash_only_prefix_is_treated_as_no_prefix(self, fake_s3_client):
        store = S3ArtifactStore(bucket="renders", prefix="/", client=fake_s3_client)
        assert store.prefix == ""
        assert store.object_key("body.stl") == "body.stl"

    def test_there_is_no_local_directory(self, s3_store):
        """Which is what makes the read path stream instead of sendfile."""
        assert s3_store.local_root() is None


class TestRoundTrip:
    def test_put_file_uploads_with_the_right_content_type(self, s3_store, fake_s3_client, tmp_path):
        src = tmp_path / "proj_preview_body.stl"
        src.write_bytes(b"solid body\nendsolid\n")

        key = s3_store.put_file("proj_preview_body.stl", src)

        assert key == "proj_preview_body.stl"
        assert s3_store.exists(key)
        assert s3_store.size(key) == len(b"solid body\nendsolid\n")
        with s3_store.open(key) as body:
            assert body.read() == b"solid body\nendsolid\n"
        call = fake_s3_client.calls[-1]
        assert call[0] == "upload_file"
        assert call[2] == "renders/v1/proj_preview_body.stl"
        assert call[3]["ContentType"] == "model/stl"

    def test_put_bytes_round_trips(self, s3_store):
        s3_store.put_bytes("body.glb", b"glTF\x02")
        with s3_store.open("body.glb") as body:
            assert body.read() == b"glTF\x02"

    def test_delete_reports_whether_anything_went_away(self, s3_store):
        """S3 deletes are idempotent and say nothing, so existence is checked first."""
        s3_store.put_bytes("body.stl", b"x")
        assert s3_store.delete("body.stl") is True
        assert s3_store.delete("body.stl") is False


class TestMissingArtifacts:
    def test_a_missing_key_reads_as_absent(self, s3_store):
        assert s3_store.exists("never-rendered.stl") is False
        assert s3_store.size("never-rendered.stl") is None

    def test_opening_a_missing_key_raises_not_found(self, s3_store):
        with pytest.raises(ArtifactNotFound):
            s3_store.open("never-rendered.stl")

    def test_publishing_a_file_that_is_not_on_disk_raises(self, s3_store, tmp_path):
        with pytest.raises(ArtifactNotFound):
            s3_store.put_file("body.stl", tmp_path / "nothing-here.stl")

    def test_an_upload_failure_is_raised_not_swallowed(self, s3_store, fake_s3_client, tmp_path):
        """A silent upload failure is exactly the quiet 404 this seam prevents."""
        src = tmp_path / "body.stl"
        src.write_bytes(b"x")

        def explode(**_kwargs):
            raise FakeClientError("InternalError", 500, "storage is having a day")

        fake_s3_client.upload_file = explode
        with pytest.raises(ArtifactStoreError):
            s3_store.put_file("body.stl", src)

    def test_a_non_404_read_failure_is_raised_not_reported_as_missing(self, s3_store, fake_s3_client):
        def explode(**_kwargs):
            raise FakeClientError("AccessDenied", 403, "no")

        fake_s3_client.get_object = explode
        with pytest.raises(ArtifactStoreError):
            s3_store.open("body.stl")

    def test_a_broken_existence_check_degrades_to_a_miss_and_warns(
        self, s3_store, fake_s3_client, caplog
    ):
        """A store that cannot answer must slow renders down, not fail them.

        But never silently: a permission fault answering every key looks
        exactly like a permanently cold cache, so it is logged.
        """
        def explode(**_kwargs):
            raise FakeClientError("AccessDenied", 403, "no")

        fake_s3_client.head_object = explode
        with caplog.at_level("WARNING"):
            assert s3_store.exists("body.stl") is False
        assert "existence check failed" in caplog.text


class TestKeySafety:
    @pytest.mark.parametrize("bad", ["../../etc/passwd", "/etc/passwd", "a/../../x"])
    def test_traversal_never_reaches_the_wire(self, s3_store, fake_s3_client, bad):
        """There is no filesystem here to bounce an escaping path off.

        ``../../etc/passwd`` is an ordinary object name and a bucket prefix
        would not contain it, so the key rule is the only guard there is.
        """
        with pytest.raises(InvalidArtifactKey):
            s3_store.put_bytes(bad, b"x")
        assert fake_s3_client.calls == []
        assert s3_store.exists(bad) is False
        assert s3_store.size(bad) is None
        assert s3_store.delete(bad) is False


class TestFailClosed:
    def test_check_ready_passes_against_a_reachable_bucket(self, s3_store):
        s3_store.check_ready()

    def test_check_ready_refuses_an_unreachable_bucket(self, fake_s3_client):
        """Startup must die rather than 404 every completed render afterwards."""
        store = S3ArtifactStore(
            bucket="not-provisioned",
            endpoint_url="http://object-store.test:9000",
            client=fake_s3_client,
        )
        with pytest.raises(ArtifactStoreError, match="unreachable"):
            store.check_ready()

    def test_the_refusal_names_the_likely_cause(self, fake_s3_client):
        store = S3ArtifactStore(bucket="not-provisioned", client=fake_s3_client)
        with pytest.raises(ArtifactStoreError, match="does not exist"):
            store.check_ready()

    def test_rejected_credentials_say_so(self, fake_s3_client):
        def explode(**_kwargs):
            raise FakeClientError("InvalidAccessKeyId", 403, "nope")

        fake_s3_client.head_bucket = explode
        store = S3ArtifactStore(bucket="renders", client=fake_s3_client)
        with pytest.raises(ArtifactStoreError, match="AWS_ACCESS_KEY_ID"):
            store.check_ready()

    def test_a_bucketless_configuration_refuses_to_construct(self):
        with pytest.raises(ArtifactStoreError, match="RENDER_ARTIFACT_S3_BUCKET"):
            S3ArtifactStore(bucket="", client=FakeS3Client())


class TestNoCredentialLeak:
    def test_describe_carries_no_secret(self, s3_store, monkeypatch):
        """describe() feeds the startup log; it must never carry credentials.

        They are not arguments to this class at all — botocore reads them from
        the environment — so there is nothing here to leak. This pins that.
        """
        # Deliberately not shaped like a real credential — a scanner-bait
        # literal would be a worse thing to commit than the bug it guards.
        marker_id = "test-key-id-must-not-appear"
        marker_secret = "test-secret-must-not-appear"
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", marker_id)
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", marker_secret)
        rendered = repr(s3_store.describe()) + repr(s3_store)
        assert marker_id not in rendered
        assert marker_secret not in rendered
        assert set(s3_store.describe()) == {"kind", "bucket", "endpoint", "region", "prefix"}

    def test_no_presigned_or_public_url_is_ever_produced(self, s3_store):
        """Artifacts are streamed through the API, never redirected to.

        A bucket URL handed to a browser would route around the private-project
        gate on /static and the tier gate on the download route. There is
        deliberately no method here that could produce one.
        """
        surface = {name for name in dir(s3_store) if not name.startswith("_")}
        assert not {n for n in surface if "presign" in n or "public_url" in n or n == "url"}
