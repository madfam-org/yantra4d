#!/usr/bin/env python3
"""
Generate the Hyperobjects Commons catalog.

Emits two artifacts from the `projects/*/project.json` manifests:

  docs/commons-catalog.json  — machine-readable, one entry per cartridge, with
                               CDG interfaces, standards, and clone instructions
  COMMONS.md                 — human-readable index grouped by domain

Deliberately NOT written to `llms-full.txt`: that filename is owned by
`internal-devops/scripts/sync-agent-docs.py`, which regenerates it as the
org-wide agent operating contract and overwrites any content placed there.

Usage:
    python3 scripts/qa/generate_commons_catalog.py            # write artifacts
    python3 scripts/qa/generate_commons_catalog.py --check    # CI drift gate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PROJECTS = REPO / "projects"
CATALOG_JSON = REPO / "docs" / "commons-catalog.json"
CATALOG_MD = REPO / "COMMONS.md"
README_MD = REPO / "README.md"
README_BEGIN = "<!-- BEGIN COMMONS_COUNTS -->"
README_END = "<!-- END COMMONS_COUNTS -->"
UPSTREAM = "https://github.com/madfam-org/yantra4d"
#: Where the cartridges themselves live. Since RFC 0038 P2 every published
#: cartridge is a directory at the ROOT of one commons repo, which the platform
#: consumes as the single `projects/` submodule — so there is no longer a
#: "submodule-backed vs vendored" distinction to draw, and every entry clones
#: the same way.
COMMONS_REPO = "https://github.com/madfam-org/solid-hyperobjects"
SCHEMA_VERSION = "commons_catalog_v1"

# Cartridges deliberately kept OUT of the published Commons catalogue, and why.
#
# Kept as an explicit map rather than inferred: a private submodule cloned
# without access simply has no LICENSE to read, so an inferred rule would
# silently include exactly the entries that must never appear.
NOT_COMMONS = {
    # Client engagement. The client retains all private rights to the repo, so
    # the design is not ours to publish. This catalogue ships from a public
    # repo, and an entry here would advertise a private repo, its name, and a
    # clone command for it.
    "tablaco": "client engagement — client retains all private rights",
    "tablaco-v2": "client engagement — client retains all private rights",
    # Test fixture (box.py + box.step), not a Bounded 4D Hyperobject. Since
    # RFC 0038 P2 it is vendored under apps/api/tests/fixtures/cartridges/ and
    # is not under a cartridge root at all, so this entry is belt-and-braces:
    # it keeps the exclusion explicit if the fixture is ever mounted as one.
    "cq-hyperobject-test": "engine test fixture, not a Commons object; repo archived",
}
CLIENT_PRIVATE = set(NOT_COMMONS)

# Cartridges with a KNOWN, documented NonCommercial exposure: files vendored
# from an NC-licensed upstream inside an otherwise commercially-usable
# cartridge. The catalogue must not present such a cartridge as cleanly
# commercial, so its entry carries a `license_exposure` field with this text.
# Kept in step with KNOWN_NC_EXPOSURE in scripts/qa/check_licenses.py.
KNOWN_NC_EXPOSURE: dict[str, str] = {
    # Empty since 2026-09-05: the last acknowledgement (rugged-box, which
    # vendored the CC BY-NC-SA 4.0 "Super Customizable Rugged Box in OpenSCAD"
    # source) was removed when the slug returned as a clean-room re-creation
    # under ADR-021 — the new cartridge is an original MADFAM work licensed
    # CERN-OHL-W-2.0 and vendors nothing, so the exposure no longer exists and
    # keeping the row would have mislabelled a clean cartridge in the
    # catalogue. See projects/rugged-box/NOTICE.
    #
    # Add a row here the moment any cartridge vendors NC-licensed upstream
    # files again; entries whose cartridge is absent are reported as STALE by
    # check_licenses.py rather than dropped silently.
}


def clone_instructions(slug: str) -> dict[str, str]:
    """How to obtain just this cartridge.

    One answer for every cartridge since RFC 0038 P2: they all live at the root
    of the commons repo. Before P2 this returned `kind: "submodule"` with a
    per-cartridge repo URL for the 34 satellite repos and `kind: "sparse"` for
    the rest; those satellites are absorbed and archived, so the distinction is
    gone and `kind` is always `"sparse"`.
    """
    return {
        "kind": "sparse",
        "command": (
            f"git clone --filter=blob:none --sparse {COMMONS_REPO} && "
            f"cd solid-hyperobjects && git sparse-checkout set {slug}"
        ),
    }


def _len(value) -> int:
    return len(value) if isinstance(value, (list, dict)) else 0


def _modes(manifest: dict) -> list[dict]:
    modes = manifest.get("modes") or []
    if isinstance(modes, dict):
        modes = list(modes.values())
    return [m for m in modes if isinstance(m, dict)]


def _engine_support(manifest: dict, directory: Path) -> tuple[list[str], bool]:
    """Resolve which kernels a cartridge can render on, and whether it is dual-engine.

    Engine is resolved per mode (mirroring ManifestService.mode_engine), so the
    authoritative signal is which source files each mode declares — not the
    presence of a top-level main.py.

    CQ-only cartridges declare `scad_file` pointing at their .py source as a
    placeholder, so a declared scad_file alone proves nothing. Each mode's
    kernel is therefore resolved from the source that actually exists on disk,
    mirroring apps/api/tests/scripts/geometric_regression.py.

    "Dual-engine" is a cartridge-level property, per README: exact CadQuery
    B-Rep modes shipping *alongside* the original OpenSCAD modes. The two
    kernels need not appear on the same mode.
    """
    modes = _modes(manifest)
    project_engine = (manifest.get("project") or {}).get("engine")

    engines: set[str] = set()
    for mode in modes:
        scad_file = mode.get("scad_file") or ""
        cq_file = mode.get("cq_file") or (
            scad_file.replace(".scad", ".py") if scad_file.endswith(".scad") else ""
        )
        real_scad = scad_file.endswith(".scad") and (directory / scad_file).exists()
        real_cq = bool(cq_file) and cq_file.endswith(".py") and (directory / cq_file).exists()

        if real_scad:
            engines.add("openscad")
        if real_cq:
            engines.add("cadquery")
        # An explicit per-mode engine only counts if that mode has real source.
        if mode.get("engine") and (real_scad or real_cq):
            engines.add(mode["engine"])

    if project_engine:
        engines.add(project_engine)
    dual = {"openscad", "cadquery"} <= engines
    # A cartridge with no declared engine anywhere renders on the OpenSCAD default.
    return sorted(engines) or ["openscad"], dual


def build_entry(manifest_path: Path) -> dict:
    slug = manifest_path.parent.name
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    project = m.get("project") or {}
    hyper = m.get("hyperobject") if isinstance(m.get("hyperobject"), dict) else {}

    # Two conventions are in use: Commons cartridges declare
    # hyperobject.commons_license, while several standalone cartridge repos
    # declare project.license. Read both rather than reporting a licensed
    # cartridge as unlicensed because it picked the other field.
    commons_license = hyper.get("commons_license") or project.get("license") or m.get("license")

    interfaces = []
    for iface in hyper.get("cdg_interfaces") or []:
        if not isinstance(iface, dict):
            continue
        label = iface.get("label")
        if isinstance(label, dict):
            label = label.get("en") or next(iter(label.values()), None)
        interfaces.append({
            "id": iface.get("id"),
            "label": label,
            "geometry_type": iface.get("geometry_type"),
            "standard": iface.get("standard"),
            "parameters": iface.get("parameters") or [],
        })

    directory = manifest_path.parent
    engines, dual_engine = _engine_support(m, directory)
    return {
        "slug": slug,
        "name": project.get("name") or slug,
        "domain": hyper.get("domain"),
        "engines": engines,
        "dual_engine": dual_engine,
        "modes": _len(m.get("modes")),
        "parts": _len(m.get("parts")),
        "parameters": _len(m.get("parameters")),
        # The parameter ids themselves — the contract surface a downstream
        # consumer (e.g. a Fashion Cabinet hardware_ref params_map) resolves
        # against. `parameters` stays a count for backward compatibility.
        "parameter_ids": [
            p["id"] for p in (m.get("parameters") or [])
            if isinstance(p, dict) and isinstance(p.get("id"), str)
        ],
        "export_formats": m.get("export_formats") or [],
        "commons_license": commons_license,
        # Documented NC exposure from vendored upstream files, if any.
        **({"license_exposure": KNOWN_NC_EXPOSURE[slug]}
           if slug in KNOWN_NC_EXPOSURE else {}),
        "societal_benefit": hyper.get("societal_benefit"),
        "material_awareness": hyper.get("material_awareness"),
        "cdg_interfaces": interfaces,
        "standards": sorted({
            i["standard"] for i in interfaces
            if i.get("standard") and i["standard"] != "internal"
        }),
        "source": {
            # Path within the commons repo (COMMONS_REPO), which the platform
            # mounts at `projects/` — so this is also the platform path.
            "repo": COMMONS_REPO,
            "manifest": f"{slug}/project.json",
            "has_cadquery": "cadquery" in engines,
            "has_openscad": "openscad" in engines,
        },
        "clone": clone_instructions(slug),
    }


def build_catalog() -> dict:
    entries = [
        build_entry(p)
        for p in sorted(PROJECTS.glob("*/project.json"))
        if p.parent.name not in CLIENT_PRIVATE
    ]
    domains: dict[str, int] = {}
    standards: set[str] = set()
    for e in entries:
        domains[e["domain"] or "uncategorized"] = domains.get(e["domain"] or "uncategorized", 0) + 1
        standards.update(e["standards"])
    return {
        "schema_version": SCHEMA_VERSION,
        "upstream": UPSTREAM,
        "counts": {
            "cartridges": len(entries),
            "with_cdg_interfaces": sum(1 for e in entries if e["cdg_interfaces"]),
            "with_commons_license": sum(1 for e in entries if e["commons_license"]),
            "dual_engine": sum(1 for e in entries if e["dual_engine"]),
        },
        "domains": dict(sorted(domains.items(), key=lambda kv: (-kv[1], kv[0]))),
        "standards": sorted(standards),
        "cartridges": entries,
    }


def render_markdown(catalog: dict) -> str:
    c = catalog["counts"]
    lines = [
        "# The Hyperobjects Commons",
        "",
        "> Generated by `scripts/qa/generate_commons_catalog.py`. Do not edit by hand.",
        "",
        (f"**{c['cartridges']} cartridges** · "
        f"{c['with_cdg_interfaces']} with declared CDG interfaces · "
        f"{c['with_commons_license']} licensed · "
        f"{c['dual_engine']} dual-engine (CadQuery B-Rep + OpenSCAD CSG)"),
        "",
        ("The machine-readable form, including per-object CDG interfaces, standards, "
        "and clone instructions, is [`docs/commons-catalog.json`](docs/commons-catalog.json)."),
        "",
        ("*A hyperobject here is never the thing on your desk — it is the family the "
        "thing regenerates into. On the word, its philosophy (Morton, 2013), and its "
        "hypertext lineage: [Why \"Hyperobjects\"](docs/strategy/MANIFESTO.md#on-the-word-why-hyperobjects).*"),
        "",
    ]
    if any(e.get("license_exposure") for e in catalog["cartridges"]):
        lines += [
            ("† Carries vendored upstream files under a NonCommercial license, so "
             "commercial use is constrained by those files' terms despite the "
             "cartridge's own license — see the cartridge's `NOTICE` and the "
             "`license_exposure` field in the JSON catalog."),
            "",
        ]
    lines += [
        "## Standards referenced",
        "",
        ", ".join(f"`{s}`" for s in catalog["standards"]) or "_none declared_",
        "",
    ]
    by_domain: dict[str, list[dict]] = {}
    for e in catalog["cartridges"]:
        by_domain.setdefault(e["domain"] or "uncategorized", []).append(e)

    for domain in sorted(by_domain, key=lambda d: (-len(by_domain[d]), d)):
        entries = sorted(by_domain[domain], key=lambda e: e["slug"])
        lines += [f"## {domain} ({len(entries)})", "",
                  "| Cartridge | Engines | Modes | CDG interfaces | License |",
                  "| :-- | :-- | --: | :-- | :-- |"]
        for e in entries:
            ifaces = ", ".join(
                f"{i['geometry_type']}"
                for i in e["cdg_interfaces"] if i.get("geometry_type")
            ) or "—"
            license_cell = e["commons_license"] or "—"
            if e.get("license_exposure"):
                license_cell += " †"
            lines.append(
                f"| [`{e['slug']}`](projects/{e['slug']}/) | {'/'.join(e['engines'])} | "
                f"{e['modes']} | {ifaces} | {license_cell} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"



def render_readme(catalog: dict, current: str) -> str:
    """Refresh README's counts block in place.

    The README states these figures are generated rather than hand-maintained.
    They were not: it claimed 324 cartridges in one paragraph and 326 in
    another. Now the claim is true, and drift is caught by --check.
    """
    counts = catalog["counts"]
    licenses: dict[str, int] = {}
    for entry in catalog["cartridges"]:
        licenses[entry.get("commons_license") or "unlicensed"] = (
            licenses.get(entry.get("commons_license") or "unlicensed", 0) + 1
        )
    cern = sum(n for lic, n in licenses.items() if lic.startswith("CERN-OHL"))
    total = counts["cartridges"]

    block = "\n".join([
        README_BEGIN,
        "",
        "| | |",
        "| :-- | --: |",
        f"| Cartridges | {total} |",
        f"| With declared CDG interfaces | {counts['with_cdg_interfaces']} |",
        f"| Carrying an explicit license | {counts['with_commons_license']} |",
        f"| Dual-engine (CadQuery B-Rep + OpenSCAD CSG) | {counts['dual_engine']} |",
        f"| Distinct external standards referenced | {len(catalog.get('standards', []))} |",
        f"| Licensed CERN-OHL-W-2.0 | {cern} of {total} |",
        "",
        README_END,
    ])

    if README_BEGIN not in current or README_END not in current:
        return current
    head, _, rest = current.partition(README_BEGIN)
    _, _, tail = rest.partition(README_END)
    return head + block + tail


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the Hyperobjects Commons catalog")
    ap.add_argument("--check", action="store_true",
                    help="fail if committed artifacts differ from freshly generated ones")
    args = ap.parse_args()

    catalog = build_catalog()
    if not catalog["cartridges"]:
        print("ERROR: no cartridges found under projects/ — refusing to write an empty catalog")
        return 1

    payload = json.dumps(catalog, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    markdown = render_markdown(catalog)

    if args.check:
        stale = []
        readme_current = README_MD.read_text(encoding="utf-8") if README_MD.exists() else ""
        readme_fresh = render_readme(catalog, readme_current)
        for path, fresh in ((CATALOG_JSON, payload), (CATALOG_MD, markdown), (README_MD, readme_fresh)):
            current = path.read_text(encoding="utf-8") if path.exists() else None
            if current != fresh:
                stale.append(path.relative_to(REPO))
        if stale:
            print("ERROR: commons catalog is stale: " + ", ".join(str(p) for p in stale))
            print("Regenerate with: python3 scripts/qa/generate_commons_catalog.py")
            return 1
        print(f"Commons catalog up to date ({catalog['counts']['cartridges']} cartridges)")
        return 0

    CATALOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_JSON.write_text(payload, encoding="utf-8")
    CATALOG_MD.write_text(markdown, encoding="utf-8")
    if README_MD.exists():
        README_MD.write_text(render_readme(catalog, README_MD.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"Wrote {CATALOG_JSON.relative_to(REPO)} and {CATALOG_MD.relative_to(REPO)} "
          f"({catalog['counts']['cartridges']} cartridges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
