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

Writes (onboarding a new cartridge, forking to a new slug) are NOT resolution:
they always target ``Config.PROJECTS_DIR`` via ``project_write_root()``.
"""
import functools
import logging
from pathlib import Path

from config import Config
from utils.route_helpers import error_response

logger = logging.getLogger(__name__)


def project_roots() -> list[Path]:
    """Cartridge roots in resolution order: public commons first, then private.

    A root that does not exist on disk is still returned -- callers test for
    the cartridge, not the root, and a public clone simply has no
    ``private-projects/``. ``PRIVATE_PROJECTS_DIR`` is skipped when it is
    configured to the same path as ``PROJECTS_DIR`` so a single-root
    deployment (or a test that monkeypatches only ``PROJECTS_DIR``) does not
    search the same directory twice.
    """
    roots = [Path(Config.PROJECTS_DIR)]
    private = getattr(Config, "PRIVATE_PROJECTS_DIR", None)
    if private is not None and Path(private) != Path(Config.PROJECTS_DIR):
        roots.append(Path(private))
    return roots


def project_write_root() -> Path:
    """The root new cartridges are written into. Always the public commons.

    Coerced to ``Path``: ``Config.PROJECTS_DIR`` is a ``Path`` in production but
    tests monkeypatch it with a plain string, and callers do ``root / slug``.
    """
    return Path(Config.PROJECTS_DIR)


def find_project_dir(slug: str) -> Path | None:
    """First existing ``<root>/<slug>`` across ``project_roots()``, or None.

    Applies the path-traversal guard per root: a slug that escapes its root
    (``../secret``) resolves outside it and is rejected there, so it can never
    be answered by any root.
    """
    for root in project_roots():
        try:
            root_resolved = Path(root).resolve()
        except OSError:  # pragma: no cover - unreadable root
            continue
        candidate = (root_resolved / slug).resolve()
        if not candidate.is_relative_to(root_resolved):
            continue
        if candidate.is_dir():
            return candidate
    return None


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
        from services.editor.git_operations import git_init
        git_init(project_dir)

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
