"""
Centralized project directory resolution and validation.

Eliminates duplicate slug/project resolution logic scattered across route files.

Since RFC 0038 P2 a cartridge can live under more than one root: the public
commons is ONE git submodule mounted at ``Config.PROJECTS_DIR``
(madfam-org/solid-hyperobjects, each cartridge at ``<slug>/``), and the
client-private cartridges mount separately at ``Config.PRIVATE_PROJECTS_DIR``.
``project_roots()`` is the single ordered list every read path searches, and
``resolve_project_dir()`` is the single function that searches it -- so the
path-traversal guard is written once and applies to every root.

User-authored cartridges (forks, GitHub imports, onboarding, AI synthesis)
live in a third root, ``Config.USER_PROJECTS_DIR``. It is searched LAST, so a
user cartridge can never shadow a curated one, and it is the only root new
cartridges are written into: ``project_write_root()`` returns it. The commons
and private roots ship with the release and are treated as read-only content.

A new slug must be free in EVERY root (``slug_in_use()``), not just the one it
is written into, so a write can never create a cartridge that a curated root
would hide or that would hide a curated one.
"""
import functools
import logging
from pathlib import Path

from config import Config
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)


def _unique_roots(*roots) -> list[Path]:
    """``roots`` as ``Path`` objects, in order, without repeats or ``None``."""
    seen: list[Path] = []
    for root in roots:
        if root is None:
            continue
        path = Path(root)
        if path not in seen:
            seen.append(path)
    return seen


def curated_project_roots() -> list[Path]:
    """The release-shipped roots: public commons first, then private.

    These hold curated content. They are never written by a route that creates
    a cartridge, and they are the only roots trusted on interpreter and include
    search paths (see ``services.engine.cadquery_engine``).
    """
    return _unique_roots(
        Config.PROJECTS_DIR, getattr(Config, "PRIVATE_PROJECTS_DIR", None),
    )


def project_roots() -> list[Path]:
    """Cartridge roots in resolution order: commons, private, then user.

    A root that does not exist on disk is still returned -- callers test for
    the cartridge, not the root, and a public clone simply has no
    ``private-projects/``. A root configured to the same path as an earlier
    one is skipped, so a single-root deployment (or a test that monkeypatches
    only ``PROJECTS_DIR``) does not search the same directory twice.
    """
    return _unique_roots(
        *curated_project_roots(), getattr(Config, "USER_PROJECTS_DIR", None),
    )


def project_write_root() -> Path:
    """The root new cartridges are written into: the user-projects root.

    Never the commons or the private root. Coerced to ``Path`` because tests
    monkeypatch Config paths with plain strings and callers do ``root / slug``.
    The directory may not exist yet; writers create it with their first
    cartridge (``mkdir(parents=True)`` / ``copytree`` / ``git clone``).
    """
    return Path(getattr(Config, "USER_PROJECTS_DIR", None) or Config.PROJECTS_DIR)


def _candidate(root: Path, slug: str) -> Path | None:
    """``<root>/<slug>`` resolved, or None when the slug escapes ``root``."""
    try:
        root_resolved = Path(root).resolve()
    except OSError:  # pragma: no cover - unreadable root
        return None
    candidate = (root_resolved / slug).resolve()
    if not candidate.is_relative_to(root_resolved):
        return None
    return candidate


def find_project_dir(slug: str) -> Path | None:
    """First existing ``<root>/<slug>`` across ``project_roots()``, or None.

    Applies the path-traversal guard per root: a slug that escapes its root
    (``../secret``) resolves outside it and is rejected there, so it can never
    be answered by any root.
    """
    for root in project_roots():
        candidate = _candidate(root, slug)
        if candidate is not None and candidate.is_dir():
            return candidate
    return None


