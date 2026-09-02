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
from pathlib import Path
from typing import BinaryIO

from services.storage.base import (
    ArtifactNotFound,
    ArtifactStore,
    ArtifactStoreError,
    InvalidArtifactKey,
    normalize_key,
)

logger = logging.getLogger(__name__)


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
    def open(self, key: str) -> BinaryIO:
        path = self.path_for(key)
        try:
            return path.open("rb")
        except (FileNotFoundError, IsADirectoryError) as exc:
            raise ArtifactNotFound(key) from exc

    def exists(self, key: str) -> bool:
        try:
            return self.path_for(key).is_file()
        except InvalidArtifactKey:
            return False

    def size(self, key: str) -> int | None:
        try:
            return self.path_for(key).stat().st_size
        except (InvalidArtifactKey, OSError):
            return None

    def delete(self, key: str) -> bool:
        try:
            self.path_for(key).unlink()
            return True
        except (InvalidArtifactKey, FileNotFoundError, IsADirectoryError):
            return False

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
