#!/usr/bin/env python3
"""ceq asset coverage for the commons — the N/M tracker.

Every cartridge in ``docs/commons-catalog.json`` should eventually have two
ceq-rendered assets: a ``hyperobject-card`` (the commons trading card) and a
``hyperobject-texture`` (the FLUX material plate). ``scripts/dev/ceq_backfill.py``
mints them and records each one in the sidecar index ``docs/ceq-coverage.json``.
This script reads catalog + sidecar and answers "how many, and which are left?".

Counts are always derived from the catalog as it stands on disk — the commons is
mid-growth (a fourth-hundred merge is in flight) and any number baked into a
script here would be wrong by the next merge.

## Two lanes, deliberately asymmetric

Missing coverage NEVER fails. Until the ``hyperobjects-coverage`` ceq client is
registered and the backfill has run, coverage is 0/N and that is the expected
state, not a regression — a blocking lane here would just be a red X nobody can
clear. Use ``--strict`` (or ``--min-coverage``) once the backfill has landed and
you want the gap defended.

A malformed sidecar ALWAYS fails, in every mode. The sidecar is what stops the
driver re-minting renders it already paid for; a corrupt one is a live bug, not
backlog.

## The thumbnail cross-reference

Coverage is also reported against the existing gallery thumbnails, split real vs
placeholder. That split is the actual priority list: a cartridge whose gallery
tile is still a generated SVG placeholder gains the most from a ceq card, so
``ceq-missing + thumbnail-placeholder`` is the cohort to backfill first.
Classification sniffs magic bytes, not extensions (the placeholder generator can
write SVG into a ``.webp`` name).

Usage:
    python3 scripts/qa/ceq_coverage.py                 # one-line summary + gaps
    python3 scripts/qa/ceq_coverage.py --json          # machine-readable
    python3 scripts/qa/ceq_coverage.py --list-missing card
    python3 scripts/qa/ceq_coverage.py --strict        # fail if any gap remains
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.ceq_coverage_core import (  # noqa: E402
    ASSET_KINDS,
    CATALOG_PATH,
    SIDECAR_PATH,
    CoverageError,
    catalog_entries,
    load_catalog,
    load_sidecar,
    sidecar_record,
    thumbnail_status,
)

THUMB_STATES = ("real", "placeholder", "missing")


def compute(catalog_path: Path, sidecar_path: Path, thumb_dirs=None) -> dict:
    """Build the full coverage report as plain data (so --json and the text
    renderer can never disagree about what was measured)."""
    catalog = load_catalog(catalog_path)
    sidecar = load_sidecar(sidecar_path)  # raises CoverageError when malformed
    entries = catalog_entries(catalog)
    total = len(entries)

    per_kind = {kind: {"covered": 0, "missing": []} for kind in ASSET_KINDS}
    thumbs = Counter()
    # cohort key: (kind, thumbnail_state) -> count of slugs MISSING that kind
    cohorts: Counter = Counter()
    both = 0

    for entry in entries:
        slug = str(entry["slug"])
        tstate = thumbnail_status(slug, thumb_dirs)
        thumbs[tstate] += 1
        covered_kinds = 0
        for kind in ASSET_KINDS:
            if sidecar_record(sidecar, slug, kind):
                per_kind[kind]["covered"] += 1
                covered_kinds += 1
            else:
                per_kind[kind]["missing"].append(slug)
                cohorts[(kind, tstate)] += 1
        if covered_kinds == len(ASSET_KINDS):
            both += 1

    # Slugs in the sidecar that the catalog no longer lists — stale entries left
    # behind by a renamed or withdrawn cartridge. Informational: the sidecar is
    # append-mostly and pruning is the operator's call.
    known = {str(e["slug"]) for e in entries}
    orphans = sorted(s for s in sidecar.get("assets", {}) if s not in known)

    return {
        "catalog": str(catalog_path),
        "sidecar": str(sidecar_path),
        "sidecar_exists": sidecar_path.exists(),
        "total_cartridges": total,
        "kinds": {
            kind: {
                "covered": per_kind[kind]["covered"],
                "total": total,
                "missing": per_kind[kind]["missing"],
            }
            for kind in ASSET_KINDS
        },
        "complete": both,
        "thumbnails": {state: thumbs.get(state, 0) for state in THUMB_STATES},
        "cohorts": {
            kind: {state: cohorts.get((kind, state), 0) for state in THUMB_STATES}
            for kind in ASSET_KINDS
        },
        "orphans": orphans,
    }


def render_text(report: dict, list_missing: str | None) -> None:
    total = report["total_cartridges"]
    parts = [
        f"{report['kinds'][k]['covered']}/{total} {k}" for k in ASSET_KINDS
    ]
    print(
        f"ceq coverage: {', '.join(parts)} — {report['complete']}/{total} complete"
        + ("" if report["sidecar_exists"] else "  (no sidecar yet — backfill has not run)")
    )

    t = report["thumbnails"]
    print(
        f"  gallery thumbnails: {t['real']} real, {t['placeholder']} placeholder, "
        f"{t['missing']} missing"
    )
    for kind in ASSET_KINDS:
        c = report["cohorts"][kind]
        print(
            f"  {kind} gaps by thumbnail: {c['placeholder']} placeholder-backed, "
            f"{c['missing']} no-thumbnail, {c['real']} already-real"
        )
    if report["orphans"]:
        print(
            f"  {len(report['orphans'])} sidecar slug(s) not in the catalog: "
            + ", ".join(report["orphans"][:8])
            + (" …" if len(report["orphans"]) > 8 else "")
        )

    if list_missing:
        for slug in report["kinds"][list_missing]["missing"]:
            print(f"  MISSING {list_missing} {slug}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    ap.add_argument("--sidecar", type=Path, default=SIDECAR_PATH)
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    ap.add_argument(
        "--list-missing",
        choices=ASSET_KINDS,
        help="print every slug missing this asset kind (feeds --only / a worklist)",
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="fail when any cartridge is missing an asset (use after the backfill lands)",
    )
    ap.add_argument(
        "--min-coverage",
        type=float,
        default=None,
        metavar="PCT",
        help="fail when per-kind coverage is below this percentage (0-100)",
    )
    args = ap.parse_args()

    try:
        report = compute(args.catalog, args.sidecar)
    except CoverageError as exc:
        # Malformed sidecar/catalog is always fatal, in every mode.
        print(f"ceq coverage: FAILED — {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        render_text(report, args.list_missing)

    total = report["total_cartridges"]
    if args.strict and report["complete"] < total:
        print(
            f"ceq coverage: --strict — {total - report['complete']} cartridge(s) "
            "still missing at least one ceq asset",
            file=sys.stderr,
        )
        return 1
    if args.min_coverage is not None and total:
        for kind in ASSET_KINDS:
            pct = 100.0 * report["kinds"][kind]["covered"] / total
            if pct < args.min_coverage:
                print(
                    f"ceq coverage: --min-coverage — {kind} at {pct:.1f}% "
                    f"< {args.min_coverage:.1f}%",
                    file=sys.stderr,
                )
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
