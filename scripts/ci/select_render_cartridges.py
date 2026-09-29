#!/usr/bin/env python3
"""Select changed cartridges across the platform's commons gitlink.

Print one checkout-relative directory per line. Missing Git history or an
uninitialised/wrong commons checkout is an error, never an empty selection.
"""
import argparse
from pathlib import Path
import subprocess
import sys


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=120)


def tree_entry(repo, ref):
    entries = git(repo, "ls-tree", "-z", ref, "--", "projects").split(b"\0")
    for entry in entries:
        if entry:
            metadata, name = entry.split(b"\t", 1)
            if name == b"projects":
                mode, _, oid = metadata.decode().split()
                return mode, oid
    return None


def select(repo, base, head="HEAD"):
    # Resolve revisions before using them in further Git commands.
    base = git(repo, "rev-parse", "--verify", "--end-of-options", base + "^{commit}").decode().strip()
    head = git(repo, "rev-parse", "--verify", "--end-of-options", head + "^{commit}").decode().strip()
    commons = repo / "projects"
    available = sorted(p.parent for p in commons.glob("*/project.json") if p.is_file())
    if not available:
        raise ValueError("No commons cartridges found; initialise the pinned checkout")
    if any("\n" in p.name or "\r" in p.name for p in available):
        raise ValueError("Cartridge names cannot contain line breaks")
    old, new = tree_entry(repo, base), tree_entry(repo, head)
    if new is None:
        raise ValueError("Target revision contains no commons tree or gitlink")
    if new and new[0] == "160000":
        actual = git(commons, "rev-parse", "HEAD").decode().strip()
        if actual != new[1]:
            raise ValueError("Commons checkout does not match the target gitlink")
        if old == new:
            return []
        if not old or old[0] != "160000":
            return available  # topology migration: the entire new pin needs checking
        try:
            git(commons, "cat-file", "-e", old[1] + "^{commit}")
        except subprocess.CalledProcessError:
            # actions/checkout may have fetched only the current commons commit.
            # Fetch only the exact base gitlink from its configured origin.
            git(commons, "fetch", "--no-tags", "origin", old[1])
        changed = git(commons, "diff", "--name-only", "-z", old[1], new[1], "--")
        paths = [Path(p.decode()) for p in changed.split(b"\0") if p]
    elif old and old[0] == "160000":
        return available
    else:
        changed = git(repo, "diff", "--name-only", "-z", base, head, "--", "projects")
        paths = [Path(p.decode()).relative_to("projects") for p in changed.split(b"\0") if p]
    # Shared geometry/library changes can affect every consumer.
    if any(p.parts[0] in {"libs", "commons-lib"} or
           (len(p.parts) == 1 and p.suffix in {".py", ".scad"}) for p in paths):
        return available
    touched = {p.parts[0] for p in paths if len(p.parts) > 1}
    return [p for p in available if p.name in touched]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    try:
        for path in select(repo, args.base):
            print(path.relative_to(repo))
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print(f"::error::Cannot select render cartridges: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
