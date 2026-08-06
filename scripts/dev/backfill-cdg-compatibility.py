#!/usr/bin/env python3
"""Backfill derived CDG compatibility into manifests' `compatible_with` fields.

The compatibility graph (apps/api/services/core/compatibility_graph.py) DERIVES which
objects interface, from each interface's `geometry_type` + `standard`. That derivation is
computed live, but only ~22 explicit `compatible_with` links were ever hand-authored. This
script PERSISTS the derived edges back into the manifests so the interoperability data is
durable (survives even if the deriver changes) and visible to anyone reading a project.json.

For each object, for each of its CDG interfaces that resolves to a known standard family,
it adds the slugs of every OTHER object that mates with it *on that family* to that
interface's `compatible_with` list — merged with (never clobbering) any existing entries,
deduped, sorted. Idempotent: running twice is a no-op.

    # preview what would change, touch nothing:
    .venv/bin/python scripts/dev/backfill-cdg-compatibility.py --dry-run
    # write:
    .venv/bin/python scripts/dev/backfill-cdg-compatibility.py
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "apps" / "api"))

from services.core.compatibility_graph import (  # noqa: E402
    _geometry_compatible,
    normalize_family,
)


def _load(pj: Path) -> dict | None:
    try:
        return json.loads(pj.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _hyperobject(data: dict) -> dict:
    proj = data.get("project", {}) or {}
    return data.get("hyperobject", {}) or proj.get("hyperobject", {}) or {}


def _submodule_dirs() -> set[Path]:
    """Absolute paths of every git submodule under the repo.

    Submodule-backed projects (gridfinity, din-rail-clip, motor-mount, …) are
    externally-owned repos; writing into their project.json from the parent leaves
    the submodule dirty and desyncs checks like manifest-sync. We NEVER backfill
    them here — their compatible_with belongs in the submodule repo via its own PR.
    """
    gm = REPO / ".gitmodules"
    subs: set[Path] = set()
    if not gm.exists():
        return subs
    for line in gm.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("path"):
            _, _, path = line.partition("=")
            subs.add((REPO / path.strip()).resolve())
    return subs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", default="projects")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pdir = REPO / args.projects
    submodules = _submodule_dirs()
    skipped_submodules = 0
    manifests: dict[str, tuple[Path, dict]] = {}
    for pj in sorted(pdir.glob("*/project.json")):
        if pj.parent.resolve() in submodules:
            skipped_submodules += 1
            continue
        data = _load(pj)
        if not data:
            continue
        proj = data.get("project", {}) or {}
        if proj.get("unlisted"):
            continue
        slug = proj.get("slug") or pj.parent.name
        manifests[slug] = (pj, data)

    # Index every (slug, family) → the interface's geometry_type
    # family_members[family] = list of (slug, geometry_type)
    family_members: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for slug, (_, data) in manifests.items():
        for c in (_hyperobject(data).get("cdg_interfaces", []) or []):
            fam = normalize_family(c.get("standard", ""))
            if fam:
                family_members[fam].append((slug, c.get("geometry_type", "")))

    # For each object's interface, compute the set of compatible partner slugs on its family
    # partners[slug][family] = set(partner slugs)
    partners: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for fam, members in family_members.items():
        for i in range(len(members)):
            for j in range(len(members)):
                if i == j:
                    continue
                (slug_a, gt_a), (slug_b, gt_b) = members[i], members[j]
                if slug_a == slug_b:
                    continue
                if _geometry_compatible(gt_a, gt_b):
                    partners[slug_a][fam].add(slug_b)

    changed = 0
    added_total = 0
    for slug, (pj, data) in manifests.items():
        ho = _hyperobject(data)
        ifaces = ho.get("cdg_interfaces", []) or []
        dirty = False
        for c in ifaces:
            fam = normalize_family(c.get("standard", ""))
            if not fam:
                continue
            derived = partners.get(slug, {}).get(fam, set())
            if not derived:
                continue
            existing = [x for x in (c.get("compatible_with") or []) if isinstance(x, str)]
            merged = sorted(set(existing) | derived)
            if merged != existing:
                added_total += len(set(merged) - set(existing))
                c["compatible_with"] = merged
                dirty = True
        if dirty:
            changed += 1
            if not args.dry_run:
                pj.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")

    verb = "would update" if args.dry_run else "updated"
    print(f"backfill: {verb} {changed} manifests, +{added_total} compatible_with links "
          f"across {len(family_members)} standard families "
          f"(skipped {skipped_submodules} submodule-backed projects)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
