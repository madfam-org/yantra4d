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
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
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


@dataclass(frozen=True)
class ArtifactInfo:
    """What a store knows about one artifact without reading its bytes.

    Everything that used to be learned from ``os.stat`` on a file in the static
    directory — is it there, how big, how old, and (for revalidation) has it
    changed — comes from here instead, so the same question has an answer when
    the artifact is an object in a bucket.

    ``modified_at`` is epoch seconds so the two backends are directly
    comparable: the GC sorts on it and the read path renders it as
    ``Last-Modified``. ``etag`` is whatever the backend can supply cheaply
    (S3 hands one back on every ``HEAD``); when it is ``None`` the read path
    derives one from size and mtime, which is what Werkzeug does for a file.
    """

    key: str
    size: int
    modified_at: float
    etag: str | None = None
    content_type: str | None = None


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
    def open(self, key: str, *, start: int | None = None, end: int | None = None) -> BinaryIO:
        """Open the artifact for binary reading. Raises :class:`ArtifactNotFound`.

        *start* and *end* select a half-open byte range ``[start, end)``. A
        backend that can ask its storage for exactly those bytes should — the
        point of the range arguments is that a ``Range`` request for the last
        kilobyte of a 200 MB mesh does not drag the whole object through the
        API pod.
        """

    @abstractmethod
    def stat(self, key: str) -> ArtifactInfo | None:
        """Metadata for *key*, or ``None`` when nothing is stored under it.

        The one primitive behind ``exists``, ``size``, the GC's age and size
        passes, and the read path's ``ETag`` / ``Last-Modified``. A backend
        implements this and gets those for free.
        """

    @abstractmethod
    def list(self, prefix: str = "") -> list[ArtifactInfo]:
        """Every artifact whose key starts with *prefix*, in key order.

        This is what replaced ``os.scandir``/``glob.glob`` over the static
        directory. Both backends list the whole store, nested keys included:
        nothing produces a nested layout today, but a backend that quietly
        skipped one would make the two behave differently for a reason no
        caller could see.

        *prefix* is matched literally against the key, not as a path segment,
        so ``list("gridfinity_preview_")`` finds one project's renders.
        """

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Remove the artifact. ``True`` if something was removed."""

    def exists(self, key: str) -> bool:
        """Whether an artifact is stored under *key*."""
        return self.stat(key) is not None

    def size(self, key: str) -> int | None:
        """Size in bytes, or ``None`` when the artifact is absent."""
        info = self.stat(key)
        return info.size if info is not None else None

    # ── materialising ──────────────────────────────────────────────────
    def local_path(self, key: str) -> Path | None:
        """A real file already holding this artifact, or ``None``.

        Only a filesystem-backed store has one. Callers that need a path — the
        verifier subprocess, trimesh, a printer upload — use
        :func:`services.storage.local_artifact`, which falls back to
        :meth:`fetch_to_path` when this returns ``None``.
        """
        return None

    def fetch_to_path(self, key: str, destination: str | os.PathLike) -> Path:
        """Copy the artifact to *destination* and return it.

        The generic implementation streams through :meth:`open`, which is
        correct for every backend; one that can download faster may override.
        """
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        body = self.open(key)
        try:
            with target.open("wb") as out:
                shutil.copyfileobj(body, out)
        finally:
            # botocore's StreamingBody is only a context manager on recent
            # versions; closing it by hand works on every one.
            close = getattr(body, "close", None)
            if callable(close):
                close()
        return target

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

    def describe(self) -> dict:
        """Operator-facing summary for ``/api/health``. Never includes credentials."""
        return {"kind": self.kind}
