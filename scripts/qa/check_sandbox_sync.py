#!/usr/bin/env python3
"""Sandbox drift guard — the vendored commons-sandbox core must match its lock.

Yantra4D's cq_runner and Fashion Cabinet's fc_runner share one restricted-execution
security core (packages/commons-sandbox). The canonical source is Fashion Cabinet;
this repo vendors a copy. This lane asserts the vendored SECURITY CORE
(core.py + __init__.py) matches the sha256 hashes pinned in sandbox.lock.json, so a
change to the shared core cannot silently drift between the two runners — if Fashion
Cabinet updates it, this goes red until the copy here is refreshed and re-pinned.

    python scripts/qa/check_sandbox_sync.py            # verify (CI)
    python scripts/qa/check_sandbox_sync.py --update   # re-pin after re-vendoring

Read-proof and fail-closed: a missing file or lock, or any hash mismatch, fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages" / "commons-sandbox" / "src" / "commons_sandbox"
LOCK = ROOT / "packages" / "commons-sandbox" / "sandbox.lock.json"

# The security-critical files whose bytes must not drift from the canonical source.
GUARDED = ["core.py", "__init__.py"]


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _current() -> dict[str, str]:
    return {name: _hash(PKG / name) for name in GUARDED}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--update", action="store_true",
                    help="re-pin sandbox.lock.json to the vendored files' current hashes")
    args = ap.parse_args()

    missing = [n for n in GUARDED if not (PKG / n).is_file()]
    if missing:
        print(f"check_sandbox_sync: FAIL — vendored core missing: {', '.join(missing)}")
        return 1

    current = _current()

    if args.update:
        LOCK.write_text(json.dumps({
            "_comment": "sha256 of the vendored commons-sandbox security core. "
                        "Canonical source: fashion-cabinet/packages/commons-sandbox. "
                        "Re-pin only after re-vendoring; see VENDORED.md.",
            "hashes": current,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"check_sandbox_sync: re-pinned {len(current)} files in {LOCK.name}")
        return 0

    if not LOCK.exists():
        print(f"check_sandbox_sync: FAIL — {LOCK.name} missing (run with --update to create)")
        return 1

    locked = json.loads(LOCK.read_text(encoding="utf-8")).get("hashes", {})
    problems = []
    for name in GUARDED:
        if locked.get(name) != current[name]:
            problems.append(
                f"{name}: vendored copy does not match the lock — the shared sandbox "
                f"core drifted; re-vendor from fashion-cabinet and re-pin"
            )

    print(f"check_sandbox_sync: guarded={len(GUARDED)} mismatches={len(problems)}")
    for p in problems:
        print(f"  FAIL {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
