"""Compatibility graph — derive which hyperobjects physically interface, from CDG metadata.

Yantra4D's differentiator is Common Denominator Geometry (CDG): objects designed to
interface via shared real-world standards (NEMA, VESA, DIN-rail, Gridfinity, 1/4-20,
GHT…). Every manifest declares its interfaces (`geometry_type` + `standard`), but the
*graph of what-mates-with-what* was never computed — only ~22 explicit `compatible_with`
links existed across 300 objects. This module DERIVES that graph.

Two objects share an edge when they each expose a CDG interface that:
  1. resolves to the same **standard family** (normalized: "ASME B1.1 1/4-20 UNC" and
     "ASME 1/4-20" both → "1/4-20"), and
  2. has **compatible geometry** — either the same anchoring geometry (bolt_pattern↔
     bolt_pattern, grid↔grid, rail↔rail) or a complementary pair (socket↔profile,
     socket↔thread, thread↔thread) of that same family.

Edge kinds:
  - "same_family"  — both anchor to the same standard the same way (e.g. two VESA plates,
                     two Gridfinity bins): they share an ecosystem / are interchangeable.
  - "mates_with"   — complementary geometries of one family physically join (a socket seats
                     a thread/profile; a bolt_pattern bolts to a bolt_pattern).

Everything is pure-Python over the cached catalog records' raw interface data; no DB.

Public API:
    get_graph(force=False)      -> {"nodes": [...], "edges": [...], "families": {...}, ...}
    works_with(slug)            -> {"slug":..., "partners": [...]}  (edges for one object)
    invalidate_graph()          -> drop the cache (call after projects change)
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import defaultdict
from typing import Any

from config import Config

logger = logging.getLogger(__name__)

_cache: dict[str, Any] | None = None
_cache_sig: tuple | None = None

# ── standard-family normalization ─────────────────────────────────────────────
# Free-text standards get mapped to a canonical family key. Order matters: the first
# pattern that matches wins, so put more-specific families before generic ones.
_FAMILY_PATTERNS: list[tuple[str, str]] = [
    (r"1/4[\s-]?20", "unc-1/4-20"),
    (r"3/8[\s-]?16", "unc-3/8-16"),
    (r"\bvesa\b", "vesa"),
    (r"\bnema\b", "nema-stepper"),
    (r"gridfinity", "gridfinity"),
    (r"multiboard", "multiboard"),
    (r"din\s*(en\s*)?60715|ts35|din\s*rail", "din-rail-35"),
    (r"pco\s*1881", "pco-1881"),
    (r"\bght\b|garden hose", "ght-hose"),
    (r"\bnpt\b", "npt"),
    (r"\bbsp\b", "bsp"),
    (r"arca[\s-]?swiss|arca", "arca-swiss"),
    (r"picatinny|1913", "picatinny"),
    (r"\bnato\b", "nato-rail"),
    (r"\bgopro\b", "gopro-mount"),
    (r"iso\s*518|hot\s*shoe|cold\s*shoe|accessory shoe", "iso-518-shoe"),
    (r"15\s*mm\s*(lws|rod)", "15mm-rod"),
    (r"\bmc4\b", "mc4"),
    (r"e26|e27|edison\s*screw", "e26-e27-lamp"),
    (r"gu10", "gu10-lamp"),
    (r"b22", "b22-lamp"),
    (r"m22\s*x?\s*1|m24\s*x?\s*1|aerator", "aerator-m22-m24"),
    (r"pg7|pg9|pg11|pg13|pg16|pg21|cable gland", "cable-gland"),
    (r"gt2|htd|timing belt", "timing-belt"),
    (r"\b2020\b|2040|v-?slot|t-?slot|1020|extrusion", "t-slot-extrusion"),
    (r"miter|t-?track|19mm", "miter-ttrack"),
    (r"ws2812|neopixel|sk6812", "addressable-led"),
    (r"ws28|8x8|16x16", "led-matrix"),
    (r"rms\b|w0\.800|objective", "rms-objective"),
    (r"thorlabs|breadboard|25\s*mm.*grid|1\s*in.*grid", "optical-breadboard"),
    (r"picatinny|weaver", "picatinny"),
    (r"molle|pals", "molle-pals"),
    (r"\bm3\b", "iso-m3"),
    (r"\bm4\b", "iso-m4"),
    (r"\bm5\b", "iso-m5"),
    (r"\bm6\b", "iso-m6"),
    (r"\bm8\b", "iso-m8"),
    (r"iso\s*15|608|6\d\d\s*bearing|bearing", "bearing-608"),
    (r"iso\s*53|involute|module\s*\d|pressure angle", "involute-gear"),
    (r"din\s*3975|worm", "worm-gear"),
    (r"iso\s*23509|bevel", "bevel-gear"),
    (r"webbing|molle|pals", "webbing-strap"),
    (r"pc\s*fan|40mm|60mm|80mm|120mm|140mm\s*fan", "pc-fan"),
    (r"18650|21700|\baa\b|\baaa\b|battery cell", "battery-cell"),
    (r"m49|m52|m58|m6[27]|m72|m77|m82|filter thread", "filter-thread"),
    (r"drip|1/4in.*1/2in|hydroponic", "drip-irrigation"),
    (r"emt|conduit", "conduit"),
    (r"net cup|net-cup", "net-cup"),
    (r"iso\s*4032|iso\s*4014|hex nut|hex bolt", "iso-hex-fastener"),
    (r"din\s*5480|spline|keyway|d-shaft", "shaft-spline"),
    (r"futaba|spektrum|servo (horn|spline)|24t|25t", "servo-spline"),
    (r"multiconnect|goews", "multiconnect"),
    (r"meanwell|lrs|rs-\d|psu", "psu-mount"),
    (r"cam-?lock|tailpiece", "cam-lock"),
    (r"e-?nable|osl", "enable-prosthetic"),
    (r"wall\s*stud|stud mount", "wall-stud"),
    (r"usb-?a|usb-?c|sd\s*card|microsd", "usb-sd-media"),
    (r"1\s*in.*round rail|25\s*mm.*round rail", "round-rail-25"),
    (r"can\s*[øo]|standard can|soda can", "beverage-can"),
    (r"cuvette", "cuvette"),
    (r"compass", "compass-capsule"),
    (r"tarot|mini card|standard card|playing card", "card-format"),
]

# Geometry pairs that physically join (unordered). Same-type anchors also mate.
_COMPLEMENTARY: set[frozenset[str]] = {
    frozenset({"socket", "profile"}),
    frozenset({"socket", "thread"}),
    frozenset({"socket", "spline"}),
    frozenset({"pocket", "profile"}),
    frozenset({"snap", "profile"}),
    frozenset({"rail", "profile"}),
    frozenset({"grid", "profile"}),
}
# Anchoring geometries that mate to their own kind (a bolt pattern bolts to a bolt pattern).
_SELF_MATING: set[str] = {"bolt_pattern", "grid", "rail", "thread", "snap", "socket"}


def normalize_family(standard: str) -> str | None:
    """Map a free-text CDG standard to a canonical family key, or None if unrecognized."""
    if not standard or standard.strip().lower() == "internal":
        return None
    s = standard.lower()
    for pattern, family in _FAMILY_PATTERNS:
        if re.search(pattern, s):
            return family
    return None


def _geometry_compatible(a: str, b: str) -> str | None:
    """Return the edge kind for two geometry types of the SAME family, else None."""
    if a == b and a in _SELF_MATING:
        return "same_family" if a in ("grid", "rail") else "mates_with"
    if frozenset({a, b}) in _COMPLEMENTARY:
        return "mates_with"
    return None


def _dir_signature() -> tuple:
    """Cheap stat-walk signature of the projects tree (mirrors catalog_index)."""
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


def _i18n(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("en") or next(iter(value.values()), "")
    return value or ""


def _collect_interfaces() -> list[dict]:
    """One flat list of every object's CDG interfaces, tagged with a resolved family."""
    ifaces: list[dict] = []
    for directory in Config.CARTRIDGES_DIRS:
        if not directory.is_dir():
            continue
        for child in sorted(os.scandir(directory), key=lambda e: e.name):
            if not child.is_dir():
                continue
            pj = os.path.join(child.path, "project.json")
            try:
                with open(pj, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            proj = data.get("project", {}) or {}
            if proj.get("unlisted"):
                continue
            slug = proj.get("slug", child.name)
            name = _i18n(proj.get("name", slug))
            ho = data.get("hyperobject", {}) or proj.get("hyperobject", {}) or {}
            for c in (ho.get("cdg_interfaces", []) or []):
                fam = normalize_family(c.get("standard", ""))
                if not fam:
                    continue
                ifaces.append({
                    "slug": slug,
                    "name": name,
                    "domain": ho.get("domain", ""),
                    "family": fam,
                    "geometry_type": c.get("geometry_type", ""),
                    "standard": c.get("standard", ""),
                    "iface_label": _i18n(c.get("label", "")),
                })
    return ifaces


def _build_graph() -> dict:
    """Derive nodes + edges by matching interfaces within each standard family."""
    t0 = time.perf_counter()
    ifaces = _collect_interfaces()

    by_family: dict[str, list[dict]] = defaultdict(list)
    for it in ifaces:
        by_family[it["family"]].append(it)

    # dedupe edges by (min,max slug, family, kind); keep the strongest kind per pair+family
    edge_map: dict[tuple, dict] = {}
    for family, members in by_family.items():
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                if a["slug"] == b["slug"]:
                    continue
                kind = _geometry_compatible(a["geometry_type"], b["geometry_type"])
                if not kind:
                    continue
                lo, hi = sorted((a["slug"], b["slug"]))
                key = (lo, hi, family)
                # mates_with is a stronger claim than same_family; keep the strongest
                prev = edge_map.get(key)
                if prev and prev["kind"] == "mates_with":
                    continue
                edge_map[key] = {
                    "a": lo,
                    "b": hi,
                    "family": family,
                    "kind": kind,
                    "via": a["standard"] if a["slug"] == lo else b["standard"],
                    "geometry": f"{a['geometry_type']}↔{b['geometry_type']}",
                }

    edges = list(edge_map.values())

    # node table: slug → name/domain + degree
    node_map: dict[str, dict] = {}
    for it in ifaces:
        node_map.setdefault(it["slug"], {
            "slug": it["slug"], "name": it["name"], "domain": it["domain"],
            "families": set(), "degree": 0,
        })
        node_map[it["slug"]]["families"].add(it["family"])
    for e in edges:
        node_map[e["a"]]["degree"] += 1
        node_map[e["b"]]["degree"] += 1

    nodes = []
    for n in node_map.values():
        n = dict(n)
        n["families"] = sorted(n["families"])
        nodes.append(n)
    nodes.sort(key=lambda n: (-n["degree"], n["slug"]))

    families = {
        fam: sorted({m["slug"] for m in members})
        for fam, members in by_family.items()
    }
    family_sizes = sorted(
        ({"family": f, "members": len(s)} for f, s in families.items()),
        key=lambda x: -x["members"],
    )

    return {
        "nodes": nodes,
        "edges": edges,
        "families": families,
        "family_sizes": family_sizes,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "generated_ms": int(round(time.perf_counter() - t0, 4) * 1000),
    }


def get_graph(force: bool = False) -> dict:
    """Return the cached compatibility graph, rebuilding only when projects change."""
    global _cache, _cache_sig
    sig = _dir_signature()
    if force or _cache is None or sig != _cache_sig:
        _cache = _build_graph()
        _cache_sig = sig
        logger.info(
            "compatibility graph rebuilt: %d nodes, %d edges in %dms",
            _cache["node_count"], _cache["edge_count"], _cache["generated_ms"],
        )
    return _cache


def invalidate_graph() -> None:
    """Drop the cache so the next get_graph() rebuilds."""
    global _cache, _cache_sig
    _cache = None
    _cache_sig = None


def works_with(slug: str) -> dict:
    """All compatibility partners of one object, grouped for a 'Works with' UI section."""
    graph = get_graph()
    name_by_slug = {n["slug"]: n["name"] for n in graph["nodes"]}
    domain_by_slug = {n["slug"]: n["domain"] for n in graph["nodes"]}
    partners: dict[str, dict] = {}
    for e in graph["edges"]:
        if e["a"] == slug:
            other = e["b"]
        elif e["b"] == slug:
            other = e["a"]
        else:
            continue
        p = partners.setdefault(other, {
            "slug": other,
            "name": name_by_slug.get(other, other),
            "domain": domain_by_slug.get(other, ""),
            "thumbnail": f"/projects/{other}.svg",
            "reasons": [],
        })
        p["reasons"].append({"family": e["family"], "kind": e["kind"],
                             "via": e["via"], "geometry": e["geometry"]})
    ordered = sorted(partners.values(), key=lambda p: (-len(p["reasons"]), p["slug"]))
    return {"slug": slug, "count": len(ordered), "partners": ordered}
