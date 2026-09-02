"""S3-compatible artifact store (MinIO, Ceph RGW, AWS S3).

Selected only by ``RENDER_ARTIFACT_STORE=s3``. Nothing in this module runs on
the default path, and ``boto3`` is imported lazily so a deployment on the
filesystem backend never needs it installed to start.

Three choices are worth stating outright, because each one is a security or
operability property rather than a style preference:

**Path-style addressing.** Virtual-host addressing (``bucket.host``) needs
wildcard DNS and a wildcard certificate, which no in-cluster MinIO has. Every
request is therefore ``endpoint/bucket/key``.

**Credentials come from the environment only.** The access key and secret are
read by botocore from the standard ``AWS_ACCESS_KEY_ID`` /
``AWS_SECRET_ACCESS_KEY`` / ``AWS_SESSION_TOKEN`` variables. They are never
arguments here, never stored on the instance, and never appear in
:meth:`describe`, so no log line or ``/api/health`` payload can leak them.

**Artifacts are streamed, never redirected to.** There is no presigned-URL or
public-bucket path in this class, on purpose. Every read goes back through the
API, which is what keeps the private-project gate on ``/static`` and the tier
gate on the download route applying to object-storage artifacts exactly as
they apply to files on disk. A bucket URL handed to a browser would route
around both.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
from typing import BinaryIO

from services.storage.base import (
    ArtifactInfo,
    ArtifactNotFound,
    ArtifactStore,
    ArtifactStoreError,
    InvalidArtifactKey,
    guess_content_type,
    normalize_key,
)

logger = logging.getLogger(__name__)

#: Error codes an S3 implementation may use for "that object is not here".
_MISSING_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
#: Codes that mean the *bucket* is wrong — a configuration fault, not a miss.
_BUCKET_CODES = frozenset({"NoSuchBucket", "404 Bucket"})


def _error_code(exc: Exception) -> str:
    """The S3 error code on a botocore ``ClientError``, or ``""``.

    Read off the response dict rather than by catching ``ClientError``, so this
    works against any client that speaks the same shape — including the test
    double — without importing botocore at module scope.
    """
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return ""
    error = response.get("Error")
    if isinstance(error, dict) and error.get("Code") is not None:
        return str(error["Code"])
    metadata = response.get("ResponseMetadata")
    if isinstance(metadata, dict) and metadata.get("HTTPStatusCode") is not None:
        return str(metadata["HTTPStatusCode"])
    return ""


def _is_missing(exc: Exception) -> bool:
    return _error_code(exc) in _MISSING_CODES


def _epoch(value) -> float:
    """Epoch seconds from whatever S3 handed back for ``LastModified``.

    botocore parses it to an aware ``datetime``; a fake or an odd gateway may
    send a number or nothing at all. An unknown timestamp is 0.0 rather than
    "now", so the GC never mistakes an artifact of unknown age for a fresh one
    and keep it forever.
    """
    if value is None:
        return 0.0
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt.UTC)
        return value.timestamp()
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _clean_etag(value) -> str | None:
    """S3 quotes its ETags; HTTP layers below add their own quoting."""
    if not isinstance(value, str):
        return None
    cleaned = value.strip().strip('"')
    return cleaned or None


class S3ArtifactStore(ArtifactStore):
    """Artifacts as objects in an S3-compatible bucket."""

    kind = "s3"

    def __init__(
        self,
        bucket: str,
        *,
        endpoint_url: str | None = None,
        region: str | None = None,
        prefix: str = "",
        client=None,
    ):
        if not bucket:
            raise ArtifactStoreError(
                "RENDER_ARTIFACT_STORE=s3 requires RENDER_ARTIFACT_S3_BUCKET to be set"
            )
        self.bucket = bucket
        self.endpoint_url = endpoint_url or None
        self.region = region or None
        # A prefix is a key namespace, so it obeys the same rules as a key and
        # is stored without surrounding slashes.
        self.prefix = normalize_key(prefix) if prefix and prefix.strip("/") else ""
        self._client = client

    # ── client ─────────────────────────────────────────────────────────
    @property
    def client(self):
        """The boto3 S3 client, built once on first use.

        Built lazily so importing this module — which the factory does merely
        to decide it is *not* wanted — never requires boto3.
        """
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def _build_client(self):
        try:
            import boto3
            from botocore.config import Config as BotoConfig
        except ImportError as exc:  # pragma: no cover - exercised by deployment, not tests
            raise ArtifactStoreError(
                "RENDER_ARTIFACT_STORE=s3 requires boto3; install it or set "
                "RENDER_ARTIFACT_STORE=fs"
            ) from exc

        return boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=self.region,
            config=BotoConfig(
                # MinIO and friends have no wildcard DNS: bucket goes in the path.
                s3={"addressing_style": "path"},
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    # ── keys ───────────────────────────────────────────────────────────
    def object_key(self, key: str) -> str:
        """Full object name for an artifact key, including the configured prefix."""
        safe_key = normalize_key(key)
        return f"{self.prefix}/{safe_key}" if self.prefix else safe_key

    # ── writing ────────────────────────────────────────────────────────
    def put_file(self, key: str, source_path: str | os.PathLike) -> str:
        safe_key = normalize_key(key)
        source = os.fspath(source_path)
        if not os.path.isfile(source):
            raise ArtifactNotFound(f"No file to publish at {source_path!r}")
        try:
            self.client.upload_file(
                source,
                self.bucket,
                self.object_key(safe_key),
                ExtraArgs={"ContentType": guess_content_type(safe_key)},
            )
        except Exception as exc:
            raise ArtifactStoreError(
                f"Failed to upload artifact {safe_key!r} to bucket {self.bucket!r}: {exc}"
            ) from exc
        return safe_key

    def put_bytes(self, key: str, data: bytes) -> str:
        safe_key = normalize_key(key)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self.object_key(safe_key),
                Body=data,
                ContentType=guess_content_type(safe_key),
            )
        except Exception as exc:
            raise ArtifactStoreError(
                f"Failed to write artifact {safe_key!r} to bucket {self.bucket!r}: {exc}"
            ) from exc
        return safe_key

    # ── reading ────────────────────────────────────────────────────────
    def open(self, key: str, *, start: int | None = None, end: int | None = None) -> BinaryIO:
        safe_key = normalize_key(key)
        params = {"Bucket": self.bucket, "Key": self.object_key(safe_key)}
        if start is not None or end is not None:
            # HTTP byte ranges are inclusive on both sides; the store's are
            # half-open, so the last byte is `end - 1`. An open-ended range is
            # `bytes=start-`, which S3 answers to the end of the object.
            first = start or 0
            params["Range"] = f"bytes={first}-" if end is None else f"bytes={first}-{end - 1}"
        try:
            response = self.client.get_object(**params)
        except Exception as exc:
            if _is_missing(exc):
                raise ArtifactNotFound(safe_key) from exc
            raise ArtifactStoreError(
                f"Failed to read artifact {safe_key!r} from bucket {self.bucket!r}: {exc}"
            ) from exc
        return response["Body"]

    def _head(self, key: str, purpose: str) -> dict | None:
        """``head_object`` for *key*, or ``None`` when it is absent or unanswerable.

        A fault that is not a miss — a permission problem, a wrong bucket, a
        network blip — is reported as absent so the caller degrades to "render
        it again" rather than failing the request. Never silently, though: a
        store answering this way for every key looks exactly like a permanently
        cold cache, and *purpose* is what tells the operator which read gave up.
        """
        try:
            safe_key = normalize_key(key)
        except InvalidArtifactKey:
            return None
        try:
            return self.client.head_object(Bucket=self.bucket, Key=self.object_key(safe_key))
        except Exception as exc:
            if not _is_missing(exc):
                logger.warning(
                    "Artifact store %s failed for %r in bucket %r: %s",
                    purpose, safe_key, self.bucket, exc,
                )
            return None

    def exists(self, key: str) -> bool:
        return self._head(key, "existence check") is not None

    def size(self, key: str) -> int | None:
        head = self._head(key, "size lookup")
        if head is None:
            return None
        content_length = head.get("ContentLength")
        return int(content_length) if content_length is not None else None

    def stat(self, key: str) -> ArtifactInfo | None:
        head = self._head(key, "stat")
        if head is None:
            return None
        try:
            safe_key = normalize_key(key)
        except InvalidArtifactKey:  # pragma: no cover - _head already refused it
            return None
        return ArtifactInfo(
            key=safe_key,
            size=int(head.get("ContentLength") or 0),
            modified_at=_epoch(head.get("LastModified")),
            etag=_clean_etag(head.get("ETag")),
            content_type=head.get("ContentType") or None,
        )

    def list(self, prefix: str = "") -> list[ArtifactInfo]:
        """Every object under the store prefix, as artifact keys.

        Paginated by hand rather than with a paginator, so the fake client the
        tests run against only has to implement ``list_objects_v2`` — and so a
        bucket holding more than one page of renders is listed completely,
        which is exactly the case the GC has to get right.
        """
        namespace = f"{self.prefix}/" if self.prefix else ""
        found: list[ArtifactInfo] = []
        token: str | None = None
        while True:
            params = {"Bucket": self.bucket, "Prefix": f"{namespace}{prefix}"}
            if token:
                params["ContinuationToken"] = token
            try:
                page = self.client.list_objects_v2(**params)
            except Exception as exc:
                logger.warning(
                    "Artifact listing failed for prefix %r in bucket %r: %s",
                    prefix, self.bucket, exc,
                )
                break
            for entry in page.get("Contents") or []:
                object_name = entry.get("Key") or ""
                if namespace:
                    if not object_name.startswith(namespace):
                        continue
                    object_name = object_name[len(namespace):]
                if not object_name or object_name.endswith("/"):
                    # A directory placeholder some consoles create. Not an
                    # artifact, and normalize_key would reject its empty tail.
                    continue
                found.append(
                    ArtifactInfo(
                        key=object_name,
                        size=int(entry.get("Size") or 0),
                        modified_at=_epoch(entry.get("LastModified")),
                        etag=_clean_etag(entry.get("ETag")),
                    )
                )
            if not page.get("IsTruncated"):
                break
            token = page.get("NextContinuationToken")
            if not token:
                break
        found.sort(key=lambda info: info.key)
        return found

    def delete(self, key: str) -> bool:
        try:
            safe_key = normalize_key(key)
        except InvalidArtifactKey:
            return False
        # S3 deletes are idempotent and report nothing about what was there, so
        # the "did something go away" answer has to be established first.
        if not self.exists(safe_key):
            return False
        try:
            self.client.delete_object(Bucket=self.bucket, Key=self.object_key(safe_key))
        except Exception as exc:
            logger.warning(
                "Artifact store delete failed for %r in bucket %r: %s",
                safe_key, self.bucket, exc,
            )
            return False
        return True

    # ── lifecycle ──────────────────────────────────────────────────────
    def check_ready(self) -> None:
        """Fail closed: refuse to start against a bucket we cannot reach.

        Starting anyway would accept renders, publish them nowhere, and hand
        back URLs that 404 — the exact quiet failure this whole change exists
        to prevent.
        """
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception as exc:
            code = _error_code(exc)
            hint = ""
            if code in _BUCKET_CODES or code in _MISSING_CODES:
                hint = " — the bucket does not exist; provision it before enabling the s3 store"
            elif code in {"403", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                hint = (
                    " — credentials were rejected; check AWS_ACCESS_KEY_ID and "
                    "AWS_SECRET_ACCESS_KEY in the environment"
                )
            raise ArtifactStoreError(
                f"Artifact bucket {self.bucket!r} is unreachable at "
                f"{self.endpoint_url or 'the default AWS endpoint'}: {exc}{hint}"
            ) from exc

    def describe(self) -> dict:
        """Operator-facing summary. Contains no credentials, by construction."""
        return {
            "kind": self.kind,
            "bucket": self.bucket,
            "endpoint": self.endpoint_url or "",
            "region": self.region or "",
            "prefix": self.prefix,
        }

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"S3ArtifactStore(bucket={self.bucket!r}, prefix={self.prefix!r})"
