"""Serving stored artifacts over HTTP.

Two helpers, one per call site the API already had: `/static/<filename>` in
``app.py`` and the render-artifact branch of the download route. Each has two
branches:

**Filesystem-backed store** — the default, and the production configuration.
The branch is literally the code it replaced: ``send_from_directory`` for
`/static`, ``safe_join_path`` plus ``send_file`` for the download. Nothing is
re-implemented, so ``ETag``, ``Last-Modified``, ``Content-Length``,
``Accept-Ranges``, conditional 304s, ranged 206s, the zero-copy send and the
404 shape are all byte-for-byte what they were before object storage existed.
That is the point: the flag defaults to ``fs``, and ``fs`` must be
indistinguishable.

**Anything else** — the artifact is streamed out of the store in chunks. The
API stays in the request path, which is what keeps #78's private-project gate
on `/static` and the tier gate on the download route applying to object-storage
artifacts exactly as they apply to files on disk. A presigned or public bucket
URL would route around both, so none is ever produced.

The streaming branch answers the same conditional and range requests the
filesystem branch does, because a viewer, a `curl -C -` and a CDN in front of
the API do not know which backend is behind it:

``ETag`` / ``Last-Modified``
    From ``ArtifactStore.stat``. S3 supplies a real ETag on every HEAD; a
    backend that cannot is given one derived from size and mtime, which is the
    same information Werkzeug derives a file's ETag from.

``If-None-Match`` / ``If-Modified-Since`` → 304
    Checked before anything is read, so a revalidation costs one HEAD and no
    object body at all.

``Range`` → 206 / 416
    Parsed here and pushed down into the store, so a range read fetches *that
    range* from the bucket rather than dragging the whole object through the
    API pod to slice it. ``If-Range`` is honoured: a stale validator falls back
    to the full 200, as RFC 9110 requires.

Cache-Control is deliberately **not** set here. `/static` responses come out
``no-cache`` on both backends — the filesystem branch from Werkzeug's
``send_file`` default, the streaming branch from the same value set explicitly
— and #78's gate replaces that with ``private, no-store`` for a private
project's artifact, on either backend. Nothing in this module can make an
artifact shared-cacheable.
"""
from __future__ import annotations

import datetime as dt
import logging

from flask import Response, request, send_file, send_from_directory, stream_with_context
from werkzeug.http import (
    http_date,
    is_resource_modified,
    parse_if_range_header,
    parse_range_header,
)

