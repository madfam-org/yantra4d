"""Shared test fixtures for backend API tests."""
import datetime
import hashlib
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
    # The private cartridge root defaults to <repo>/private-projects. Pin it
    # inside tmp_path too, or a test would resolve slugs out of the developer's
    # real private mount and pass or fail depending on who is running it.
    monkeypatch.setattr(Config, "PRIVATE_PROJECTS_DIR", tmp_path / "private-projects")
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
    """In-memory S3, one bucket deep.

    Reproduces the response *shapes* the store reads, not just the happy path:
    `LastModified` as an aware datetime and a quoted `ETag` (both of which the
    read path renders into HTTP headers), `Range` on `get_object`, and
    `list_objects_v2` with continuation tokens — paging is where a hand-rolled
    listing usually goes wrong, and the GC depends on seeing every object.

    `tests/unit/test_artifact_store_moto.py` runs the same assertions against
    real botocore via moto, so this double cannot drift into agreeing with the
    store about something S3 does not actually do.
    """

    #: Objects returned per `list_objects_v2` page. Small on purpose: the
    #: paging loop is exercised by an ordinary two-object listing.
    page_size = 2

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
    def head_bucket(self, Bucket):  # boto3 spells its parameters this way
        self._require_bucket(Bucket)
        return {}

    def upload_file(self, Filename, Bucket, Key, ExtraArgs=None):  # boto3 spells its parameters this way
        self._require_bucket(Bucket)
        self.calls.append(("upload_file", Bucket, Key, dict(ExtraArgs or {})))
        with open(Filename, "rb") as fh:
            body = fh.read()
        self._store(Bucket, Key, body, (ExtraArgs or {}).get("ContentType", ""))

    def put_object(self, Bucket, Key, Body, ContentType=None):  # boto3 spells its parameters this way
        self._require_bucket(Bucket)
        self.calls.append(("put_object", Bucket, Key, ContentType))
        self._store(Bucket, Key, Body, ContentType or "")

    def _store(self, bucket, key, body, content_type):
        self.objects[(bucket, key)] = {
            "body": body,
            "content_type": content_type,
            "last_modified": datetime.datetime.now(datetime.UTC),
            "etag": f'"{hashlib.md5(body).hexdigest()}"',
        }

    def get_object(self, Bucket, Key, Range=None):  # boto3 spells its parameters this way
        entry = self._require_object(Bucket, Key, "NoSuchKey", 404)
        body = entry["body"]
        if Range:
            # `bytes=first-last` (inclusive) or `bytes=first-`.
            spec = Range.split("=", 1)[1]
            first_s, _, last_s = spec.partition("-")
            first = int(first_s)
            body = body[first:int(last_s) + 1] if last_s else body[first:]
        return {
            "Body": io.BytesIO(body),
            "ContentLength": len(body),
            "LastModified": entry["last_modified"],
            "ETag": entry["etag"],
        }

    def head_object(self, Bucket, Key):  # boto3 spells its parameters this way
        entry = self._require_object(Bucket, Key, "404", 404)
        return {
            "ContentLength": len(entry["body"]),
            "ContentType": entry["content_type"],
            "LastModified": entry["last_modified"],
            "ETag": entry["etag"],
        }

    def list_objects_v2(self, Bucket, Prefix="", ContinuationToken=None):  # boto3 spells its parameters this way
        self._require_bucket(Bucket)
        self.calls.append(("list_objects_v2", Bucket, Prefix, ContinuationToken))
        keys = sorted(k for b, k in self.objects if b == Bucket and k.startswith(Prefix))
        start = keys.index(ContinuationToken) if ContinuationToken in keys else 0
        page = keys[start:start + self.page_size]
        rest = keys[start + self.page_size:]
        return {
            "Contents": [
                {
                    "Key": key,
                    "Size": len(self.objects[(Bucket, key)]["body"]),
                    "LastModified": self.objects[(Bucket, key)]["last_modified"],
                    "ETag": self.objects[(Bucket, key)]["etag"],
                }
                for key in page
            ],
            "IsTruncated": bool(rest),
            **({"NextContinuationToken": rest[0]} if rest else {}),
        }

    def delete_object(self, Bucket, Key):  # boto3 spells its parameters this way
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
