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

import logging
import os
from typing import BinaryIO

from services.storage.base import (
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
    def open(self, key: str) -> BinaryIO:
        safe_key = normalize_key(key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.object_key(safe_key))
        except Exception as exc:
            if _is_missing(exc):
                raise ArtifactNotFound(safe_key) from exc
            raise ArtifactStoreError(
                f"Failed to read artifact {safe_key!r} from bucket {self.bucket!r}: {exc}"
            ) from exc
        return response["Body"]

    def exists(self, key: str) -> bool:
        try:
            safe_key = normalize_key(key)
        except InvalidArtifactKey:
            return False
        try:
            self.client.head_object(Bucket=self.bucket, Key=self.object_key(safe_key))
            return True
        except Exception as exc:
            if _is_missing(exc):
                return False
            # Anything else — a permission fault, a wrong bucket, a network
            # blip — is reported as absent so the caller degrades to "render it
            # again" rather than failing the request, but it is never silent:
            # a store that answers this way for every key would otherwise look
            # exactly like a permanently cold cache.
            logger.warning(
                "Artifact store existence check failed for %r in bucket %r: %s",
                safe_key, self.bucket, exc,
            )
            return False

    def size(self, key: str) -> int | None:
        try:
            safe_key = normalize_key(key)
        except InvalidArtifactKey:
            return None
        try:
            head = self.client.head_object(Bucket=self.bucket, Key=self.object_key(safe_key))
        except Exception as exc:
            if not _is_missing(exc):
                logger.warning(
                    "Artifact store size lookup failed for %r in bucket %r: %s",
                    safe_key, self.bucket, exc,
                )
            return None
        content_length = head.get("ContentLength")
        return int(content_length) if content_length is not None else None

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
