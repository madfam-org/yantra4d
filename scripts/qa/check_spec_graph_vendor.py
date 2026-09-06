#!/usr/bin/env python3
"""The other half of the graph-engine drift guard: is the KEYSTONE's copy current?

`hyperobjects-spec` renders `.graph.json` cartridges by transpiling them with a
**vendored, byte-identical copy** of this repo's graph engine — `y4d_spec/graph/`,
pinned there by sha256 in `graph.lock.json` and guarded on that side by
`scripts/qa/check_graph_sync.py`. The copy is what makes the keystone's verdict about a
graph cartridge a verdict about the script THIS platform actually runs.

That guard alone only stops the keystone from drifting away from its own lock. It cannot
notice this direction: an engine change lands HERE, the keystone's copy is now stale, its
lock still matches its own (old) copy, and both repos stay green while the keystone
verifies graph cartridges against a transpiler the platform no longer uses. Nothing would
say so until someone happened to diff the two files.

So this is the reverse assertion, run where the keystone is already installed at
`SPEC_PIN`: the INSTALLED keystone's vendored hashes must equal this repo's live files.
An engine change here goes red until the keystone is re-vendored, re-pinned, and the pin
moved.

    python3 scripts/qa/check_spec_graph_vendor.py

WHEN THE SPEC IS OLDER THAN THE CONTRACT
----------------------------------------
Exactly the posture `check_render_env.py` takes, and for the same reason: a pin that
predates `y4d_spec.graph` must not make this guard red by accident. A MISSING
`y4d_spec.graph` (or a missing lock inside it) exits 0 with a one-line "spec too old —
check inactive". Any other import error still fails: a spec that is present but BROKEN
must not read as a spec that is merely old.

Note the asymmetry that follows from that: this check goes live only once `SPEC_PIN`
moves to a keystone carrying the vendored engine. Until then it prints its stand-down
line, which is the honest report — there is nothing to compare yet.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# The live files here, keyed by the name the keystone vendors them under. This mapping is
# the contract; the keystone's `graph.lock.json` carries the same one in `canonical_paths`
# and a disagreement between the two is itself a drift worth failing on.
CANONICAL = {
    "graph_engine.py": REPO / "apps" / "api" / "services" / "engine" / "graph_engine.py",
    "graph.schema.json": REPO / "packages" / "schemas" / "graph.schema.json",
    "graph-node-catalog.json": REPO / "packages" / "schemas" / "graph-node-catalog.json",
}


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_spec_lock():
    """The installed keystone's vendored lock, or None when the pin predates it.

    Returns (lock_dict, package_dir, None) or (None, None, reason). Only a MISSING
    `y4d_spec.graph` — or a keystone that has the package but no lock file — is a reason
    to stand down; anything else raises.
    """
    try:
        import y4d_spec.graph as vendored
    except ImportError as exc:
        name = getattr(exc, "name", "") or ""
        if name in ("y4d_spec", "y4d_spec.graph"):
            return None, None, str(exc)
        raise

    pkg_dir = Path(vendored.__file__).resolve().parent
    lock_path = pkg_dir / "graph.lock.json"
    if not lock_path.is_file():
        return None, None, f"no graph.lock.json in the installed {pkg_dir}"
    return json.loads(lock_path.read_text(encoding="utf-8")), pkg_dir, None


def main() -> int:
    lock, pkg_dir, inactive = load_spec_lock()
    if lock is None:
        print(
            f"check_spec_graph_vendor: spec too old — check inactive "
            f"({inactive}). It goes live with the next spec pin bump."
        )
        return 0

    missing = [name for name, path in CANONICAL.items() if not path.is_file()]
    if missing:
        print(
            f"check_spec_graph_vendor: FAIL — canonical source missing here: "
            f"{', '.join(missing)}"
        )
        return 1

    locked = lock.get("hashes", {})
    problems = []

    # The keystone must be pinning exactly the files this repo considers canonical. A
    # keystone that vendored a different SET is a drift the hashes alone would not show.
    if set(locked) != set(CANONICAL):
        problems.append(
            f"the installed keystone pins {sorted(locked)} but this repo's canonical set "
            f"is {sorted(CANONICAL)} — the vendoring contract itself has drifted"
        )

    for name, path in CANONICAL.items():
        here = _hash(path)
        there = locked.get(name)
        if there is None:
            continue  # already reported by the set comparison above
        if here != there:
            rel = path.relative_to(REPO)
            problems.append(
                f"{name}: this repo's {rel} is sha256 {here[:12]}…, the installed "
                f"keystone vendors {there[:12]}… — re-vendor into hyperobjects-spec "
                f"(cp the file, then `python scripts/qa/check_graph_sync.py --update`), "
                f"land it, and move SPEC_PIN"
            )

    print(
        f"check_spec_graph_vendor: comparing {len(CANONICAL)} canonical files against the "
        f"keystone vendored at {pkg_dir} — mismatches={len(problems)}"
    )
    for p in problems:
        print(f"  FAIL {p}")
    if problems:
        print(
            "  The keystone transpiles graph cartridges with a byte-identical copy of "
            "this engine. A stale copy means the commons' graph cartridges are verified "
            "against a transpiler this platform no longer runs. See "
            "hyperobjects-spec/src/y4d_spec/graph/VENDORED.md."
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
