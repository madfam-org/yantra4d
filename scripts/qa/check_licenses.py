#!/usr/bin/env python3
"""
Cross-check every cartridge's declared license against the license it ships.

A cartridge declares `hyperobject.commons_license` in project.json, and ships a
LICENSE file. Nothing kept those two honest, so the Commons accumulated:

  - cartridges declaring CERN-OHL-W-2.0 while shipping GPL (upstream forks that
    cannot legally be relicensed),
  - a cartridge whose LICENSE file is a saved HTML 404 page,
  - a proprietary, all-rights-reserved client design inside a public commons,
  - cartridges shipping a license they never declared.

Findings are grouped by severity. `--strict` fails on CONFLICT only, so the
metadata backlog can be worked down without blocking every build; use
`--strict-all` to fail on anything.

Usage:
    python3 scripts/qa/check_licenses.py            # report
    python3 scripts/qa/check_licenses.py --strict   # fail on conflicts
"""
from __future__ import annotations

import argparse
import configparser
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO / "projects"


def submodule_slugs() -> set[str]:
    """Cartridges published as their own repo.

    Only these need a LICENSE file of their own — a cartridge that lives inside
    this repo is covered by the root LICENSE plus its declared commons_license.
    """
    gitmodules = REPO / ".gitmodules"
    if not gitmodules.exists():
        return set()
    cp = configparser.ConfigParser()
    cp.read_string(gitmodules.read_text(encoding="utf-8"))
    return {
        cp[s]["path"].split("/", 1)[1]
        for s in cp.sections()
        if cp[s].get("path", "").startswith("projects/")
    }

# Licenses that cannot be relicensed under the Commons default because they are
# copyleft: a derivative work has to keep them.
COPYLEFT = {"GPL-2.0", "GPL-3.0", "AGPL-3.0"}
COMMONS_DEFAULT = "CERN-OHL-W-2.0"


def identify(path: Path) -> str:
    """Best-effort SPDX-ish identifier for a license file."""
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:4000]
    except OSError:
        return "UNREADABLE"

    # A license file that is actually a web page is a download that silently failed.
    if re.match(r"\s*<(!doctype|html)", head, re.I):
        return "HTML-ERROR-PAGE"

    version = "3.0" if re.search(r"Version 3", head) else ("2.0" if re.search(r"Version 2", head) else "")
    if "GNU LESSER GENERAL PUBLIC" in head:
        return f"LGPL-{version or '3.0'}"
    if "GNU AFFERO" in head:
        return f"AGPL-{version or '3.0'}"
    if "GNU GENERAL PUBLIC" in head:
        return f"GPL-{version or '3.0'}"
    if "CERN Open Hardware" in head or "CERN-OHL" in head:
        variant = ("W" if "Weakly Reciprocal" in head
                   else "S" if "Strongly Reciprocal" in head
                   else "P" if "Permissive" in head else "?")
        return f"CERN-OHL-{variant}-2.0"
    if "BSD 2-Clause" in head:
        return "BSD-2-Clause"
    if "BSD 3-Clause" in head:
        return "BSD-3-Clause"
    if "Apache License" in head:
        return "Apache-2.0"
    if "Permission is hereby granted, free of charge" in head:
        return "MIT"
    if "Creative Commons" in head or "creativecommons.org" in head:
        m = re.search(r"(CC[- ]BY[A-Z-]*)[- ]?(\d\.\d)?", head, re.I)
        return (m.group(0).upper().replace(" ", "-") if m else "CC")
    if re.search(r"All rights reserved|Uso Privado|Private Use|Proprietary", head, re.I):
        return "PROPRIETARY"
    return "UNKNOWN"


def audit() -> list[dict]:
    findings = []
    standalone = submodule_slugs()
    for manifest in sorted(PROJECTS.glob("*/project.json")):
        slug = manifest.parent.name
        hyper = json.loads(manifest.read_text(encoding="utf-8")).get("hyperobject") or {}
        declared = hyper.get("commons_license") if isinstance(hyper, dict) else None

        files = {p.name: identify(p) for p in sorted(manifest.parent.glob("LICENSE*"))}
        files.update({p.name: identify(p) for p in sorted(manifest.parent.glob("COPYING*"))})
        shipped = {v for v in files.values()}

        def add(severity, message):
            findings.append({"severity": severity, "slug": slug, "declared": declared,
                             "files": files, "message": message})

        if not files:
            # An in-repo cartridge is covered by the root LICENSE; only a
            # cartridge published as its own repo needs to carry one.
            if slug in standalone:
                add("METADATA", "published as its own repo but ships no LICENSE file")
            elif not declared:
                add("METADATA", "declares no commons_license and ships no LICENSE file")
            continue

        if "HTML-ERROR-PAGE" in shipped:
            add("CONFLICT", "LICENSE file is a saved HTML error page, not license text — "
                            "the cartridge effectively ships no license")
        if "PROPRIETARY" in shipped:
            add("CONFLICT", "ships an all-rights-reserved / proprietary license but sits in a "
                            "public commons catalogue")
        copyleft = shipped & COPYLEFT
        if copyleft and declared and declared not in copyleft:
            add("CONFLICT", f"declares {declared} but ships {', '.join(sorted(copyleft))} — "
                            f"copyleft cannot be relicensed on a derivative work")
        if len(shipped - {"UNKNOWN"}) > 1:
            add("CONFLICT", f"ships more than one license: {', '.join(sorted(shipped))}")
        if declared and shipped and declared not in shipped and not copyleft:
            add("MISMATCH", f"declares {declared} but ships {', '.join(sorted(shipped))}")
        if not declared:
            add("METADATA", f"declares no commons_license; ships {', '.join(sorted(shipped))}")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit cartridge licensing consistency")
    ap.add_argument("--strict", action="store_true", help="exit non-zero on CONFLICT findings")
    ap.add_argument("--strict-all", action="store_true", help="exit non-zero on any finding")
    args = ap.parse_args()

    findings = audit()
    order = {"CONFLICT": 0, "MISMATCH": 1, "METADATA": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["slug"]))

    conflicts = [f for f in findings if f["severity"] == "CONFLICT"]
    mismatches = [f for f in findings if f["severity"] == "MISMATCH"]
    metadata = [f for f in findings if f["severity"] == "METADATA"]

    for f in findings:
        print(f"[{f['severity']:8}] {f['slug']:26} {f['message']}")
        if f["severity"] != "METADATA":
            print(f"{'':11} files: {f['files']}")

    total = len(list(PROJECTS.glob("*/project.json")))
    print(f"\n{total} cartridges — {len(conflicts)} conflict, "
          f"{len(mismatches)} mismatch, {len(metadata)} metadata-only")

    if args.strict_all and findings:
        return 1
    if args.strict and conflicts:
        print("\nCONFLICT findings block: a cartridge must not ship a license it cannot honour.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
