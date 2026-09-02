"""Shared test fixtures for backend API tests."""
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Ensure Config paths point to tmp_path and manifest cache is cleared for every test."""
    from config import Config
    monkeypatch.setattr(Config, "PROJECTS_DIR", tmp_path)
    monkeypatch.setattr(Config, "CARTRIDGES_DIRS", [tmp_path])
    monkeypatch.setattr(Config, "SCAD_DIR", tmp_path)
    monkeypatch.setattr(Config, "MULTI_PROJECT", True)
    monkeypatch.setattr(Config, "AUTH_ENABLED", False)
    monkeypatch.setattr(Config, "LIBS_DIR", tmp_path / "libs")
    monkeypatch.setattr(Config, "OPENSCADPATH", str(tmp_path / "libs"))

    # The artifact store is a process-wide singleton whose filesystem backend
    # reads Config.STATIC_DIR at call time. Dropping it between tests keeps a
    # test that selects the s3 backend from leaking into the next one.
    from services.storage import reset_artifact_store
    reset_artifact_store()

    import manifest as manifest_mod
    manifest_mod.manifest_service._manifest_cache.clear()
    yield
    manifest_mod.manifest_service._manifest_cache.clear()
    reset_artifact_store()


@pytest.fixture(autouse=True)
def _disable_rate_limits():
    """Disable Flask-Limiter in tests to prevent rate limit interference."""
    from extensions import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True


# ──────────────────────────────────────────────
# A stand-in for an S3-compatible endpoint
# ──────────────────────────────────────────────
#
# The object-storage backend is exercised against this rather than a live MinIO
# or a mocking library, so the backend tests carry no extra dependency and run
# anywhere the rest of the suite runs. It reproduces the parts of the boto3 S3
# client that `S3ArtifactStore` actually calls, including the error shapes that
# decide control flow: botocore reports a missing key as ``NoSuchKey`` from
# ``get_object`` but as the bare status code ``404`` from ``head_object`` and
# ``head_bucket`` (a HEAD response has no body to carry a code), and the store
# has to treat all three as "not here".


class FakeClientError(Exception):
    """Shaped like botocore's ClientError, which is read by response dict."""

    def __init__(self, code: str, status: int, message: str = ""):
        super().__init__(f"{code}: {message}")
        self.response = {
            "Error": {"Code": code, "Message": message},
            "ResponseMetadata": {"HTTPStatusCode": status},
        }


class FakeS3Client:
    """In-memory S3, one bucket deep."""

    def __init__(self, buckets=("renders",)):
        self.objects: dict[tuple[str, str], dict] = {}
        self.buckets = set(buckets)
        self.calls: list[tuple] = []

    # ── helpers ────────────────────────────────────────────────────────
    def _require_bucket(self, bucket):
        if bucket not in self.buckets:
            raise FakeClientError("NoSuchBucket", 404, f"bucket {bucket}")

    def _require_object(self, bucket, key, code, status):
        self._require_bucket(bucket)
        if (bucket, key) not in self.objects:
            raise FakeClientError(code, status, key)
        return self.objects[(bucket, key)]

    # ── the surface S3ArtifactStore uses ───────────────────────────────
    def head_bucket(self, Bucket):  # noqa: N803 — boto3's parameter name
        self._require_bucket(Bucket)
        return {}

    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None):  # noqa: N803
        self._require_bucket(Bucket)
        self.calls.append(("upload_file", Bucket, Key, dict(ExtraArgs or {})))
        with open(Filename, "rb") as fh:
            body = fh.read()
        self.objects[(Bucket, Key)] = {
            "body": body,
            "content_type": (ExtraArgs or {}).get("ContentType", ""),
        }

    def put_object(self, Bucket, Key, Body, ContentType=None):  # noqa: N803
        self._require_bucket(Bucket)
        self.calls.append(("put_object", Bucket, Key, ContentType))
        self.objects[(Bucket, Key)] = {"body": Body, "content_type": ContentType or ""}

    def get_object(self, Bucket, Key):  # noqa: N803
        entry = self._require_object(Bucket, Key, "NoSuchKey", 404)
        return {"Body": io.BytesIO(entry["body"]), "ContentLength": len(entry["body"])}

    def head_object(self, Bucket, Key):  # noqa: N803
        entry = self._require_object(Bucket, Key, "404", 404)
        return {"ContentLength": len(entry["body"]), "ContentType": entry["content_type"]}

    def delete_object(self, Bucket, Key):  # noqa: N803
        self._require_bucket(Bucket)
        self.objects.pop((Bucket, Key), None)
        return {}


@pytest.fixture
def fake_s3_client():
    return FakeS3Client()


@pytest.fixture
def s3_store(fake_s3_client):
    """An S3ArtifactStore wired to the in-memory endpoint."""
    from services.storage import S3ArtifactStore
    return S3ArtifactStore(
        bucket="renders",
        endpoint_url="http://object-store.test:9000",
        region="us-east-1",
        prefix="renders/v1",
        client=fake_s3_client,
    )
