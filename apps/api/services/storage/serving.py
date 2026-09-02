"""Serving stored artifacts over HTTP.

Two helpers, one per call site the API already had: `/static/<filename>` in
``app.py`` and the render-artifact branch of the download route. Each has two
branches:

**Filesystem-backed store** — the default, and the production configuration.
The branch is literally the code it replaced: ``send_from_directory`` for
`/static`, ``safe_join_path`` plus ``send_file`` for the download. Nothing is
re-implemented, so ``ETag``, ``Last-Modified``, ``Content-Length``,
``Accept-Ranges``, conditional 304s, the zero-copy send and the 404 shape are
all byte-for-byte what they were before object storage existed. That is the
point: the flag defaults to ``fs``, and ``fs`` must be indistinguishable.

**Anything else** — the artifact is streamed out of the store in chunks. The
API stays in the request path, which is what keeps #78's private-project gate
on `/static` and the tier gate on the download route applying to object-storage
artifacts exactly as they apply to files on disk. A presigned or public bucket
URL would route around both, so none is ever produced.

Known difference on the streaming branch: no ``Range`` support and no
conditional revalidation, because the upstream object store is not asked for
either. Meshes are fetched whole by the viewer and by download clients, so this
costs nothing today; it is recorded in
`docs/operations/render-artifact-storage.md` rather than left to be discovered.
"""
from __future__ import annotations

import logging

from flask import Response, send_file, send_from_directory, stream_with_context

from services.storage import (
    ArtifactNotFound,
    ArtifactStore,
    InvalidArtifactKey,
    get_artifact_store,
    guess_content_type,
    normalize_key,
)

logger = logging.getLogger(__name__)

#: Chunk size for streamed artifacts. 64 KiB is the usual sweet spot between
#: syscall count and per-request memory with many concurrent downloads.
STREAM_CHUNK_BYTES = 64 * 1024


def _stream(store: ArtifactStore, key: str):
    """Yield the artifact's bytes, closing the underlying stream either way."""
    body = store.open(key)
    try:
        while True:
            chunk = body.read(STREAM_CHUNK_BYTES)
            if not chunk:
                return
            yield chunk
    finally:
        close = getattr(body, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                logger.debug("Failed to close artifact stream for %r", key, exc_info=True)


def _streamed_response(
    store: ArtifactStore,
    key: str,
    *,
    as_attachment: bool,
    download_name: str | None,
) -> Response | None:
    """Stream *key* out of a non-filesystem store, or ``None`` when it is absent."""
    size = store.size(key)
    if size is None and not store.exists(key):
        return None

    response = Response(
        stream_with_context(_stream(store, key)),
        mimetype=guess_content_type(key),
    )
    if size is not None:
        response.headers["Content-Length"] = str(size)
    if as_attachment:
        # Headers.set renders the RFC 6266 filename* form for non-ASCII names,
        # matching what send_file would have produced.
        response.headers.set(
            "Content-Disposition",
            "attachment",
            filename=download_name or key.rsplit("/", 1)[-1],
        )
    return response


def send_static_artifact(filename: str, *, store: ArtifactStore | None = None) -> Response | None:
    """Response for ``/static/<filename>``, or ``None`` when there is no such artifact.

    Returning ``None`` rather than aborting leaves the 404 to the caller, so the
    route keeps producing the app's own JSON error shape.
    """
    store = store or get_artifact_store()
    root = store.local_root()
    if root is not None:
        # Unchanged from before the store existed, including Werkzeug's own
        # safe-join and its NotFound for a missing or non-file path.
        return send_from_directory(str(root), filename)

    try:
        key = normalize_key(filename)
    except InvalidArtifactKey:
        return None
    try:
        return _streamed_response(store, key, as_attachment=False, download_name=None)
    except ArtifactNotFound:
        return None


def send_artifact_download(
    filename: str,
    expected_suffix: str,
    *,
    store: ArtifactStore | None = None,
) -> Response | None:
    """Attachment response for a render artifact, or ``None`` when it is not stored.

    *expected_suffix* is the extension the route already validated the request
    against (without the dot); it is re-checked here so a stored object cannot
    be served under a format the caller did not ask for.
    """
    store = store or get_artifact_store()
    root = store.local_root()

    if root is not None:
        from utils.route_helpers import safe_join_path

        safe_path = safe_join_path(str(root), filename)
        if safe_path and safe_path.exists() and safe_path.suffix.lower() == f".{expected_suffix}":
            return send_file(safe_path, as_attachment=True, download_name=filename)
        return None

    try:
        key = normalize_key(filename)
    except InvalidArtifactKey:
        return None
    if not key.lower().endswith(f".{expected_suffix}"):
        return None
    try:
        return _streamed_response(
            store, key, as_attachment=True, download_name=key.rsplit("/", 1)[-1]
        )
    except ArtifactNotFound:
        return None
