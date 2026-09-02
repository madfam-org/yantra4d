"""The S3 backend against a real botocore client.

Everything else in the suite drives `S3ArtifactStore` through `FakeS3Client`,
a hand-written double. A double is only worth what its fidelity is worth, and
this store makes decisions on details a double is very easy to get wrong: which
error code a *missing* object produces from `get_object` versus `head_object`,
that `LastModified` arrives as an aware datetime, that `ETag` comes quoted,
that `list_objects_v2` pages. So the same behaviours are asserted here against
boto3 talking to moto's in-process S3.

Skipped when moto is not installed — it is a test-only dependency and is
deliberately not in `requirements.txt`, since shipping a mocking library in the
API image to support a backend that is off by default would be absurd. CI
installs it alongside pytest.
"""
import pytest

pytest.importorskip("moto", reason="moto is a test-only dependency")

# Imported below the skip guard on purpose: without moto installed the module
# must not fail at import time, it must skip.
import boto3
from moto import mock_aws

from services.storage import (
    ArtifactNotFound,
    ArtifactStoreError,
    S3ArtifactStore,
    local_artifact,
)

BUCKET = "render-artifacts-test"
PREFIX = "renders/v1"
MESH = b"solid body\n" + b"y" * 200 + b"\nendsolid body\n"


@pytest.fixture
def aws_credentials(monkeypatch):
    """Dummy credentials so botocore signs; moto never checks them."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def store(aws_credentials):
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket=BUCKET)
        yield S3ArtifactStore(bucket=BUCKET, region="us-east-1", prefix=PREFIX, client=client)


class TestRoundTrip:
    def test_bytes_go_in_and_come_back(self, store):
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl")
        try:
            assert body.read() == MESH
        finally:
            body.close()

    def test_a_file_goes_in_with_its_content_type(self, store, tmp_path):
        source = tmp_path / "body.stl"
        source.write_bytes(MESH)
        store.put_file("body.stl", source)

        info = store.stat("body.stl")
        assert info is not None
        assert info.content_type == "model/stl"

    def test_the_prefix_namespaces_the_object_but_not_the_key(self, store):
        store.put_bytes("body.stl", MESH)
        raw = store.client.list_objects_v2(Bucket=BUCKET)["Contents"]
        assert [entry["Key"] for entry in raw] == [f"{PREFIX}/body.stl"]
        assert [info.key for info in store.list()] == ["body.stl"]


class TestStatShapes:
    def test_size_last_modified_and_etag_are_all_usable(self, store):
        import time as time_mod
        store.put_bytes("body.stl", MESH)

        info = store.stat("body.stl")
        assert info.size == len(MESH)
        # A float epoch, not a datetime: the GC does arithmetic on this and the
        # read path formats it as Last-Modified.
        assert isinstance(info.modified_at, float)
        assert abs(info.modified_at - time_mod.time()) < 300
        # Unquoted, because HTTP layers below add their own quoting.
        assert info.etag and not info.etag.startswith('"')

    def test_a_missing_object_stats_as_absent(self, store):
        assert store.stat("never-rendered.stl") is None
        assert store.exists("never-rendered.stl") is False
        assert store.size("never-rendered.stl") is None


class TestMissingObjectErrorCodes:
    """The codes the store branches on, straight from botocore.

    `get_object` reports `NoSuchKey`; `head_object` has no body to carry a code
    and reports the bare status `404`. Treating only one of them as "missing"
    is the classic way to make a cold cache look like an outage.
    """

    def test_get_object_on_a_missing_key_is_not_found(self, store):
        with pytest.raises(ArtifactNotFound):
            store.open("never-rendered.stl")

    def test_delete_reports_whether_anything_went_away(self, store):
        store.put_bytes("body.stl", MESH)
        assert store.delete("body.stl") is True
        assert store.delete("body.stl") is False


class TestRanges:
    @pytest.mark.parametrize("start,end", [(0, 10), (10, 40), (len(MESH) - 3, len(MESH))])
    def test_a_bounded_range_is_served_by_the_bucket(self, store, start, end):
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl", start=start, end=end)
        try:
            assert body.read() == MESH[start:end]
        finally:
            body.close()

    def test_an_open_ended_range_runs_to_the_end(self, store):
        store.put_bytes("body.stl", MESH)
        body = store.open("body.stl", start=len(MESH) - 5)
        try:
            assert body.read() == MESH[-5:]
        finally:
            body.close()


class TestListing:
    def test_listing_pages_past_the_first_thousand(self, store):
        """`list_objects_v2` caps a page at 1000 keys.

        The GC lists the whole bucket; a listing that stopped at the first page
        would leave everything past it to accumulate forever. 1001 objects is
        the cheapest way to actually cross that boundary.
        """
        for i in range(1001):
            store.put_bytes(f"part{i:04d}.stl", b"x")

        listed = store.list()

        assert len(listed) == 1001
        assert listed[0].key == "part0000.stl"
        assert listed[-1].key == "part1000.stl"

    def test_the_prefix_narrows_the_listing(self, store):
        store.put_bytes("gridfinity_preview_1_body.stl", MESH)
        store.put_bytes("otherproject_preview_1_body.stl", MESH)
        assert [info.key for info in store.list("gridfinity_")] == [
            "gridfinity_preview_1_body.stl"
        ]


class TestFailClosed:
    def test_an_unreachable_bucket_refuses_to_start(self, aws_credentials):
        with mock_aws():
            client = boto3.client("s3", region_name="us-east-1")
            store = S3ArtifactStore(bucket="never-provisioned", client=client)
            with pytest.raises(ArtifactStoreError) as raised:
                store.check_ready()
        assert "provision it" in str(raised.value)

    def test_a_provisioned_bucket_is_accepted(self, store):
        store.check_ready()


class TestMaterialising:
    def test_a_local_copy_is_made_and_then_removed(self, store):
        store.put_bytes("body.glb", MESH)
        with local_artifact("body.glb", store=store) as path:
            assert path.suffix == ".glb"
            assert path.read_bytes() == MESH
        assert not path.exists()
