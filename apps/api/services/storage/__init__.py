"""Render artifact storage: one interface, a filesystem backend, an S3 backend.

Import surface for the rest of the app::

    from services.storage import get_artifact_store, publish_artifact

`get_artifact_store()` returns the process-wide store chosen by
``RENDER_ARTIFACT_STORE`` (``fs`` by default — today's directory, unchanged).
`publish_artifact()` is what a renderer calls once it has written a file: under
``fs`` that is a no-op, under ``s3`` it uploads.

Why this exists at all: `docs/operations/render-artifact-storage.md`.
"""
from __future__ import annotations

import contextlib
import logging
import os
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path

from services.storage.base import (
    ArtifactInfo,
    ArtifactNotFound,
    ArtifactStore,
    ArtifactStoreError,
    InvalidArtifactKey,
    guess_content_type,
    key_for_path,
    normalize_key,
)
from services.storage.fs import FilesystemArtifactStore
from services.storage.s3 import S3ArtifactStore

logger = logging.getLogger(__name__)

__all__ = [
    "ArtifactInfo",
    "ArtifactNotFound",
    "ArtifactStore",
    "ArtifactStoreError",
    "FilesystemArtifactStore",
    "InvalidArtifactKey",
    "S3ArtifactStore",
    "artifact_key",
    "build_artifact_store",
    "get_artifact_store",
    "guess_content_type",
    "key_for_path",
    "local_artifact",
    "normalize_key",
    "publish_artifact",
    "publish_artifact_best_effort",
    "reset_artifact_store",
]

#: The two recognised values of ``RENDER_ARTIFACT_STORE``.
STORE_KINDS = ("fs", "s3")

_store: ArtifactStore | None = None
_store_lock = threading.Lock()


def build_artifact_store(kind: str | None = None) -> ArtifactStore:
    """Construct the store named by *kind* (default: the configured one).

    An unrecognised name raises rather than falling back to ``fs``. Falling
    back would be the friendlier behaviour and the wrong one: a typo in the
    deployment would then look like a working object-storage rollout while
    every artifact quietly went to local disk, and the pod that later replaced
    it would serve none of them.
    """
    from config import Config

    resolved = (kind if kind is not None else Config.RENDER_ARTIFACT_STORE or "fs").strip().lower()

    if resolved == "fs":
        return FilesystemArtifactStore()
    if resolved == "s3":
        return S3ArtifactStore(
            bucket=Config.RENDER_ARTIFACT_S3_BUCKET,
            endpoint_url=Config.RENDER_ARTIFACT_S3_ENDPOINT,
            region=Config.RENDER_ARTIFACT_S3_REGION,
            prefix=Config.RENDER_ARTIFACT_S3_PREFIX,
        )
    raise ArtifactStoreError(
        f"Unknown RENDER_ARTIFACT_STORE={resolved!r}; expected one of {', '.join(STORE_KINDS)}"
    )


def get_artifact_store() -> ArtifactStore:
    """The process-wide artifact store, built once."""
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = build_artifact_store()
    return _store


def set_artifact_store(store: ArtifactStore | None) -> None:
    """Install *store* as the process-wide store (or clear it). For tests and startup."""
    global _store
    with _store_lock:
        _store = store


def reset_artifact_store() -> None:
    """Drop the cached store so the next call re-reads configuration."""
    set_artifact_store(None)


def artifact_key(path: str | os.PathLike, *, store: ArtifactStore | None = None) -> str:
    """The store key for an artifact a renderer wrote to *path*."""
    store = store or get_artifact_store()
    return key_for_path(path, store.local_root())


def publish_artifact(path: str | os.PathLike, *, store: ArtifactStore | None = None) -> str:
    """Publish a just-rendered file and return the key it is addressable by.

    Every producer of a `/static/<key>` artifact calls this. Under the
    filesystem store the file is already at its final path and nothing is
    copied; under an object store it is uploaded. Either way the caller gets
    back the key that belongs in the URL and in the render cache.
    """
    store = store or get_artifact_store()
    key = key_for_path(path, store.local_root())
    store.put_file(key, path)
    return key


def publish_artifact_best_effort(path: str | os.PathLike, *, store: ArtifactStore | None = None) -> str:
    """Publish *path* if it is really there; otherwise just name it.

    For the producers that already trusted a converter's boolean and emitted a
    `/static/` URL without checking the file landed — the static-part
    conversion, git HEAD-diff renders, animation frames. Making those raise
    would turn a link that 404s (today's behaviour, on the rare path where a
    converter lies) into a 500 on the whole request, which is a regression, not
    a fix. The mismatch is logged rather than swallowed silently.

    The render worker deliberately does **not** use this: there, an artifact
    that failed to publish must fail the render.
    """
    store = store or get_artifact_store()
    key = key_for_path(path, store.local_root())
    if not os.path.isfile(path):
        logger.warning(
            "Artifact %s was reported produced but is not on disk; serving the "
            "key unpublished (it will 404 if it truly is not there)", path,
        )
        return key
    store.put_file(key, path)
    return key


@contextlib.contextmanager
def local_artifact(key: str, *, store: ArtifactStore | None = None) -> Iterator[Path | None]:
    """A real filesystem path for *key* while the block runs, or ``None``.

    Some consumers of a render artifact cannot take a byte stream: trimesh
    loads a file, the design verifier is a subprocess handed ``argv``, and a
    printer client uploads a path. They used to build that path by joining the
    static directory, which is exactly the assumption that breaks when the
    artifact is an object in a bucket.

    Under the filesystem store the artifact's own path is yielded and nothing
    is copied or removed — those call sites behave as they always did, down to
    the file they touch. Under any other store the object is downloaded to a
    temporary file for the duration of the block and deleted afterwards, so a
    long-lived API pod does not accumulate meshes.

    Yields ``None`` when the artifact is not stored, which every caller already
    has to handle: it is the same "no render yet" case as a missing file.
    """
    store = store or get_artifact_store()
    try:
        safe_key = normalize_key(key)
    except InvalidArtifactKey:
        yield None
        return

    existing = store.local_path(safe_key)
    if existing is not None:
        yield existing
        return

    if not store.exists(safe_key):
        yield None
        return

    suffix = Path(safe_key).suffix
    handle, staged = tempfile.mkstemp(prefix="artifact-", suffix=suffix)
    os.close(handle)
    try:
        try:
            store.fetch_to_path(safe_key, staged)
        except ArtifactNotFound:
            # Collected between the existence check and the read. Same answer
            # as a file that vanished under the old code: nothing to work with.
            fetched = False
        else:
            fetched = True
        yield Path(staged) if fetched else None
    finally:
        try:
            os.unlink(staged)
        except OSError:
            logger.debug("Could not remove staged artifact copy %s", staged, exc_info=True)


def check_artifact_store_ready(store: ArtifactStore | None = None) -> ArtifactStore:
    """Verify the store at startup, logging what took effect. Raises on failure.

    Called by the API's app factory and by the render worker's entry point, so
    a deployment pointed at a bucket it cannot reach dies at boot rather than
    accepting renders it will never be able to serve back.
    """
    store = store or get_artifact_store()
    store.check_ready()
    logger.info("Render artifact store ready: %s", store.describe())
    return store
