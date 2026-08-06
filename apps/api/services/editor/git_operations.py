"""
Git CLI wrappers for status, diff, commit, push, pull operations.

All commands use subprocess.run with list args (no shell=True) and 60s timeout.
Token injection uses GIT_ASKPASS — credentials never touch .git/config.
"""
import logging
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

GIT_TIMEOUT = 60


def _sanitize_git_output(text: str) -> str:
    """Strip embedded credentials from git output before logging."""
    return re.sub(r"https://[^@]+@", "https://***@", text)


def _run_git(project_dir: Path, args: list[str], timeout: int = GIT_TIMEOUT, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run a git command in the project directory."""
    try:
        return subprocess.run(
            ["git"] + args,
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Git command timed out after %ds: %s", timeout, " ".join(args[:2]))
        raise


def _make_askpass_env(github_token: str) -> dict:
    """Create an env dict with a GIT_ASKPASS helper that echoes the token.

    Uses a temporary script file that is automatically cleaned up by the OS.
    The token never touches .git/config — it only lives in a short-lived
    temp file that is read once by git and then deleted.
    """
    env = os.environ.copy()
    # Create a tiny shell script that echoes the token
    fd, script_path = tempfile.mkstemp(prefix="git_askpass_", suffix=".sh")
    try:
        os.write(fd, f"#!/bin/sh\necho 'x-access-token:{github_token}'\n".encode())
        os.close(fd)
        os.chmod(script_path, stat.S_IRWXU)  # 0o700 — owner-only executable
    except Exception:
        os.close(fd)
        raise

    env["GIT_ASKPASS"] = script_path
    # Prevent git from trying interactive prompts
    env["GIT_TERMINAL_PROMPT"] = "0"
    # Store path for cleanup
    env["_ASKPASS_TMPFILE"] = script_path
    return env


def _cleanup_askpass(env: dict | None) -> None:
    """Remove the temporary GIT_ASKPASS script if one was created."""
    if env and "_ASKPASS_TMPFILE" in env:
        try:
            os.unlink(env["_ASKPASS_TMPFILE"])
        except OSError:
            pass


def _get_remote_url(project_dir: Path) -> str | None:
    """Get the current origin remote URL."""
    result = _run_git(project_dir, ["remote", "get-url", "origin"], timeout=10)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


def git_init(project_dir: Path) -> dict:
    """Initialize a git repo if .git doesn't exist. git init + add all + initial commit."""
    if (project_dir / ".git").is_dir():
        return {"success": True, "already_initialized": True}

    result = _run_git(project_dir, ["init"])
    if result.returncode != 0:
        return {"success": False, "error": f"git init failed: {result.stderr.strip()}"}

    # Configure local user identity (CI runners may lack global config)
    _run_git(project_dir, ["config", "user.name", "Yantra4D"], timeout=10)
    _run_git(project_dir, ["config", "user.email", "noreply@yantra4d.com"], timeout=10)

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


def git_show_head(project_dir: Path, filepath: str) -> dict:
    """Get the HEAD version of a file."""
    result = _run_git(project_dir, ["show", f"HEAD:{filepath}"])
    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}
    return {"success": True, "content": result.stdout}


def git_archive_head(project_dir: Path, target_dir: Path) -> dict:
    """Extract the entire HEAD tree into target_dir."""
    try:
        # Provide output directory
        target_dir.mkdir(parents=True, exist_ok=True)
        # Use git archive piped to tar 
        p1 = subprocess.Popen(["git", "archive", "HEAD"], cwd=str(project_dir), stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["tar", "-x", "-C", str(target_dir)], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()  # Allow p1 to receive a SIGPIPE if p2 exits.
        p2.communicate(timeout=GIT_TIMEOUT)
        
        if p2.returncode != 0:
            return {"success": False, "error": "Failed to extract HEAD archive"}
            
        return {"success": True, "target_dir": target_dir}
    except Exception as e:
        return {"success": False, "error": str(e)}


def git_log(project_dir: Path, limit: int = 20) -> dict:
    """Get recent commit log entries.

    Args:
        project_dir: Path to the git repository.
        limit: Maximum number of commits to return (capped at 50).

    Returns:
        dict with success flag and commits list.
    """
    limit = max(1, min(limit, 50))
    # Use %x1f (unit separator) as field delimiter and %x1e (record separator) as record delimiter
    # to avoid ambiguity with commit messages containing newlines or special characters.
    fmt = "%H%x1f%h%x1f%an%x1f%aI%x1f%s"
    result = _run_git(project_dir, ["log", f"--format={fmt}", f"-{limit}"], timeout=15)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        # Empty repo with no commits returns 128
        if "does not have any commits" in stderr or "bad default revision" in stderr:
            return {"success": True, "commits": []}
        return {"success": False, "error": stderr}

    commits = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("\x1f")
        if len(parts) < 5:
            continue
        commits.append({
            "hash": parts[0],
            "short_hash": parts[1],
            "author": parts[2],
            "date": parts[3],
            "message": parts[4],
        })

    return {"success": True, "commits": commits}


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
    """Push to origin using GIT_ASKPASS for credential injection.

    Credentials never touch .git/config — they are passed via a temporary
    script that git reads once and which is deleted immediately after.
    """
    original_url = _get_remote_url(project_dir)
    if not original_url:
        return {"success": False, "error": "No origin remote configured"}

    askpass_env = _make_askpass_env(github_token)
    try:
        result = _run_git(project_dir, ["push", "origin", "HEAD"], env=askpass_env)
        if result.returncode != 0:
            return {"success": False, "error": f"git push failed: {_sanitize_git_output(result.stderr.strip())}"}
        return {"success": True}
    finally:
        _cleanup_askpass(askpass_env)


def git_pull(project_dir: Path, github_token: str) -> dict:
    """Pull from origin using GIT_ASKPASS for credential injection.

    Credentials never touch .git/config — they are passed via a temporary
    script that git reads once and which is deleted immediately after.
    """
    original_url = _get_remote_url(project_dir)
    if not original_url:
        return {"success": False, "error": "No origin remote configured"}

    askpass_env = _make_askpass_env(github_token)
    try:
        result = _run_git(project_dir, ["pull", "--ff-only", "origin"], env=askpass_env)
        if result.returncode != 0:
            return {"success": False, "error": f"git pull failed: {_sanitize_git_output(result.stderr.strip())}"}
        return {"success": True}
    finally:
        _cleanup_askpass(askpass_env)
