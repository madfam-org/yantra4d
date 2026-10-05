"""
Who created a user cartridge — recorded once, at creation, outside the cartridge.

A fork (``POST /api/projects/<slug>/fork``) or a GitHub import
(``POST /api/github/import``) is written for one account. The token's ``sub``
of that account is recorded here so the write guard
(``routes.editor.editor.require_writable_cartridge``) can let only that account
— or an admin — change the cartridge afterwards.

Where the record lives, and why there
-------------------------------------

``<write root>/.owners/<slug>.json`` — a sidecar next to the cartridges, never
inside one:

* **Not in git.** ``auto_git`` and ``git/commit`` operate on the cartridge
  directory's own repository (``git add .`` at ``<root>/<slug>``), and
  ``git/push`` pushes that repository. A file outside the directory is outside
  every one of those, by construction rather than by an ignore rule a later
  change could drop.
* **Not in any download or export.** Every serving route resolves paths inside
  ``<root>/<slug>`` (``safe_join_path`` / ``is_relative_to`` guards), so the
  sidecar is unreachable through them; ``project.meta.json`` by contrast is
  returned verbatim by ``GET /meta`` and travels with a pushed repository.
* **Never a cartridge.** ``.owners`` can never be a slug (a slug starts with a
  lowercase letter or digit) and has no ``project.json``, so discovery and
  resolution skip it.
* **Persistent.** It sits in the same write root as the cartridges it
  describes, so it lives on the same volume and survives the same restarts.

The record holds the ``sub`` and a timestamp — no email, name or other profile
data. The Studio never receives another account's ``sub``: the API answers
only ``can_write`` / ``is_owner`` for the caller.
"""
import datetime
import json
import logging
import os
import tempfile
from pathlib import Path

from utils.project_resolver import project_write_root
from utils.validators import validate_project_slug

logger = logging.getLogger(__name__)

#: Directory under the write root holding one ``<slug>.json`` per cartridge.
OWNERS_DIRNAME = ".owners"


def owners_dir() -> Path:
    return project_write_root() / OWNERS_DIRNAME


def _record_path(slug: str) -> Path | None:
    if not isinstance(slug, str) or validate_project_slug(slug) is not None:
        return None
    return owners_dir() / f"{slug}.json"


def claims_sub(claims: dict | None) -> str | None:
    """The token's ``sub``, or None when there is no usable identity."""
    if not isinstance(claims, dict):
        return None
    sub = claims.get("sub")
    if not isinstance(sub, str):
        return None
    sub = sub.strip()
    return sub or None


def record_owner(slug: str, claims: dict | None) -> bool:
    """Record the creating account for a new cartridge. Overwrites any old record.

    Returns False — and writes nothing — when the request carries no identity
    (auth disabled): such a cartridge is ownerless, and the write guard treats an
    ownerless cartridge as writable only by an admin (or in local dev mode).
    Raises OSError when the record cannot be written; the caller must then undo
    the creation, so a cartridge never exists with a record it was meant to have
    missing.
    """
    path = _record_path(slug)
    if path is None:
        raise ValueError(f"invalid slug {slug!r}")
    sub = claims_sub(claims)
    if sub is None:
        # A stale record from an earlier cartridge of the same slug must not
        # hand the new one to someone else.
        forget_owner(slug)
        return False

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    record = {
        "sub": sub,
        "recorded_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
            handle.write("\n")
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
    return True


def forget_owner(slug: str) -> None:
    """Remove a cartridge's owner record, if any (used to undo a failed creation)."""
    path = _record_path(slug)
    if path is None:
        return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def owner_sub(slug: str, project_dir: Path) -> str | None:
    """Recorded owner of the cartridge at ``project_dir``, or None.

    Only a cartridge that lives directly in the write root can have an owner:
    the record is keyed by slug, and a same-named directory in another root is a
    different cartridge. An unreadable or malformed record reads as no owner,
    which the guard treats as fail-closed.
    """
    path = _record_path(slug)
    if path is None:
        return None
    try:
        if Path(project_dir).resolve().parent != project_write_root().resolve():
            return None
    except OSError:
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        logger.warning("cartridge owner record for %s is unreadable: %s", slug, exc)
        return None
    sub = record.get("sub") if isinstance(record, dict) else None
    return sub if isinstance(sub, str) and sub else None
