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

# Cartridges deliberately outside the published Commons. Their licence terms are
# whatever they are — a proprietary client design is correct, not a defect — so
# the requirement inverts: what matters is that they stay out of the catalogue.
# Kept in step with NOT_COMMONS in scripts/qa/generate_commons_catalog.py.
NOT_COMMONS = {
    "tablaco": "client engagement — client retains all private rights",
    "cq-hyperobject-test": "engine test fixture, not a Commons object; repo archived",
}
CLIENT_PRIVATE = set(NOT_COMMONS)


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
        # Resolve the exact variant. A bare "CC" hides the difference between a
        # permissive CC-BY and a NonCommercial CC-BY-NC-SA, which is the whole
        # question when deciding whether a design can be sold.
        parts = ["CC", "BY"]
        if re.search(r"NonCommercial", head, re.I):
            parts.append("NC")
        if re.search(r"ShareAlike", head, re.I):
            parts.append("SA")
        if re.search(r"NoDerivatives", head, re.I):
            parts.append("ND")
        ver = re.search(r"(\d\.\d) International", head)
        return "-".join(parts) + (f"-{ver.group(1)}" if ver else "")
    if re.search(r"All rights reserved|Uso Privado|Private Use|Proprietary", head, re.I):
        return "PROPRIETARY"
    return "UNKNOWN"


def published_slugs() -> set[str]:
    """Slugs present in the generated public catalogue."""
    catalog = REPO / "docs" / "commons-catalog.json"
    if not catalog.exists():
        return set()
    try:
        data = json.loads(catalog.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {c.get("slug") for c in data.get("cartridges", [])}


def normalize(identifier: str | None) -> str | None:
    """Strip SPDX suffixes so GPL-3.0-or-later and GPL-3.0 compare equal.

    `-or-later` / `-only` express how a licence may be upgraded, not which
    licence it is; treating them as different identifiers reports a correct
    declaration as a conflict.
    """
    if not identifier:
        return identifier
    return re.sub(r"-(or-later|only)$", "", identifier.strip())


def audit() -> list[dict]:
    findings = []
    standalone = submodule_slugs()
    published = published_slugs()

    # Inverted requirement: client work must stay out of the public catalogue.
    for slug in sorted(CLIENT_PRIVATE & published):
        findings.append({
            "severity": "CONFLICT", "slug": slug, "declared": None, "files": {},
            "message": f"excluded cartridge appears in the published catalogue "
                       f"({NOT_COMMONS[slug]})",
        })

    for manifest in sorted(PROJECTS.glob("*/project.json")):
        slug = manifest.parent.name
        data = json.loads(manifest.read_text(encoding="utf-8"))
        hyper = data.get("hyperobject") or {}
        # Two conventions are in use: Commons cartridges declare
        # hyperobject.commons_license, while several standalone cartridge repos
        # declare project.license. Accept either, or a licensed cartridge gets
        # reported as unlicensed purely for picking the other field.
        candidates = {
            "hyperobject.commons_license": (
                hyper.get("commons_license") if isinstance(hyper, dict) else None),
            "project.license": (data.get("project") or {}).get("license"),
            "license": data.get("license"),
        }
        declared = next((v for v in candidates.values() if v), None)

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

        # Two fields can each hold a licence, so a manifest can contradict
        # itself. Reading only the first non-null would silently hide that.
        stated = {k: v for k, v in candidates.items() if v}
        if len({normalize(v) for v in stated.values()}) > 1:
            add("CONFLICT", "manifest declares conflicting licences in different fields: "
                            + ", ".join(f"{k}={v}" for k, v in sorted(stated.items())))

        if "HTML-ERROR-PAGE" in shipped:
            add("CONFLICT", "LICENSE file is a saved HTML error page, not license text — "
                            "the cartridge effectively ships no license")
        if "PROPRIETARY" in shipped and slug not in CLIENT_PRIVATE:
            add("CONFLICT", "ships an all-rights-reserved / proprietary license but sits in a "
                            "public commons catalogue")
        shipped_norm = {normalize(v) for v in shipped}
        declared_norm = normalize(declared)
        copyleft = shipped_norm & COPYLEFT
        if copyleft and declared_norm and declared_norm not in copyleft:
            add("CONFLICT", f"declares {declared} but ships {', '.join(sorted(copyleft))} — "
                            f"copyleft cannot be relicensed on a derivative work")
        if len(shipped - {"UNKNOWN"}) > 1:
            add("CONFLICT", f"ships more than one license: {', '.join(sorted(shipped))}")
        if declared_norm and shipped and declared_norm not in shipped_norm and not copyleft:
            add("MISMATCH", f"declares {declared} but ships {', '.join(sorted(shipped))}")
        if not declared and slug not in CLIENT_PRIVATE:
            add("METADATA", f"declares no commons_license; ships {', '.join(sorted(shipped))}")
        elif not declared:
            # Correct by design: client work is not part of the Commons, so it
            # has no commons_license to declare.
            add("OK", f"correctly absent from the catalogue — {NOT_COMMONS[slug]} "
                      f"(ships {', '.join(sorted(shipped))})")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit cartridge licensing consistency")
    ap.add_argument("--strict", action="store_true", help="exit non-zero on CONFLICT findings")
    ap.add_argument("--strict-all", action="store_true", help="exit non-zero on any finding")
    args = ap.parse_args()

    findings = audit()
    order = {"CONFLICT": 0, "MISMATCH": 1, "METADATA": 2, "OK": 3}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["slug"]))

    conflicts = [f for f in findings if f["severity"] == "CONFLICT"]
    mismatches = [f for f in findings if f["severity"] == "MISMATCH"]
    metadata = [f for f in findings if f["severity"] == "METADATA"]
    actionable = conflicts + mismatches + metadata

    for f in findings:
        print(f"[{f['severity']:8}] {f['slug']:26} {f['message']}")
        if f["severity"] != "METADATA":
            print(f"{'':11} files: {f['files']}")

    total = len(list(PROJECTS.glob("*/project.json")))
    print(f"\n{total} cartridges — {len(conflicts)} conflict, "
          f"{len(mismatches)} mismatch, {len(metadata)} metadata-only")

    if args.strict_all and actionable:
        return 1
    if args.strict and conflicts:
        print("\nCONFLICT findings block: a cartridge must not ship a license it cannot honour.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
