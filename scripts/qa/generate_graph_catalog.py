#!/usr/bin/env python3
"""Emit the graph node vocabulary as JSON for client consumption.

The transpiler in ``apps/api/services/engine/graph_engine.py`` is the single
source of truth for which nodes exist, what params they take, and how their
sockets are typed. The studio's node editor needs the same vocabulary, and a
hand-maintained copy would drift the moment either side changed — so the copy
is generated from the Python definitions and committed.

Run with ``--check`` in CI to fail when the committed file is stale.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "apps" / "api"

# The canonical contract lives with the schemas; the studio keeps a copy inside
# its own source tree because it is a standalone package that cannot import
# across the repo boundary. Same pattern the fallback manifest already uses,
# and --check keeps both honest.
OUTPUT_PATHS = (
    REPO_ROOT / "packages" / "schemas" / "graph-node-catalog.json",
    REPO_ROOT / "apps" / "studio" / "src" / "config" / "graph-node-catalog.json",
)

sys.path.insert(0, str(API_DIR))


def build_catalog() -> dict:
    from services.engine.graph_engine import (
        _PLANES,
        GRAPH_FILE_SUFFIX,
        MAX_NODES,
        MAX_OUTPUTS,
        MAX_PATTERN_COUNT,
        NODE_TYPES,
    )

    # Kinds that a manifest parameter may bind to. Structural kinds stay literal
    # so a render-time value can never reshape the emitted script.
    bindable_kinds = {"float", "count"}

    nodes = {}
    for type_name in sorted(NODE_TYPES):
        spec = NODE_TYPES[type_name]
        params = {}
        for param_name in sorted(spec["params"]):
            kind, default = spec["params"][param_name]
            params[param_name] = {
                "kind": kind,
                "default": default,
                "bindable": kind in bindable_kinds,
            }
        nodes[type_name] = {
            "output": spec["output"],
            "inputs": dict(sorted(spec["inputs"].items())),
            "params": params,
        }

    return {
        "generated_by": "scripts/qa/generate_graph_catalog.py",
        "source_of_truth": "apps/api/services/engine/graph_engine.py",
        "graph_file_suffix": GRAPH_FILE_SUFFIX,
        "limits": {
            "max_nodes": MAX_NODES,
            "max_outputs": MAX_OUTPUTS,
            "max_pattern_count": MAX_PATTERN_COUNT,
        },
        "planes": sorted(_PLANES),
        "nodes": nodes,
    }


def render(catalog: dict) -> str:
    return json.dumps(catalog, indent=2, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the committed catalog differs from the generated one",
    )
    args = parser.parse_args()

    text = render(build_catalog())

    if args.check:
        stale = []
        for path in OUTPUT_PATHS:
            if not path.is_file() or path.read_text() != text:
                stale.append(path.relative_to(REPO_ROOT))
        if stale:
            print(
                "STALE: "
                + ", ".join(str(p) for p in stale)
                + "\ndoes not match the node vocabulary in "
                "apps/api/services/engine/graph_engine.py.\n"
                "Regenerate with: python3 scripts/qa/generate_graph_catalog.py"
            )
            return 1
        print("graph node catalog in sync")
        return 0

    for path in OUTPUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    print(f"Wrote {len(OUTPUT_PATHS)} copies ({len(build_catalog()['nodes'])} node types)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
