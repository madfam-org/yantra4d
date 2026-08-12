#!/usr/bin/env python3
"""
Keep the Studio's offline fallback manifest in step with its source cartridge.

apps/studio/src/config/fallback-manifest.json is what the Studio serves when it
runs offline / in WASM mode with no backend reachable. It must be the gridfinity
cartridge manifest minus `project.force_backend` (which only makes sense when a
backend exists). When the two drift, offline mode silently validates against
different constraints and quotes different print estimates than the server.

Usage:
    python3 scripts/qa/sync_fallback_manifest.py           # rewrite the fallback
    python3 scripts/qa/sync_fallback_manifest.py --check   # CI drift gate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "projects" / "gridfinity" / "project.json"
FALLBACK = REPO / "apps" / "studio" / "src" / "config" / "fallback-manifest.json"


def expected() -> dict:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    # The fallback intentionally omits force_backend: offline mode has no backend
    # to force rendering onto.
    src.get("project", {}).pop("force_backend", None)
    return src


def main() -> int:
    ap = argparse.ArgumentParser(description="Sync the Studio offline fallback manifest")
    ap.add_argument("--check", action="store_true", help="fail if the fallback is stale")
    args = ap.parse_args()

    if not SOURCE.exists():
        print(f"ERROR: source manifest missing: {SOURCE.relative_to(REPO)}")
        print("Did the gridfinity submodule fail to check out? Try: git submodule update --init")
        return 1

    want = expected()
    payload = json.dumps(want, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        current = json.loads(FALLBACK.read_text(encoding="utf-8")) if FALLBACK.exists() else None
        if current == want:
            print("Fallback manifest is in sync with projects/gridfinity/project.json")
            return 0
        print("ERROR: apps/studio/src/config/fallback-manifest.json is out of sync "
              "with projects/gridfinity/project.json")
        print("Offline/WASM mode would validate and estimate differently from the server.")
        print("Fix with: python3 scripts/qa/sync_fallback_manifest.py")
        return 1

    FALLBACK.write_text(payload, encoding="utf-8")
    print(f"Wrote {FALLBACK.relative_to(REPO)} from {SOURCE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
