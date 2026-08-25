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
    (r"pco[\s-]*1881", "pco-1881"),
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
    # "16x16 / 19x19 / 9x9 brushless motor mount" is the FPV motor bolt square, not an
    # LED matrix — the old "8x8|16x16" alternatives mis-familied drone hardware.
    (r"brushless\s*motor\s*mount", "drone-motor-mount"),
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
    # sizes must be fan-qualified: bare "40mm|60mm…" matched gauges and internal parts
    (r"pc\s*fan|(40|60|80|92|120|140)\s*mm\s*fan", "pc-fan"),
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
    # ── D12 coverage: each entry names ONE physical mating standard ──────────
    # lab & optics
    (r"slas|\bsbs\b|microplate", "slas-microplate"),           # ANSI/SLAS 1/4-2004 9mm-pitch microplate footprint
    (r"iso\s*8037", "microscope-slide"),                        # ISO 8037-1 25.4x76.2mm slide
    (r"\bfalcon\b|conical\s*(centrifuge\s*)?tube", "conical-tube"),  # 15/50mL conical (Falcon) tube
    (r"90\s*mm\s*petri", "petri-90mm"),                         # 90mm petri dish body
    (r"stir\s*bars?\b", "stir-bar"),                            # PTFE magnetic stir bar sizes
    (r"\bluer\b", "luer"),                                      # ISO 80369/594 Luer taper
    (r"support\s*rod|optical\s*post", "support-rod-12"),        # Ø12-12.7mm lab/optical rod
    (r"(1\s*in|25(\.4)?\s*mm)[^a-z]*optic\b", "optic-25.4"),    # Ø1in/25mm round optics
    # construction-set & wall-system ecosystems
    (r"stemfie", "stemfie"),                                    # STEMFIE 10mm-pitch construction set
    (r"construction\s*brick|\blego\b", "brick-8mm-stud"),       # 8mm-stud construction brick
    (r"1[\s-]*in(ch)?\s*pegboard|pegboard\s*1\s*in", "pegboard-1in"),  # US 1in-pitch pegboard
    (r"french\s*cleat", "french-cleat"),                        # 45-deg French cleat
    (r"keyhole", "keyhole-hanger"),                             # keyhole-slot wall hanging
    # boards, electronics & RC
    (r"\brpi\b|raspberry\s*pi\b|\bpi\s*hat\b", "rpi-mount"),    # Raspberry Pi 58x49mm M2.5 holes (HAT spec)
    (r"arduino", "arduino-mount"),                              # Arduino Uno/Mega hole pattern
    (r"\bomron\b|\bd2f\b", "microswitch-d2f"),                  # Omron D2F/SS microswitch mount
    (r"\bsg90\b|\bmg996r?\b", "servo-body"),                    # SG90/MG996R servo body cutout
    (r"\bsma\b|u\.fl", "sma-rf"),                               # SMA / U.FL RF connector
    (r"fpv\s*(micro|nano|mini|cam)", "fpv-cam"),                # FPV cam widths 14/19/21mm
    (r"(5050|2835)\s*(led\s*)?(strip|tape)|led\s*strip", "led-strip"),  # 8-10mm SMD LED strip
    (r"3\.5\s*mm.*switch|assistive\s*switch", "at-switch-3.5mm"),  # 3.5mm assistive-tech switch jack
    (r"j1962", "sae-j1962"),                                    # OBD-II connector
    (r"iso\s*8820|\bato\b", "ato-fuse"),                        # ISO 8820-3 ATO/Mini blade fuse
    # machine, metrology & drive
    (r"\bmgn\s*\d", "mgn-rail"),                                # MGN9/12/15 miniature linear rail
    (r"iso\s*2904|\bacme\b|trapezoidal", "trapezoidal-thread"), # ISO 2904 Tr / ACME leadscrew
    (r"iso\s*4183|v-?belt\b|\bspz\b", "v-belt"),                # ISO 4183 A/SPZ V-belt groove
    (r"iso\s*261|iso\s*965", "iso-metric-thread"),              # ISO metric thread system (generic)
    (r"\ber\s*/\s*straight|\ber\s*collet|din\s*6499", "er-collet"),  # DIN 6499 ER collet
    (r"indicator[\s-]*dovetail|lever-indicator", "indicator-dovetail"),  # test-indicator dovetail
    (r"indicator\s*stem", "indicator-stem-8mm"),                # 8mm indicator stem (AGD)
    (r"\bkurt\b", "kurt-vise"),                                 # Kurt-style vise bolt pattern
    (r"hex\s*(driver\s*)?bit|1/4\s*in\s*hex", "hex-bit-1/4"),   # 1/4in hex driver bit (ISO 1173)
    # plumbing, HVAC & household
    (r"\bips\b|pvc\s*sch", "ips-pipe"),                         # IPS/PVC-sch40 pipe OD (0.84/1.05in…)
    (r"\bpex\b|copper\s*tube|\bcts\b", "cts-pipe"),             # CTS copper/PEX tube OD
    (r"tubular", "tubular-drain"),                              # 1-1/4 / 1-1/2in tubular drain slip
    (r"round\s*duct", "round-duct"),                            # US nominal round duct 4/5/6in
    (r"\d{2}-4[01]0\b|\bspi\s*\d", "spi-neck"),                 # SPI 20-410/24-410/28-410 bottle neck
    (r"crown\s*cap", "crown-cap-26"),                           # 26mm crown bottle cap
    (r"wall\s*box", "wall-box"),                                # US/EU electrical wall-box screw pattern
    (r"license\s*plate", "license-plate"),                      # US 12x6in / EU 520x110mm plate
    (r"\ba156\b", "ansi-a156-strike"),                          # ANSI/BHMA A156.2 strike/bore
    # vehicle & outdoor
    (r"handlebar", "handlebar-clamp"),                          # Ø22.2-31.8mm handlebar
    (r"bottle\s*boss", "bottle-cage-boss"),                     # bicycle 64mm M5 bottle boss
    (r"paracord", "paracord-550"),                              # MIL-C-5040 550 paracord
    (r"ferro\s*rod", "ferro-rod"),                              # 6/8mm ferrocerium rod
    # craft, hobby & wearables
    (r"mm\s*lug\b|watch\s*lug", "watch-lug"),                   # 18/20/22mm watch strap lug
    (r"eta\s*2824|\bcalibre\b|\bligne\b", "watch-movement"),    # ETA 2824-2 / ligne movement ring
    (r"class\s*15\b|l[\s-]style\s*bobbin", "bobbin-class-15"),  # Class 15 / L-style sewing bobbin
    (r"low\s*/\s*high\s*shank|presser\s*foot", "presser-shank"),  # sewing low/high presser shank
    (r"citadel|vallejo", "paint-pot"),                          # Citadel/Vallejo hobby paint pots
    (r"business\s*card", "business-card"),                      # 3.5x2in business card
    (r"portafilter|58/54/51", "portafilter-58"),                # 58/54/51mm espresso basket
    (r"(52|60)\s*mm\s*gauge", "auto-gauge-52-60"),              # 52/60mm automotive gauge pod
    (r"5/8[\s-]*27|mic\s*(stand\s*)?thread", "mic-thread-5/8-27"),  # 5/8in-27 mic stand thread
    (r"baby\s*pin", "baby-pin-5/8"),                            # 5/8in grip/lighting baby pin
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
    if not standard:
        return None
    s = standard.lower()
    # "internal", "internal/aocl", "internal peg grid 8mm"… are private geometry, never
    # a shared standard — reject the whole prefixed class, not just the exact token.
    if s.strip().startswith("internal"):
        return None
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