def slug_in_use(slug: str) -> Path | None:
    """The existing directory that already claims ``slug`` in ANY root, or None.

    Wider than ``find_project_dir``: it also covers the extra manifest roots in
    ``Config.CARTRIDGES_DIRS`` (bundled npm cartridges, ``CARTRIDGES_DIRS``
    from the environment), which the manifest service searches BEFORE the user
    root. Every writer that creates a new slug checks this first, so a new
    cartridge can neither shadow nor be shadowed by an existing one.
    """
    roots = _unique_roots(*project_roots(), *getattr(Config, "CARTRIDGES_DIRS", []))
    for root in roots:
        candidate = _candidate(root, slug)
        if candidate is not None and candidate.is_dir():
            return candidate
    return None


def shadowed_user_slugs() -> list[str]:
    """User-root slugs hidden by a cartridge of the same slug in an earlier root.

    ``slug_in_use`` keeps writes from creating such a pair, but a release can
    still add a commons cartridge whose slug a user already took. Resolution
    then answers with the commons one and the user cartridge is unreachable
    (still on disk, never deleted). The app logs these at startup so an
    operator can rename the user cartridge.
    """
    user_root = Path(getattr(Config, "USER_PROJECTS_DIR", None) or Config.PROJECTS_DIR)
    earlier = [
        root for root in _unique_roots(*getattr(Config, "CARTRIDGES_DIRS", []), *curated_project_roots())
        if root != user_root
    ]
    if user_root in curated_project_roots() or not user_root.is_dir():
        return []
    shadowed = []
    for child in sorted(user_root.iterdir()):
        if not child.is_dir():
            continue
        if any((Path(root) / child.name).is_dir() for root in earlier):
            shadowed.append(child.name)
    return shadowed


def resolve_project_dir(
    slug: str,
    *,
    require_git: bool = False,
    auto_git: bool = False,
) -> tuple[Path | None, str | None]:
    """Resolve and validate a project directory from its slug.

    Returns (project_dir, error_message). error_message is None on success.

    Searches every root in ``project_roots()`` in order, so a client-private
    cartridge mounted at ``PRIVATE_PROJECTS_DIR`` resolves exactly like a
    public one. Access control is unchanged and remains slug-based
    (``PROJECT_ACCESS_GRANTS`` / ``access_control.view``, see docs/AUTH.md) --
    which root a cartridge came from grants nothing.

    Args:
        slug: Project slug (already validated by @require_valid_slug).
        require_git: If True, return error when .git directory is missing.
        auto_git: If True, auto-initialize git when .git is missing.
    """
    project_dir = find_project_dir(slug)

    if project_dir is None:
        return None, "Project not found"

    if require_git and not (project_dir / ".git").is_dir():
        return None, "Project does not have a git repository"

    if auto_git and not (project_dir / ".git").is_dir():
        # Version control is a convenience, never a precondition: if git is
        # missing or init fails, the caller (a save) still proceeds.
        from services.editor.git_operations import git_init
        try:
            result = git_init(project_dir)
        except Exception:  # a save must not fail because of git
            logger.warning("git init failed for %s; continuing without version control",
                           project_dir.name, exc_info=True)
        else:
            if isinstance(result, dict) and not result.get("success"):
                logger.warning("git init failed for %s (%s); continuing without version control",
                               project_dir.name, result.get("error"))

    return project_dir, None


def require_project(*, require_git: bool = False, auto_git: bool = False):
    """Route decorator that resolves and injects ``project_dir`` into kwargs.

    Combines slug validation, path-traversal guard, existence check, and
    optional git verification into a single decorator.  The resolved
    ``project_dir`` (a ``Path``) is passed as a keyword argument to the
    wrapped view function.

    Usage::

        @route("/api/projects/<slug>/files", methods=["GET"])
        @require_valid_slug
        @require_project(auto_git=True)
        def list_files(slug, project_dir):
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, slug: str, **kwargs):
            project_dir, err = resolve_project_dir(
                slug, require_git=require_git, auto_git=auto_git,
            )
            if err:
                status = 404 if "not found" in err.lower() else 400
                return error_response(err, status)
            return fn(*args, slug=slug, project_dir=project_dir, **kwargs)
        return wrapper
    return decorator
