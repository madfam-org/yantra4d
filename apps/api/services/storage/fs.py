"""Filesystem artifact store — today's directory, and the default.

This backend exists to change nothing. It is the production configuration
until an operator flips ``RENDER_ARTIFACT_STORE=s3``, so every observable
detail has to survive the abstraction: the same files at the same paths, the
same URLs, and the same response headers (the read path keeps using
``send_from_directory``/``send_file`` via :meth:`local_root`).

The one subtlety is :meth:`put_file`. Renders already write straight into the
static directory, so "publishing" such a file must be a **no-op** rather than a
copy: copying would double the bytes on a volume with a hard ``sizeLimit``,
reset the mtime the GC sorts on, and change the inode under an in-flight
download. Sameness is decided with ``os.path.samefile``, not string equality,
so a symlinked or differently-spelled path to the same file is still recognised.
"""
from __future__ import annotations

import logging
import os
import shutil
import stat as stat_module
from pathlib import Path
from typing import BinaryIO

from services.storage.base import (
    ArtifactInfo,
    ArtifactNotFound,
    ArtifactStore,
    ArtifactStoreError,
    InvalidArtifactKey,
    normalize_key,
)

logger = logging.getLogger(__name__)


def _log_walk_error(exc: OSError) -> None:
    """os.walk swallows errors by default; this store would rather say so."""
    logger.warning("Artifact listing could not read %s: %s", getattr(exc, "filename", "?"), exc)


class _BoundedReader:
    """A file handle that stops after *limit* bytes.

    Used for a ``Range`` request: the underlying file is already seeked to the
    start, and the response must not run past the end of the requested range.
    """

    def __init__(self, handle: BinaryIO, limit: int):
        self._handle = handle
        self._remaining = limit

    def read(self, size: int = -1) -> bytes:
        if self._remaining <= 0:
            return b""
        want = self._remaining if size is None or size < 0 else min(size, self._remaining)
        chunk = self._handle.read(want)
        self._remaining -= len(chunk)
        return chunk

    def close(self) -> None:
        self._handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
        return False


class FilesystemArtifactStore(ArtifactStore):
    """Artifacts as files under a directory.

    *root* may be ``None``, in which case ``Config.STATIC_DIR`` is read on
    every call. That is not laziness for its own sake: the static directory is
    monkeypatched per-test and is settled at runtime from the environment, and
    reading it at call time is precisely what the code being replaced did.
    """

    kind = "fs"

    def __init__(self, root: str | os.PathLike | None = None):
        self._root = Path(root) if root is not None else None

    # ── location ───────────────────────────────────────────────────────
    @property
    def root(self) -> Path:
        if self._root is not None:
            return self._root
        from config import Config
        return Path(Config.STATIC_DIR)

    def local_root(self) -> Path:
        return self.root

    def path_for(self, key: str) -> Path:
        """Absolute path for *key*, guaranteed to stay inside :attr:`root`.

        ``normalize_key`` has already rejected traversal, but the resolved path
        is re-checked against the resolved root: a symlink inside the directory
        could otherwise point anywhere.
        """
        safe_key = normalize_key(key)
        root = self.root
        candidate = Path(os.path.join(str(root), safe_key))
        try:
            resolved = candidate.resolve()
            resolved_root = Path(root).resolve()
        except OSError as exc:
            raise InvalidArtifactKey(f"Cannot resolve artifact key {key!r}: {exc}") from exc
        if not resolved.is_relative_to(resolved_root):
            raise InvalidArtifactKey(f"Artifact key escapes the store root: {key!r}")
        return candidate

    # ── writing ────────────────────────────────────────────────────────
    def put_file(self, key: str, source_path: str | os.PathLike) -> str:
        safe_key = normalize_key(key)
        destination = self.path_for(safe_key)
        source = Path(source_path)

        if not source.is_file():
            raise ArtifactNotFound(f"No file to publish at {source_path!r}")

        # Already the artifact: publishing it must not touch the bytes.
        if destination.exists() and os.path.samefile(source, destination):
            return safe_key

        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        return safe_key

    def put_bytes(self, key: str, data: bytes) -> str:
        safe_key = normalize_key(key)
        destination = self.path_for(safe_key)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return safe_key

    # ── reading ────────────────────────────────────────────────────────
    def open(self, key: str, *, start: int | None = None, end: int | None = None) -> BinaryIO:
        path = self.path_for(key)
        try:
            handle = path.open("rb")
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise ArtifactNotFound(key) from exc
        if start is None and end is None:
            return handle
        try:
            handle.seek(start or 0)
        except OSError:
            handle.close()
            raise
        if end is None:
            return handle
        return _BoundedReader(handle, max(0, end - (start or 0)))

    def stat(self, key: str) -> ArtifactInfo | None:
        try:
            path = self.path_for(key)
            st = path.stat()
        except (InvalidArtifactKey, OSError):
            return None
        if not stat_module.S_ISREG(st.st_mode):
            return None
        return ArtifactInfo(
            key=normalize_key(key),
            size=st.st_size,
            modified_at=st.st_mtime,
            # No ETag: the read path derives one from size and mtime, which is
            # what Werkzeug already does for a file it sends.
            etag=None,
        )

    def list(self, prefix: str = "") -> list[ArtifactInfo]:
        """Every regular file under the root, as keys relative to it.

        Walks, rather than listing one level, because a key may legally contain
        ``/`` and the object backend has no way to hide a nested object from
        its own listing. Symlinked directories are not followed — the root is a
        volume the render engines write into, and a link out of it is not part
        of the store (``path_for`` refuses to resolve through one anyway).
        """
        root = self.root
        found: list[ArtifactInfo] = []
        try:
            walker = os.walk(root, followlinks=False, onerror=_log_walk_error)
            for dirpath, _dirnames, filenames in walker:
                for name in filenames:
                    full = Path(dirpath) / name
                    try:
                        relative = full.relative_to(root).as_posix()
                    except ValueError:
                        continue
                    if not relative.startswith(prefix):
                        continue
                    try:
                        st = full.lstat()
                    except OSError:
                        continue
                    if not stat_module.S_ISREG(st.st_mode):
                        continue
                    found.append(
                        ArtifactInfo(
                            key=relative, size=st.st_size, modified_at=st.st_mtime
                        )
                    )
        except OSError as exc:
            logger.error("Artifact listing failed under %s: %s", root, exc)
        found.sort(key=lambda info: info.key)
        return found

    def delete(self, key: str) -> bool:
        try:
            self.path_for(key).unlink()
            return True
        except (InvalidArtifactKey, FileNotFoundError, IsADirectoryError):
            return False

    # ── materialising ──────────────────────────────────────────────────
    def local_path(self, key: str) -> Path | None:
        """The artifact's real path. There is nothing to copy for this backend."""
        try:
            path = self.path_for(key)
        except InvalidArtifactKey:
            return None
        return path if path.is_file() else None

    # ── lifecycle ──────────────────────────────────────────────────────
    def check_ready(self) -> None:
        root = self.root
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ArtifactStoreError(f"Artifact directory {root} is not creatable: {exc}") from exc
        if not os.access(root, os.R_OK | os.W_OK):
            raise ArtifactStoreError(f"Artifact directory {root} is not readable and writable")

    def describe(self) -> dict:
        return {"kind": self.kind, "root": str(self.root)}

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"FilesystemArtifactStore(root={self.root!s})"
