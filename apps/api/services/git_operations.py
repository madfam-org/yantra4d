"""
Git CLI wrappers for status, diff, commit, push, pull operations.

All commands use subprocess.run with list args (no shell=True) and 60s timeout.
Token injection for push/pull is transient — remote URL is restored after operation.
"""
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

GIT_TIMEOUT = 60


def _run_git(project_dir: Path, args: list[str], timeout: int = GIT_TIMEOUT) -> subprocess.CompletedProcess:
    """Run a git command in the project directory."""
    return subprocess.run(
        ["git"] + args,
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _get_remote_url(project_dir: Path) -> str | None:
    """Get the current origin remote URL."""
    result = _run_git(project_dir, ["remote", "get-url", "origin"], timeout=10)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def _inject_token_url(url: str, token: str) -> str:
    """Inject GitHub token into remote URL for authenticated operations."""
    if url.startswith("https://"):
        return url.replace("https://", f"https://x-access-token:{token}@", 1)
    return url


def git_init(project_dir: Path) -> dict:
    """Initialize a git repo if .git doesn't exist. git init + add all + initial commit."""
    if (project_dir / ".git").is_dir():
        return {"success": True, "already_initialized": True}

    result = _run_git(project_dir, ["init"])
    if result.returncode != 0:
        return {"success": False, "error": f"git init failed: {result.stderr.strip()}"}

    # Configure local user identity (CI runners may lack global config)
    _run_git(project_dir, ["config", "user.name", "Qubic"], timeout=10)
    _run_git(project_dir, ["config", "user.email", "noreply@qubic.quest"], timeout=10)

    _run_git(project_dir, ["add", "."])
    result = _run_git(project_dir, ["commit", "-m", "Initial commit"])
    if result.returncode != 0:
        return {"success": False, "error": f"Initial commit failed: {result.stderr.strip()}"}

    return {"success": True, "already_initialized": False}


def git_status(project_dir: Path) -> dict:
    """Get working tree status as parsed lists of modified/added/deleted files."""
    result = _run_git(project_dir, ["status", "--porcelain"])
    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}

    modified, added, deleted, untracked = [], [], [], []
    for line in result.stdout.strip().splitlines():
        if not line or len(line) < 2:
            continue
        # Porcelain v1: XY PATH — but some git versions omit trailing space in XY
        # when Y is blank, giving "X PATH" instead of "X  PATH". Use lstrip to be safe.
        status = line[:2].strip()
        filepath = line[2:].lstrip()  # strip separator space(s) between XY and path
        if not filepath:
            continue
        if status in ("M", "MM"):
            modified.append(filepath)
        elif status in ("A", "AM"):
            added.append(filepath)
        elif status in ("D",):
            deleted.append(filepath)
        elif status == "??":
            untracked.append(filepath)

    # Check if ahead/behind remote
    branch_result = _run_git(project_dir, ["status", "--branch", "--porcelain=v2"], timeout=10)
    ahead, behind = 0, 0
    for line in branch_result.stdout.splitlines():
        if line.startswith("# branch.ab"):
            parts = line.split()
            for part in parts:
                if part.startswith("+"):
                    try:
                        ahead = int(part[1:])
                    except ValueError:
                        pass
                elif part.startswith("-"):
                    try:
                        behind = abs(int(part[1:]))
                    except ValueError:
                        pass

    # Current branch
    branch = None
    br_result = _run_git(project_dir, ["branch", "--show-current"], timeout=10)
    if br_result.returncode == 0:
        branch = br_result.stdout.strip()

    # Check for remote
    remote = _get_remote_url(project_dir)

    return {
        "success": True,
        "branch": branch,
        "modified": modified,
        "added": added,
        "deleted": deleted,
        "untracked": untracked,
        "ahead": ahead,
        "behind": behind,
        "clean": not (modified or added or deleted or untracked),
        "remote": remote,
    }


def git_diff(project_dir: Path, filepath: str | None = None) -> dict:
    """Get unified diff output."""
    args = ["diff"]
    if filepath:
        args.append(filepath)
    result = _run_git(project_dir, args)
    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}
    return {"success": True, "diff": result.stdout}


def git_commit(
    project_dir: Path,
    message: str,
    files: list[str],
    author_name: str | None = None,
    author_email: str | None = None,
) -> dict:
    """Stage specified files and commit."""
    if not files:
        return {"success": False, "error": "No files specified"}
    if not message:
        return {"success": False, "error": "Commit message is required"}

    # Stage files
    add_result = _run_git(project_dir, ["add"] + files)
    if add_result.returncode != 0:
        return {"success": False, "error": f"git add failed: {add_result.stderr.strip()}"}

    # Build commit command
    commit_args = ["commit", "-m", message]
    if author_name and author_email:
        commit_args += ["--author", f"{author_name} <{author_email}>"]

    result = _run_git(project_dir, commit_args)
    if result.returncode != 0:
        return {"success": False, "error": f"git commit failed: {result.stderr.strip()}"}

    # Get the new commit hash
    hash_result = _run_git(project_dir, ["rev-parse", "HEAD"], timeout=10)
    commit_hash = hash_result.stdout.strip() if hash_result.returncode == 0 else None

    return {"success": True, "commit": commit_hash, "message": message}


def git_push(project_dir: Path, github_token: str) -> dict:
    """Push to origin with transient token injection."""
    original_url = _get_remote_url(project_dir)
    if not original_url:
        return {"success": False, "error": "No origin remote configured"}

    authed_url = _inject_token_url(original_url, github_token)
    try:
        # Temporarily set authenticated URL
        _run_git(project_dir, ["remote", "set-url", "origin", authed_url], timeout=10)

        result = _run_git(project_dir, ["push", "origin", "HEAD"])
        if result.returncode != 0:
            return {"success": False, "error": f"git push failed: {result.stderr.strip()}"}
        return {"success": True}
    finally:
        # Always restore clean URL
        _run_git(project_dir, ["remote", "set-url", "origin", original_url], timeout=10)


def git_pull(project_dir: Path, github_token: str) -> dict:
    """Pull from origin with transient token injection."""
    original_url = _get_remote_url(project_dir)
    if not original_url:
        return {"success": False, "error": "No origin remote configured"}

    authed_url = _inject_token_url(original_url, github_token)
    try:
        _run_git(project_dir, ["remote", "set-url", "origin", authed_url], timeout=10)

        result = _run_git(project_dir, ["pull", "--ff-only", "origin"])
        if result.returncode != 0:
            return {"success": False, "error": f"git pull failed: {result.stderr.strip()}"}
        return {"success": True}
    finally:
        _run_git(project_dir, ["remote", "set-url", "origin", original_url], timeout=10)
