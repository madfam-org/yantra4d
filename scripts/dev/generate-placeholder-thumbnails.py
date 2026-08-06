#!/usr/bin/env python3
"""Generate deterministic SVG placeholder thumbnails for every hyperobject.

The real thumbnail pipeline renders a live WebGL preview per object (see
`generate-thumbnails.js`, which drives the Studio 3D viewer with Playwright and
needs a GPU). That is unavailable in headless/sandbox environments and slow to run
for hundreds of objects, so this script produces an attractive, intentional-looking
*placeholder* per object immediately: a domain-tinted gradient tile with a
geometry-type glyph and a slug-seeded procedural accent. Every tile is distinct and
stable (same object → same art across runs), so the gallery never shows broken images.

Placeholders are written as `<slug>.svg` (NOT `.webp`) into the studio public dir.
The catalog's default thumbnail path is `/projects/<slug>.webp`; a companion step
writes a per-object `thumbnail` override into the manifest is NOT done here to avoid
churning 251 manifests — instead the frontend resolves `/projects/<slug>.svg` when the
`.webp` 404s (graceful onError fallback). Run with `--emit-webp-names` to instead write
files named `<slug>.webp` containing SVG (browsers render by sniffing content), matching
the catalog default path directly.

Usage:
    .venv/bin/python scripts/dev/generate-placeholder-thumbnails.py
    .venv/bin/python scripts/dev/generate-placeholder-thumbnails.py --out apps/landing/public/projects
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Domain → (base hue pair for the gradient) as HSL. Chosen for good dark+light contrast.
DOMAIN_PALETTE: dict[str, tuple[int, int]] = {
    "household":      (200, 175),   # teal → cyan
    "industrial":     (24, 40),     # orange → amber (machined metal)
    "commercial":     (265, 290),   # violet → magenta
    "medical":        (155, 185),   # green → teal (clinical)
    "infrastructure": (210, 230),   # blue → indigo
    "hybrid":         (330, 300),   # pink → purple
    "soft-robotics":  (100, 140),   # lime → green
    "":               (220, 240),   # neutral slate for unclassified
}

# geometry_type → a simple, legible SVG glyph path/shape rendered centered.
# Each returns SVG markup for a ~140x140 icon centered at (200,190) on a 400x300 canvas.
def _glyph(geometry_type: str, stroke: str) -> str:
    cx, cy = 200, 172
    s = stroke
    g = {
        "bolt_pattern": f'''
            <circle cx="{cx-55}" cy="{cy-55}" r="13" fill="none" stroke="{s}" stroke-width="7"/>
            <circle cx="{cx+55}" cy="{cy-55}" r="13" fill="none" stroke="{s}" stroke-width="7"/>
            <circle cx="{cx-55}" cy="{cy+55}" r="13" fill="none" stroke="{s}" stroke-width="7"/>
            <circle cx="{cx+55}" cy="{cy+55}" r="13" fill="none" stroke="{s}" stroke-width="7"/>
            <rect x="{cx-78}" y="{cy-78}" width="156" height="156" rx="14" fill="none" stroke="{s}" stroke-width="5" opacity="0.5"/>''',
        "profile": f'''
            <path d="M {cx-80} {cy+60} L {cx-80} {cy-20} L {cx-30} {cy-20} L {cx-30} {cy-60}
                     L {cx+30} {cy-60} L {cx+30} {cy-20} L {cx+80} {cy-20} L {cx+80} {cy+60} Z"
                  fill="none" stroke="{s}" stroke-width="7" stroke-linejoin="round"/>''',
        "socket": f'''
            <circle cx="{cx}" cy="{cy}" r="72" fill="none" stroke="{s}" stroke-width="7"/>
            <circle cx="{cx}" cy="{cy}" r="38" fill="none" stroke="{s}" stroke-width="7" opacity="0.7"/>''',
        "snap": f'''
            <path d="M {cx-70} {cy-40} L {cx-70} {cy+40} L {cx+30} {cy+40} L {cx+30} {cy+18}
                     L {cx+70} {cy+18} L {cx+70} {cy-18} L {cx+30} {cy-18} L {cx+30} {cy-40} Z"
                  fill="none" stroke="{s}" stroke-width="7" stroke-linejoin="round"/>''',
        "grid": f'''
            <g fill="none" stroke="{s}" stroke-width="6">
              <rect x="{cx-72}" y="{cy-72}" width="48" height="48" rx="6"/>
              <rect x="{cx-12}" y="{cy-72}" width="48" height="48" rx="6"/>
              <rect x="{cx+36}" y="{cy-72}" width="36" height="48" rx="6" opacity="0.6"/>
              <rect x="{cx-72}" y="{cy-12}" width="48" height="48" rx="6"/>
              <rect x="{cx-12}" y="{cy-12}" width="48" height="48" rx="6"/>
              <rect x="{cx+36}" y="{cy-12}" width="36" height="48" rx="6" opacity="0.6"/>
            </g>''',
        "pocket": f'''
            <rect x="{cx-78}" y="{cy-58}" width="156" height="116" rx="12" fill="none" stroke="{s}" stroke-width="7"/>
            <rect x="{cx-48}" y="{cy-28}" width="96" height="56" rx="8" fill="{s}" opacity="0.22"/>''',
        "thread": f'''
            <g fill="none" stroke="{s}" stroke-width="7">
              <path d="M {cx-60} {cy-56} H {cx+60}"/>
              <path d="M {cx-60} {cy-28} H {cx+60}"/>
              <path d="M {cx-60} {cy} H {cx+60}"/>
              <path d="M {cx-60} {cy+28} H {cx+60}"/>
              <path d="M {cx-60} {cy+56} H {cx+60}"/>
              <path d="M {cx-72} {cy-70} L {cx+72} {cy+70}" opacity="0.35"/>
            </g>''',
        "surface": f'''
            <path d="M {cx-80} {cy+30} C {cx-40} {cy-40}, {cx+40} {cy-40}, {cx+80} {cy+30}"
                  fill="none" stroke="{s}" stroke-width="7"/>
            <path d="M {cx-80} {cy+58} C {cx-40} {cy-12}, {cx+40} {cy-12}, {cx+80} {cy+58}"
                  fill="none" stroke="{s}" stroke-width="7" opacity="0.55"/>''',
        "rail": f'''
            <rect x="{cx-30} " y="{cy-78}" width="60" height="156" rx="8" fill="none" stroke="{s}" stroke-width="7"/>
            <path d="M {cx-30} {cy-40} H {cx+30} M {cx-30} {cy} H {cx+30} M {cx-30} {cy+40} H {cx+30}"
                  stroke="{s}" stroke-width="5" opacity="0.6"/>''',
        "spline": f'''
            <path d="M {cx-80} {cy+50} C {cx-30} {cy-70}, {cx+30} {cy+70}, {cx+80} {cy-50}"
                  fill="none" stroke="{s}" stroke-width="7"/>''',
        "custom": f'''
            <path d="M {cx} {cy-72} L {cx+62} {cy-36} L {cx+62} {cy+36} L {cx} {cy+72}
                     L {cx-62} {cy+36} L {cx-62} {cy-36} Z" fill="none" stroke="{s}" stroke-width="7" stroke-linejoin="round"/>''',
    }
    return g.get(geometry_type, g["custom"])


def _seed(slug: str) -> int:
    return int(hashlib.sha1(slug.encode()).hexdigest()[:8], 16)


def build_svg(slug: str, name: str, domain: str, geometry_type: str) -> str:
    h1, h2 = DOMAIN_PALETTE.get(domain, DOMAIN_PALETTE[""])
    seed = _seed(slug)
    # slug-seeded rotation + a scattering of faint accent dots → each tile unique
    rot = seed % 360
    dots = ""
    r = seed
    for _ in range(5):
        r = (r * 1103515245 + 12345) & 0x7FFFFFFF
        dx = 30 + (r % 340)
        r = (r * 1103515245 + 12345) & 0x7FFFFFFF
        dy = 20 + (r % 260)
        r = (r * 1103515245 + 12345) & 0x7FFFFFFF
        rad = 3 + (r % 6)
        dots += f'<circle cx="{dx}" cy="{dy}" r="{rad}" fill="#fff" opacity="0.06"/>'
    initial = (name or slug or "?").strip()[:1].upper()
    # unique gradient ids so tiles stay correct even if several are inlined in one DOM
    uid = f"{seed:08x}"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300" width="400" height="300" role="img" aria-label="{_esc(name)} placeholder">
  <defs>
    <linearGradient id="bg{uid}" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="hsl({h1},58%,42%)"/>
      <stop offset="1" stop-color="hsl({h2},64%,32%)"/>
    </linearGradient>
    <radialGradient id="vig{uid}" cx="0.5" cy="0.42" r="0.75">
      <stop offset="0.55" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity="0.28"/>
    </radialGradient>
  </defs>
  <rect width="400" height="300" fill="url(#bg{uid})"/>
  <g transform="rotate({rot} 200 150)" opacity="0.9">{dots}</g>
  <g opacity="0.95">{_glyph(geometry_type, "#ffffff")}</g>
  <rect width="400" height="300" fill="url(#vig{uid})"/>
  <text x="24" y="272" font-family="ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif"
        font-size="20" font-weight="700" fill="#fff" opacity="0.92">{_esc(_truncate(name or slug, 26))}</text>
  <text x="376" y="40" text-anchor="end" font-family="ui-monospace,SFMono-Regular,Menlo,monospace"
        font-size="15" fill="#fff" opacity="0.6">{_esc(geometry_type or "object")}</text>
  <text x="24" y="44" font-family="ui-sans-serif,system-ui,sans-serif" font-size="30" font-weight="800"
        fill="#fff" opacity="0.85">{_esc(initial)}</text>
</svg>'''


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _truncate(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


def _i18n_name(proj: dict, slug: str) -> str:
    name = proj.get("name", slug)
    if isinstance(name, dict):
        return name.get("en") or next(iter(name.values()), slug)
    return name or slug


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="apps/studio/public/projects",
                    help="output dir (repo-relative)")
    ap.add_argument("--projects", default="projects",
                    help="cartridges dir (repo-relative)")
    ap.add_argument("--ext", default="svg", choices=["svg", "webp"],
                    help="file extension. 'webp' writes SVG content under .webp names to match the catalog default path.")
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    args = ap.parse_args()

    out = (REPO / args.out)
    out.mkdir(parents=True, exist_ok=True)
    pdir = REPO / args.projects

    written = skipped = 0
    for pj in sorted(glob.glob(str(pdir / "*" / "project.json"))):
        try:
            data = json.load(open(pj, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        proj = data.get("project", {}) or {}
        ho = data.get("hyperobject", {}) or proj.get("hyperobject", {}) or {}
        slug = proj.get("slug") or os.path.basename(os.path.dirname(pj))
        domain = ho.get("domain", "")
        cdg = ho.get("cdg_interfaces", []) or []
        gtypes = sorted({c.get("geometry_type") for c in cdg if c.get("geometry_type")})
        geometry_type = gtypes[0] if gtypes else ""
        name = _i18n_name(proj, slug)

        target = out / f"{slug}.{args.ext}"
        if target.exists() and not args.force:
            skipped += 1
            continue
        target.write_text(build_svg(slug, name, domain, geometry_type), encoding="utf-8")
        written += 1

    print(f"placeholders → {out}: wrote {written}, skipped {skipped} (existing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
