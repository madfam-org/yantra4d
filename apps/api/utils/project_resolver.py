"""
Centralized project directory resolution and validation.

Eliminates duplicate slug/project resolution logic scattered across route files.
"""
import functools
import logging
from pathlib import Path

from flask import jsonify

from config import Config

logger = logging.getLogger(__name__)


def resolve_project_dir(
    slug: str,
    *,
    require_git: bool = False,
    auto_git: bool = False,
) -> tuple[Path | None, str | None]:
    """Resolve and validate a project directory from its slug.

    Returns (project_dir, error_message). error_message is None on success.

    Args:
        slug: Project slug (already validated by @require_valid_slug).
        require_git: If True, return error when .git directory is missing.
        auto_git: If True, auto-initialize git when .git is missing.
    """
    project_dir = (Config.PROJECTS_DIR / slug).resolve()

    # Guard path traversal
    if not project_dir.is_relative_to(Config.PROJECTS_DIR.resolve()):
        return None, "Project not found"

    if not project_dir.is_dir():
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
                return jsonify({"status": "error", "error": err}), status
            return fn(*args, slug=slug, project_dir=project_dir, **kwargs)
        return wrapper
    return decorator
