#!/usr/bin/env python3
"""Generate docs/README.md for each project from its project.json manifest."""

import json
import sys
from pathlib import Path

PROJECTS_DIR = Path(__file__).resolve().parent.parent / "projects"


def get_label(obj, key="label", lang="en"):
    """Extract label from i18n object or plain string."""
    val = obj.get(key, obj.get("id", ""))
    if isinstance(val, dict):
        return val.get(lang, val.get("en", val.get("es", "")))
    return str(val)


def fmt_value(v):
    """Format a value for display."""
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


def generate_doc(manifest, slug):
    """Generate markdown documentation from a project manifest."""
    project = manifest.get("project", {})
    lines = []

    # Title and description
    name = project.get("name", slug)
    lines.append(f"# {name}")
    lines.append("")
    desc = project.get("description", "")
    if isinstance(desc, dict):
        desc_en = desc.get("en", desc.get("es", ""))
        desc_es = desc.get("es", "")
        lines.append(f"{desc_en}")
        if desc_es and desc_es != desc_en:
            lines.append(f"")
            lines.append(f"*{desc_es}*")
    elif desc:
        lines.append(desc)
    lines.append("")

    # Metadata
    version = project.get("version", "")
    if version:
        lines.append(f"**Version**: {version}  ")
    lines.append(f"**Slug**: `{slug}`")
    lines.append("")

    # Modes
    modes = manifest.get("modes", [])
    if modes:
        lines.append("## Modes")
        lines.append("")
        lines.append("| ID | Label | SCAD File | Parts |")
        lines.append("|---|---|---|---|")
        for m in modes:
            mid = m.get("id", "")
            label = get_label(m)
            scad = m.get("scad_file", "")
            parts = ", ".join(m.get("parts", []))
            lines.append(f"| `{mid}` | {label} | `{scad}` | {parts} |")
        lines.append("")

    # Parameters
    params = manifest.get("parameters", [])
    if params:
        lines.append("## Parameters")
        lines.append("")
        lines.append("| Name | Type | Default | Range | Description |")
        lines.append("|---|---|---|---|---|")
        for p in params:
            pid = p.get("id", "")
            label = get_label(p)
            ptype = p.get("type", "")
            default = fmt_value(p.get("default", ""))
            pmin = p.get("min", "")
            pmax = p.get("max", "")
            step = p.get("step", "")
            rng = ""
            if pmin != "" and pmax != "":
                rng = f"{pmin}–{pmax}"
                if step and step != 1:
                    rng += f" (step {step})"
            tooltip = get_label(p, "tooltip")
            lines.append(f"| `{pid}` | {ptype} | {default} | {rng} | {tooltip or label} |")
        lines.append("")

    # Presets
    presets = manifest.get("presets", [])
    if presets:
        lines.append("## Presets")
        lines.append("")
        for preset in presets:
            label = get_label(preset)
            lines.append(f"- **{label}**")
            values = preset.get("values", {})
            if values:
                kv = ", ".join(f"`{k}`={fmt_value(v)}" for k, v in values.items())
                lines.append(f"  {kv}")
        lines.append("")

    # Parts
    parts = manifest.get("parts", [])
    if parts:
        lines.append("## Parts")
        lines.append("")
        lines.append("| ID | Label | Default Color |")
        lines.append("|---|---|---|")
        for part in parts:
            pid = part.get("id", "")
            label = get_label(part)
            color = part.get("default_color", "")
            lines.append(f"| `{pid}` | {label} | `{color}` |")
        lines.append("")

    # Constraints
    constraints = manifest.get("constraints", [])
    if constraints:
        lines.append("## Constraints")
        lines.append("")
        for c in constraints:
            rule = c.get("rule", "")
            msg = c.get("message", "")
            if isinstance(msg, dict):
                msg = msg.get("en", msg.get("es", ""))
            severity = c.get("severity", "warning")
            lines.append(f"- `{rule}` — {msg} ({severity})")
        lines.append("")

    # Assembly steps
    assembly = manifest.get("assembly_steps", [])
    if assembly:
        lines.append("## Assembly Steps")
        lines.append("")
        for step in assembly:
            snum = step.get("step", "")
            label = get_label(step)
            notes = step.get("notes", "")
            if isinstance(notes, dict):
                notes = notes.get("en", notes.get("es", ""))
            hw = step.get("hardware", [])
            lines.append(f"{snum}. **{label}**")
            if notes:
                lines.append(f"   {notes}")
            if hw:
                lines.append(f"   Hardware: {', '.join(hw)}")
        lines.append("")

    # BOM
    bom = manifest.get("bom", {})
    if isinstance(bom, list):
        hardware = bom
    else:
        hardware = bom.get("hardware", [])
    if hardware:
        lines.append("## Bill of Materials")
        lines.append("")
        lines.append("| Item | Quantity | Unit |")
        lines.append("|---|---|---|")
        for h in hardware:
            label = get_label(h)
            qty = h.get("quantity_formula", "")
            unit = h.get("unit", "")
            lines.append(f"| {label} | {qty} | {unit} |")
        lines.append("")

    # Estimate constants
    est = manifest.get("estimate_constants", {})
    if est:
        lines.append("## Render Estimates")
        lines.append("")
        for k, v in est.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Auto-generated from `project.json` by `scripts/generate-project-docs.py`*")
    lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate project docs from manifests")
    parser.add_argument("--slug", help="Generate docs for a single project")
    parser.add_argument("--dry-run", action="store_true", help="Print output without writing files")
    parser.add_argument("--force", action="store_true", help="Include tablaco (skipped by default)")
    args = parser.parse_args()

    if not PROJECTS_DIR.is_dir():
        print(f"Projects directory not found: {PROJECTS_DIR}", file=sys.stderr)
        sys.exit(1)

    slugs = [args.slug] if args.slug else sorted(
        d.name for d in PROJECTS_DIR.iterdir()
        if d.is_dir() and (d / "project.json").exists()
    )

    generated = 0
    for slug in slugs:
        if slug == "tablaco" and not args.force:
            print(f"  skip  {slug} (has manual docs; use --force to override)")
            continue

        manifest_path = PROJECTS_DIR / slug / "project.json"
        if not manifest_path.exists():
            print(f"  skip  {slug} (no project.json)")
            continue

        with open(manifest_path) as f:
            manifest = json.load(f)

        doc = generate_doc(manifest, slug)

        if args.dry_run:
            print(f"--- {slug} ---")
            print(doc[:500])
            print("...")
        else:
            docs_dir = PROJECTS_DIR / slug / "docs"
            docs_dir.mkdir(exist_ok=True)
            out_path = docs_dir / "README.md"
            out_path.write_text(doc)
            print(f"  wrote {out_path.relative_to(PROJECTS_DIR.parent)}")

        generated += 1

    print(f"\nGenerated {generated} project doc(s)")


if __name__ == "__main__":
    main()
