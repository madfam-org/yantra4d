#!/usr/bin/env python3
"""Graph-core drift guard — the vendored hyperobject graph core, in both directions.

RFC 0067 (owner ruling G-2) put the kernel-neutral graph core — graph format 1.2, the
node-pack interface and the `script` node contract — in the keystone,
`madfam-org/hyperobjects-spec` `src/hyperobject_graph/`, where it is CANONICAL. Every
kernel vendors a byte-identical copy and pins it by the keystone's `core.lock.json`; this
repo's copy is `packages/hyperobject-graph/src/hyperobject_graph/` (see its VENDORED.md).
It is the mirror of the graph ENGINE, which is canonical here and vendored there
(`check_spec_graph_vendor.py`).

    python3 scripts/qa/check_graph_core_vendor.py            # the copy matches its lock
    python3 scripts/qa/check_graph_core_vendor.py --spec     # ... and the keystone's lock

Default (blocking in `ci.yml`, no keystone needed): the vendored `core.lock.json` is the
one the keystone published (its sha256 is pinned below), every vendored file's sha256
equals that lock, and the lock lists exactly the vendored files. A hand-edit of the copy,
with or without its lock, goes red.

`--spec` (where the keystone is installed at SPEC_PIN): additionally, the INSTALLED
keystone's `hyperobject_graph/core.lock.json` pins the same files with the same hashes as
the vendored lock. A core change in the keystone goes red here at the next pin move until
the copy is refreshed. A pin that predates the core (no `hyperobject_graph` installed)
stands down in one line, as `check_spec_graph_vendor.py` does for the engine; a keystone
that is present but broken still fails.

Read-proof and fail-closed: a missing file or lock, or any mismatch, fails.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "packages" / "hyperobject-graph" / "src" / "hyperobject_graph"
LOCK = PKG / "core.lock.json"

# The keystone commit this copy was taken from, and the sha256 of ITS core.lock.json.
# Pinned here, outside the copy, so that editing a vendored file AND its lock together
# cannot pass: the lock must still be the one the keystone published. Re-vendoring moves
# both lines in the same commit (VENDORED.md).
CANONICAL_COMMIT = "85ac9f542ce97be7771eae65d86442cea9d49aa5"
CANONICAL_LOCK_SHA256 = "8bbf19c501877896d4ea28205157fb2655af088d8baeeef614104b4a75a08c37"


def _vendored_files() -> list[str]:
    """Every vendored file at any depth, as the keystone's lock names them (relative
    posix paths), except the lock itself and bytecode caches."""
    return sorted(
        p.relative_to(PKG).as_posix() for p in PKG.rglob("*")
        if p.is_file() and p != LOCK and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )


def check_copy() -> list[str]:
    if not LOCK.is_file():
        return [f"{LOCK.relative_to(REPO)} missing — re-vendor (VENDORED.md)"]
    if hashlib.sha256(LOCK.read_bytes()).hexdigest() != CANONICAL_LOCK_SHA256:
        not_published = (
            f"core.lock.json is not the lock the keystone published at "
            f"{CANONICAL_COMMIT[:8]} — re-vendor from the keystone and move "
            f"CANONICAL_COMMIT/CANONICAL_LOCK_SHA256 together (VENDORED.md)"
        )
        return [not_published]
    locked = json.loads(LOCK.read_text(encoding="utf-8")).get("hashes", {})
    files = _vendored_files()
    problems = []
    for name in sorted(set(files) | set(locked)):
        if name not in files:
            problems.append(f"{name}: locked but not vendored")
        elif name not in locked:
            problems.append(f"{name}: vendored but not in the lock")
        elif hashlib.sha256((PKG / name).read_bytes()).hexdigest() != locked[name]:
            problems.append(f"{name}: the vendored copy was edited — re-vendor, never hand-edit")
    return problems


def check_spec() -> tuple[list[str], str | None]:
    """Compare with the installed keystone. Returns (problems, stand-down reason)."""
    spec = importlib.util.find_spec("hyperobject_graph")
    if spec is None or spec.origin is None:
        return [], "the installed keystone has no hyperobject_graph (pin predates the core)"
    installed = Path(spec.origin).resolve().parent
    if REPO in installed.parents:
        # The vendored copy shadows the import. Stand down only when no keystone is
        # installed at all; a keystone hidden behind the copy must not read as absent.
        try:
            from importlib.metadata import PackageNotFoundError, distribution

            distribution("hyperobjects-spec")
        except PackageNotFoundError:
            return [], "only the vendored copy is importable here; no keystone installed"
        shadowed = (
            "the keystone is installed but the vendored copy shadows its "
            "hyperobject_graph on the import path — run without it on sys.path"
        )
        return [shadowed], None
    lock_path = installed / "core.lock.json"
    if not lock_path.is_file():
        missing = f"the installed keystone's hyperobject_graph has no core.lock.json ({installed})"
        return [missing], None
    theirs = json.loads(lock_path.read_text(encoding="utf-8")).get("hashes", {})
    ours = json.loads(LOCK.read_text(encoding="utf-8")).get("hashes", {})
    if theirs != ours:
        moved = sorted(n for n in set(theirs) | set(ours) if theirs.get(n) != ours.get(n))
        drift = (
            f"the keystone at SPEC_PIN carries a different graph core ({', '.join(moved)}) "
            f"— re-vendor packages/hyperobject-graph from it (VENDORED.md)"
        )
        return [drift], None
    return [], None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", action="store_true",
                    help="also compare with the installed keystone's core lock")
    args = ap.parse_args()

    problems = check_copy()
    stood_down = None
    if args.spec and not problems:
        spec_problems, stood_down = check_spec()
        problems += spec_problems
    if stood_down:
        print(f"check_graph_core_vendor: keystone comparison inactive — {stood_down}")
    print(f"check_graph_core_vendor: files={len(_vendored_files())} problems={len(problems)}")
    for p in problems:
        print(f"  FAIL {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