from services.storage import (
    ArtifactInfo,
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

#: What Werkzeug's ``send_file`` sends when no max-age is configured, which is
#: how `/static` has always been served. Repeated here so the streaming branch
#: is not accidentally more cacheable than the branch it stands in for.
DEFAULT_CACHE_CONTROL = "no-cache"


def _stream(store: ArtifactStore, key: str, start: int | None, end: int | None):
    """Yield the artifact's bytes, closing the underlying stream either way."""
    body = store.open(key, start=start, end=end)
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


def artifact_etag(info: ArtifactInfo) -> str:
    """A validator for this artifact.

    The backend's own when it has one — S3's ETag is the object's MD5, so it
    changes when and only when the bytes do. Otherwise size and mtime, which is
    what Werkzeug builds a file's ETag from and is exactly as strong.

    Rendered artifacts carry the parameter hash in their *name*, so two renders
    that differ are two different keys; the validator is what catches the case
    a name is reused, which is what the `head_` git-diff renders do.
    """
    if info.etag:
        return info.etag
    return f"{int(info.modified_at)}-{info.size}"


def _set_disposition(response: Response, as_attachment: bool, name: str) -> None:
    """The ``Content-Disposition`` Werkzeug's ``send_file`` would have sent.

    ``inline`` with the file name for an ordinary read, ``attachment`` for a
    download — ``send_file`` sets one either way, and `Headers.set` renders the
    RFC 6266 ``filename*`` form for a non-ASCII name exactly as it does.
    """
    response.headers.set(
        "Content-Disposition",
        "attachment" if as_attachment else "inline",
        filename=name,
    )


def _not_modified(etag: str, info: ArtifactInfo, as_attachment: bool, name: str) -> Response:
    """A 304 carrying the validators and nothing else.

    No body and no entity headers: a 304 that advertised a Content-Length it
    was not sending would hang a client waiting for bytes. ``Content-Type`` and
    ``Content-Length`` go, ``Content-Disposition`` stays — which is what
    Werkzeug's ``make_conditional`` does to a 304 off ``send_file``.
    """
    response = Response(status=304)
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Last-Modified"] = http_date(info.modified_at)
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    _set_disposition(response, as_attachment, name)
    return response


def _unsatisfiable_range(info: ArtifactInfo) -> Response:
    """416, naming the length the client should have asked within."""
    response = Response(status=416)
    response.headers["Content-Range"] = f"bytes */{info.size}"
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    return response


def _modified_at(info: ArtifactInfo) -> dt.datetime:
    """The artifact's mtime as the aware, second-resolution datetime HTTP uses.

    Werkzeug's conditional helpers want a datetime, and HTTP dates have no
    sub-second component — so the comparison has to happen at the resolution
    the header is written at, or a client would revalidate forever.
    """
    return dt.datetime.fromtimestamp(info.modified_at, dt.UTC).replace(microsecond=0)


def _if_range_matches(etag: str, info: ArtifactInfo) -> bool:
    """Whether a conditional range may be served.

    Absent ``If-Range`` means "just serve the range". Present, it is either the
    validator the client already holds or a date; either way a mismatch means
    the artifact changed under them and the whole thing has to be re-sent as a
    200, which is what RFC 9110 asks for.
    """
    if_range = parse_if_range_header(request.headers.get("If-Range"))
    if if_range is None:
        return True
    if if_range.etag is not None:
        return if_range.etag.strip('"') == etag
    if if_range.date is not None:
        return _modified_at(info) <= if_range.date
    return True


def _streamed_response(
    store: ArtifactStore,
    key: str,
    *,
    as_attachment: bool,
    download_name: str | None,
) -> Response | None:
    """Stream *key* out of a non-filesystem store, or ``None`` when it is absent."""
    info = store.stat(key)
    if info is None:
        return None

    etag = artifact_etag(info)
    name = download_name or key.rsplit("/", 1)[-1]

    # Revalidation first: a 304 must cost a HEAD and no object body.
    if not is_resource_modified(
        request.environ, etag=f'"{etag}"', last_modified=_modified_at(info)
    ):
        return _not_modified(etag, info, as_attachment, name)

    start: int | None = None
    end: int | None = None
    status = 200
    content_range = None

    range_header = request.headers.get("Range")
    if range_header and _if_range_matches(etag, info):
        parsed = parse_range_header(range_header)
        if parsed is None or parsed.units != "bytes":
            # Unparseable or a unit we do not speak: RFC 9110 says ignore it.
            pass
        else:
            span = parsed.range_for_length(info.size)
            if span is None:
                return _unsatisfiable_range(info)
            start, end = span
            status = 206
            content_range = parsed.to_content_range_header(info.size)

    response = Response(
        stream_with_context(_stream(store, key, start, end)),
        status=status,
        # The name decides the type, not what the object was stored with:
        # `fs` serves whatever Werkzeug would guess from the file name, and
        # the two branches must label the same mesh the same way.
        mimetype=guess_content_type(key),
    )
    length = info.size if start is None else (end - start)
    response.headers["Content-Length"] = str(length)
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Last-Modified"] = http_date(info.modified_at)
    response.headers["Cache-Control"] = DEFAULT_CACHE_CONTROL
    if content_range:
        response.headers["Content-Range"] = content_range
        # Werkzeug advertises range support on the ranged response and nowhere
        # else — a plain 200 off `send_file` carries no `Accept-Ranges` — and
        # the two backends have to agree header for header.
        response.headers["Accept-Ranges"] = "bytes"
    _set_disposition(response, as_attachment, name)
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
