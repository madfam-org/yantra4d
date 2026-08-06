"""Catalog index — a cached, faceted, searchable view over all project manifests.

The legacy discovery path (`discover_projects` + `_enrich_project`) re-scans and
re-parses every `project.json` on every request with no caching, and exposes only a
handful of fields. That does not scale past a few hundred projects.

This module builds a compact **catalog record** per project ONCE, memoized behind a
directory-mtime signature, and exposes fast in-process search + faceting over it. Each
record carries exactly the fields the discovery UI needs — including the rich
`hyperobject` facet data (domain, CDG geometry types, engineering standards) that the
manifests already contain but nothing surfaces today.

Public API:
    get_catalog()                      -> {"records": [...], "facets": {...}, "count": N, "generated_ms": ...}
    search_catalog(**filters)          -> {"results": [...], "total": N, "facets": {...}, ...}
    invalidate_catalog()               -> clears the cache (call after a project changes)

Everything is pure-Python and filesystem-only; no DB required.
"""
from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from config import Config

logger = logging.getLogger(__name__)

# ── module-level cache ────────────────────────────────────────────────────────
_cache: dict[str, Any] | None = None
_cache_sig: tuple | None = None


def _i18n(value: Any, lang: str = "en") -> str:
    """Collapse an i18n string ({en,es} or str) to one language, falling back to en."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or next(iter(value.values()), "")
    return value or ""


def _dir_signature() -> tuple:
    """A cheap signature of the projects tree: (dir, count, max child mtime) per root.

    Rebuilds the index only when a project is added/removed/modified — a stat walk,
    not a JSON-parse walk, so it stays fast even at thousands of projects.
    """
    sig = []
    for directory in Config.CARTRIDGES_DIRS:
        if not directory.is_dir():
            continue
        latest = 0.0
        count = 0
        try:
            for child in os.scandir(directory):
                if not child.is_dir():
                    continue
                pj = os.path.join(child.path, "project.json")
                try:
                    st = os.stat(pj)
                except OSError:
                    continue
                count += 1
                latest = max(latest, st.st_mtime)
        except OSError:
            continue
        sig.append((str(directory), count, round(latest, 3)))
    return tuple(sig)


# Boolean material-awareness capability flags a manifest may declare, in the
# order we surface them. `notes` is free i18n text, not a capability, so it is
# deliberately excluded from the facet.
_MATERIAL_CAPABILITY_FLAGS = (
    "tolerance_by_material",
    "shrinkage_compensation",
    "recycled_material_toggle",
)


def _material_signal(material_awareness: Any) -> tuple[bool, list[str]]:
    """Reduce a `material_awareness` block to (aware?, [capability flags that are true]).

    The block is a dict of boolean capability flags (plus an optional i18n `notes`
    string). `material_aware` is true when a non-empty block is present at all;
    `capabilities` lists the flag names set to true, lowercased, in a stable order —
    exactly the values the `material` facet counts and filters on.
    """
    if not isinstance(material_awareness, dict) or not material_awareness:
        return False, []
    caps = [flag for flag in _MATERIAL_CAPABILITY_FLAGS if material_awareness.get(flag) is True]
    return True, caps


def _build_record(slug: str, data: dict, mtime: float) -> dict:
    """Extract one compact, discovery-ready catalog record from a raw manifest."""
    proj = data.get("project", {}) or {}
    # hyperobject block may live at top level or (legacy) under project
    ho = data.get("hyperobject", {}) or proj.get("hyperobject", {}) or {}

    cdg = ho.get("cdg_interfaces", []) or []
    geometry_types = sorted({c.get("geometry_type") for c in cdg if c.get("geometry_type")})
    standards = sorted({
        c["standard"] for c in cdg
        if c.get("standard") and c["standard"] != "internal"
    })

    tags = [t for t in (proj.get("tags") or []) if isinstance(t, str)]
    modes = data.get("modes", []) or []
    parts = data.get("parts", []) or []

    # Material hyper-awareness. In the manifests this is a block of boolean
    # capability flags (e.g. tolerance_by_material / shrinkage_compensation /
    # recycled_material_toggle) — how the object adapts its geometry to the
    # material it's printed in — plus an optional i18n `notes` string. It is NOT
    # a list of named materials, so we surface the *capabilities* an object
    # declares as a compact, lowercase, discovery-ready signal.
    material_aware, material_capabilities = _material_signal(ho.get("material_awareness"))

    name_en = _i18n(proj.get("name", slug))
    desc_en = _i18n(proj.get("description", "")).split("\n")[0]

    # a lightweight lowercase haystack for substring/keyword search
    haystack = " ".join([
        slug, name_en, desc_en,
        " ".join(tags), " ".join(standards), " ".join(geometry_types),
        " ".join(material_capabilities),
        ho.get("domain", ""),
    ]).lower()

    return {
        "slug": slug,
        "name": name_en,
        "name_i18n": proj.get("name") if isinstance(proj.get("name"), dict) else {"en": name_en},
        "description": desc_en,
        "engine": proj.get("engine", "openscad"),
        "difficulty": proj.get("difficulty", "beginner"),
        "domain": ho.get("domain") or "",
        "is_hyperobject": bool(ho.get("is_hyperobject") or proj.get("hyperobject", {}).get("is_hyperobject")),
        "dual_engine": proj.get("engine") == "cadquery" and any(m.get("engine") == "openscad" for m in modes),
        "tags": tags,
        "geometry_types": geometry_types,   # CDG "connects via"
        "standards": standards,             # real-world interoperability ("compatible with X")
        "material_aware": material_aware,   # declares any material-awareness at all
        "material_capabilities": material_capabilities,  # which flags ("adapts to material" facet)
        "mode_count": len(modes),
        "part_count": len(parts),
        # Prefer an explicit manifest thumbnail; otherwise the generated placeholder
        # tile (an SVG written per-object by scripts/dev/generate-placeholder-thumbnails.py).
        # The real WebGL thumbnail pipeline writes `/projects/<slug>.webp`; when that
        # exists the frontend uses it and the .svg is the graceful fallback.
        "thumbnail": proj.get("thumbnail") or f"/projects/{slug}.svg",
        "modified_ms": int(mtime * 1000),
        "unlisted": bool(proj.get("unlisted", False)),
        "_haystack": haystack,
    }


def _build_catalog() -> dict:
    """Parse every manifest once and assemble records + facet counts."""
    t0 = time.perf_counter()
    records: list[dict] = []
    for directory in Config.CARTRIDGES_DIRS:
        if not directory.is_dir():
            continue
        for child in sorted(os.scandir(directory), key=lambda e: e.name):
            if not child.is_dir():
                continue
            pj = os.path.join(child.path, "project.json")
            try:
                st = os.stat(pj)
                with open(pj, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            slug = (data.get("project", {}) or {}).get("slug", child.name)
            try:
                records.append(_build_record(slug, data, st.st_mtime))
            except Exception:
                logger.warning("catalog: skipping malformed manifest at %s", pj)

    facets = _compute_facets(records)
    return {
        "records": records,
        "facets": facets,
        "count": len(records),
        "generated_ms": int(round(time.perf_counter() - t0, 4) * 1000),
    }


def _compute_facets(records: list[dict]) -> dict:
    """Value → count maps for each facet dimension (listed projects only)."""
    from collections import Counter
    listed = [r for r in records if not r["unlisted"]]
    domain = Counter(r["domain"] for r in listed if r["domain"])
    difficulty = Counter(r["difficulty"] for r in listed if r["difficulty"])
    engine = Counter(r["engine"] for r in listed)
    geometry = Counter(g for r in listed for g in r["geometry_types"])
    standards = Counter(s for r in listed for s in r["standards"])
    tags = Counter(t for r in listed for t in r["tags"] if t not in ("hyperobject", "commons", "cdg"))
    # Material-awareness capabilities. The block itself is near-universal (~95% of
    # objects declare one), so `material_aware` alone makes a poor facet; the
    # *capabilities* split the corpus meaningfully (tolerance-by-material is common,
    # shrinkage/recycled are the differentiated minority), so those are the chips.
    material = Counter(m for r in listed for m in r["material_capabilities"])

    def top(counter: Counter, n: int | None = None) -> list[dict]:
        items = counter.most_common(n)
        return [{"value": v, "count": c} for v, c in items]

    return {
        "domain": top(domain),
        "difficulty": top(difficulty),
        "engine": top(engine),
        "geometry_type": top(geometry),
        "standard": top(standards, 60),   # 120+ exist; expose the most common as chips
        "material": top(material),
        "tag": top(tags, 40),
    }


def get_catalog(force: bool = False) -> dict:
    """Return the cached catalog, rebuilding only when the projects tree changed."""
    global _cache, _cache_sig
    sig = _dir_signature()
    if force or _cache is None or sig != _cache_sig:
        _cache = _build_catalog()
        _cache_sig = sig
        logger.info("catalog rebuilt: %d records in %dms", _cache["count"], _cache["generated_ms"])
    return _cache


def invalidate_catalog() -> None:
    """Drop the cache so the next get_catalog() rebuilds (call after edits)."""
    global _cache, _cache_sig
    _cache = None
    _cache_sig = None


# ── search ────────────────────────────────────────────────────────────────────
_SORTS = {
    "name": lambda r: r["name"].lower(),
    "recent": lambda r: -r["modified_ms"],
    "complexity": lambda r: (r["mode_count"] + r["part_count"]),
}


def search_catalog(
    q: str = "",
    domain: str | None = None,
    difficulty: str | None = None,
    engine: str | None = None,
    geometry_type: str | None = None,
    standard: str | None = None,
    material: str | None = None,
    material_aware: bool = False,
    tag: str | None = None,
    hyperobject_only: bool = False,
    sort: str = "name",
    limit: int = 60,
    offset: int = 0,
) -> dict:
    """Filter + rank + paginate the catalog. All matching is in-process over the cache.

    Text `q`: whitespace-split, AND semantics (every term must appear in the haystack).
    Facet params are exact-match filters. Returns the page plus post-filter facet counts
    so the UI can show how many results each remaining facet value would yield.
    """
    cat = get_catalog()
    rows = [r for r in cat["records"] if not r["unlisted"]]

    if hyperobject_only:
        rows = [r for r in rows if r["is_hyperobject"]]
    if domain:
        rows = [r for r in rows if r["domain"] == domain]
    if difficulty:
        rows = [r for r in rows if r["difficulty"] == difficulty]
    if engine:
        rows = [r for r in rows if r["engine"] == engine]
    if geometry_type:
        rows = [r for r in rows if geometry_type in r["geometry_types"]]
    if standard:
        rows = [r for r in rows if standard in r["standards"]]
    if material_aware:
        rows = [r for r in rows if r["material_aware"]]
    if material:
        rows = [r for r in rows if material in r["material_capabilities"]]
    if tag:
        rows = [r for r in rows if tag in r["tags"]]

    terms = [t for t in q.lower().split() if t]
    if terms:
        rows = [r for r in rows if all(t in r["_haystack"] for t in terms)]

    facets = _compute_facets(rows)  # facet counts reflect the current filtered set
    total = len(rows)

    keyfn = _SORTS.get(sort, _SORTS["name"])
    rows = sorted(rows, key=keyfn)

    page = rows[offset: offset + limit]
    # strip the internal haystack from the wire payload
    results = [{k: v for k, v in r.items() if k != "_haystack"} for r in page]

    return {
        "results": results,
        "total": total,
        "limit": limit,
        "offset": offset,
        "facets": facets,
        "catalog_count": cat["count"],
    }
