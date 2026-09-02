"""Artifact store interface and key rules.

Render artifacts (STL/GLB/3MF/…) are produced by the render worker and served
by the API. Today both are containers in one pod sharing a `render-output`
emptyDir, and "the artifact" is a file on a disk both processes can see. That
implicit sharing is what stops the worker from being split into its own
Deployment: split the pod and every render would succeed and then 404 on
download, quietly (see ADR-014 and
`docs/operations/render-artifact-storage.md`).

This module puts a seam there. Producers `put` an artifact under a **key** and
readers `open`/`stream` it back by that key; where the bytes actually live is
the backend's business. Two backends exist:

``fs``
    Today's directory (``Config.STATIC_DIR``). The default, and deliberately
    a no-op for artifacts that already sit at their final path — a render that
    wrote straight into the static directory is *published* without a copy, so
    paths, inodes, mtimes and served headers are byte-for-byte what they were
    before this abstraction existed.

``s3``
    Any S3-compatible endpoint (MinIO in this platform's own clusters), with
    path-style addressing. Selected only by explicit configuration.

## Keys

A key is the artifact-relative path already used in URLs today: the file name
under the static directory, e.g. ``gridfinity_preview_9f2c1a_body.stl``. The
`/static/<key>` and download URL shapes do not change, which is what keeps
#78's private-project gate and the download tier gate applying unchanged —
both read the *name*, and neither ever sees a bucket URL. Artifacts are never
served by handing out a presigned or public object URL: the API streams them,
so every request keeps passing through those gates.

Keys are relative and forward-slashed. Subdirectories are accepted so a future
layout can nest, but nothing produces them today.
"""
from __future__ import annotations

import mimetypes
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

#: Every key that reaches a backend has passed :func:`normalize_key`.
_ILLEGAL_KEY_SEGMENTS = {"", ".", ".."}


class ArtifactStoreError(RuntimeError):
    """The store is misconfigured or unreachable.

    Raised at startup by :meth:`ArtifactStore.check_ready` so a deployment
    pointed at a bucket it cannot reach fails loudly instead of accepting
    renders it will not be able to serve back.
    """


class ArtifactNotFound(KeyError):
    """No artifact is stored under this key."""


class InvalidArtifactKey(ValueError):
    """The key is not a safe, relative, artifact-relative path."""


def normalize_key(key: str | os.PathLike) -> str:
    """Return *key* as a safe relative POSIX path, or raise.

    This is the one place traversal is rejected. It has to be, because the s3
    backend has no filesystem to bounce an escaping path off: ``../../etc/passwd``
    is a perfectly ordinary S3 object name, and a bucket prefix would not
    contain it. The filesystem backend re-checks containment on top of this.
    """
    if isinstance(key, os.PathLike):
        key = os.fspath(key)
    if not isinstance(key, str):
        raise InvalidArtifactKey(f"Artifact key must be a string, got {type(key).__name__}")

    candidate = key.replace("\\", "/").strip()
    if not candidate:
        raise InvalidArtifactKey("Artifact key must not be empty")
    if "\x00" in candidate:
        raise InvalidArtifactKey("Artifact key must not contain NUL")
    if candidate.startswith("/"):
        raise InvalidArtifactKey(f"Artifact key must be relative: {key!r}")

    segments = candidate.split("/")
    if any(segment in _ILLEGAL_KEY_SEGMENTS for segment in segments):
        raise InvalidArtifactKey(f"Artifact key must not contain empty or dot segments: {key!r}")

    return "/".join(segments)


def key_for_path(path: str | os.PathLike, root: str | os.PathLike | None) -> str:
    """The store key for an artifact that a renderer just wrote to *path*.

    Inside *root* the key is the relative path, which is exactly the name the
    `/static/<name>` URL already carries. Outside it — or with no root at all,
    as for a non-filesystem backend whose staging directory is incidental — the
    file name alone is the key, matching how every artifact is addressed today.
    """
    name = Path(path).name
    if root is None:
        return normalize_key(name)
    try:
        relative = Path(path).resolve().relative_to(Path(root).resolve())
    except (ValueError, OSError):
        return normalize_key(name)
    return normalize_key(relative.as_posix())


def guess_content_type(key: str) -> str:
    """MIME type for *key*, matching what Werkzeug would serve for the same name.

    Deliberately the plain :mod:`mimetypes` lookup with an
    ``application/octet-stream`` fallback — the same call Werkzeug's
    ``send_file`` makes — so a mesh streamed from object storage is labelled
    exactly as the same mesh served off disk.
    """
    content_type, _encoding = mimetypes.guess_type(key)
    return content_type or "application/octet-stream"


class ArtifactStore(ABC):
    """Where render artifacts live, addressed by key."""

    #: Short name reported by ``/api/health`` and used in logs. ``fs`` | ``s3``.
    kind: str = "abstract"

    # ── writing ────────────────────────────────────────────────────────
    @abstractmethod
    def put_file(self, key: str, source_path: str | os.PathLike) -> str:
        """Store the file at *source_path* under *key*. Returns the key.

        Renderers are subprocesses that write to a real path; this is how that
        path becomes an artifact. A backend whose storage *is* that path may
        legitimately do nothing.
        """

    @abstractmethod
    def put_bytes(self, key: str, data: bytes) -> str:
        """Store *data* under *key*. Returns the key."""

    # ── reading ────────────────────────────────────────────────────────
    @abstractmethod
    def open(self, key: str) -> BinaryIO:
        """Open the artifact for binary reading. Raises :class:`ArtifactNotFound`."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Whether an artifact is stored under *key*."""

    @abstractmethod
    def size(self, key: str) -> int | None:
        """Size in bytes, or ``None`` when the artifact is absent."""

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove the artifact. ``True`` if something was removed."""

    # ── capability hooks ───────────────────────────────────────────────
    def local_root(self) -> Path | None:
        """The real directory backing this store, or ``None``.

        The read path uses this to keep the filesystem backend on Flask's
        ``send_from_directory``/``send_file`` — conditional requests, ranges,
        ETag, ``Last-Modified`` and the zero-copy send all intact — instead of
        re-implementing them over a generic byte stream. A backend with no
        local directory gets streamed instead.
        """
        return None

    def check_ready(self) -> None:
        """Fail loudly if this store cannot be used. Called once at startup."""
        return None

    def describe(self) -> dict:
        """Operator-facing summary for ``/api/health``. Never includes credentials."""
        return {"kind": self.kind}
