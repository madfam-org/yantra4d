"""
Crochet / Knitting Needle Gauge — Yantra4D Hyperobject Cartridge (CadQuery).

A sizing gauge: a plate with precisely-sized through-holes. You push a needle or
hook through the holes; the smallest snug hole is its size. The holes ARE the
functional interface — each hole diameter is a real US/metric needle size, so a
gauge printed anywhere sizes any needle to the same standard.

Real sizes encoded (metric mm ↔ US knitting):
  2.0(US0) 2.25(1) 2.75(2) 3.0(2.5) 3.25(3) 3.5(4) 3.75(5) 4.0(6) 4.5(7)
  5.0(US8) 5.5(9) 6.0(10) 6.5(10.5) 8.0(11) 9.0(13) 10.0(15) 12.0(17)
  (Crochet hooks share the same metric ladder.)

Modes:
  - ruler_gauge : a flat stick with an in-line row of graduated holes and a
    scale edge — the classic needle gauge.
  - disc_gauge  : a round disc with the holes arranged radially like a clock,
    compact for a project bag.
  - gauge_swatch: a plate with a large square window (a stitch/gauge counter you
    lay over knitting) plus a few needle holes along one edge.

Watertight strategy:
  Every hole is a through-hole (open both faces → vented). The size text is NOT
  embossed (embossed thin glyphs crack meshes); instead each hole is tagged by a
  notch count / tick marks cut as through-slots. The blank is fillet-cleaned
  BEFORE the holes are cut. Holes bored in ONE pushPoints pass = one boolean.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq
import math


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Standard needle ladder (metric mm; each is a real US/crochet size) ───────
NEEDLE_SIZES = [
    2.0, 2.25, 2.75, 3.0, 3.25, 3.5, 3.75, 4.0, 4.5,
    5.0, 5.5, 6.0, 6.5, 8.0, 9.0, 10.0, 12.0,
]


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "ruler_gauge"))
# "ruler_gauge" | "disc_gauge" | "gauge_swatch"

size_min = float(PARAM(lambda: size_min, 2.0))    # smallest hole to include (mm)
size_max = float(PARAM(lambda: size_max, 10.0))   # largest hole to include (mm)
clear    = float(PARAM(lambda: clear, 0.15))      # per-side hole oversize (mm)
plate_th = float(PARAM(lambda: plate_th, 3.0))    # plate thickness (mm)
window   = float(PARAM(lambda: window, 25.0))     # swatch window side (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
size_min = max(1.5, min(size_min, 8.0))
size_max = max(size_min + 1.0, min(size_max, 14.0))
clear    = max(0.0, min(clear, 0.6))
plate_th = max(2.0, min(plate_th, 6.0))
window   = max(12.0, min(window, 60.0))

_sizes = [s for s in NEEDLE_SIZES if size_min - 1e-6 <= s <= size_max + 1e-6]
if not _sizes:
    _sizes = [size_min, (size_min + size_max) / 2.0, size_max]


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _rounded_plate(length, width, th, fillet_r):
    """A rounded-rectangle plate, fillet-cleaned BEFORE hole cuts."""
    plate = cq.Workplane("XY").box(length, width, th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(fillet_r, min(length, width) / 2.0 - 0.5))
    except Exception:
        pass
    return plate


# ── Part builders ────────────────────────────────────────────────────────────
def build_ruler_gauge():
    """A flat stick with an in-line row of graduated holes; each hole is a real
    needle size, tagged with 1..n tick marks so sizes are readable without text."""
    n = len(_sizes)
    max_r = _sizes[-1] / 2.0 + clear
    pitch = max(_sizes[-1] + 5.0, 12.0)
    length = pitch * n + 12.0
    width = max_r * 2.0 + 12.0
    body = _rounded_plate(length, width, plate_th, 3.0)

    x0 = -(pitch * (n - 1)) / 2.0
    # Per-hole radii differ, so build a combined cutter (one final boolean cut).
    # Each hole is a vented through-hole (open both faces). Holes are graduated
    # in size (self-documenting) and one small hang hole sits at the left end.
    cutter = cq.Workplane("XY").circle(2.0).extrude(plate_th + 2.0).translate((x0 - pitch * 0.55, 0, -1.0))
    for i, s in enumerate(_sizes):
        r = s / 2.0 + clear
        x = x0 + i * pitch
        h = cq.Workplane("XY").circle(r).extrude(plate_th + 2.0).translate((x, 0, -1.0))
        cutter = cutter.union(h)
    body = body.cut(cutter)
    return body


def build_disc_gauge():
    """A round disc with the holes arranged radially like clock positions —
    compact for a project bag. A centre hanging hole too."""
    n = len(_sizes)
    max_r = _sizes[-1] / 2.0 + clear
    ring_r = max(22.0, (max_r + 4.0) * n / math.pi + 6.0)
    disc_r = ring_r + max_r + 6.0
    body = cq.Workplane("XY").circle(disc_r).extrude(plate_th)
    try:
        body = body.edges("|Z").fillet(2.0)
    except Exception:
        pass

    cutter = None
    for i, s in enumerate(_sizes):
        r = s / 2.0 + clear
        ang = 2.0 * math.pi * i / n
        x = ring_r * math.cos(ang)
        y = ring_r * math.sin(ang)
        h = cq.Workplane("XY").circle(r).extrude(plate_th + 2.0).translate((x, y, -1.0))
        cutter = h if cutter is None else cutter.union(h)
    body = body.cut(cutter)

    # Centre hanging hole (through, vented).
    hang = cq.Workplane("XY").circle(3.0).extrude(plate_th + 2.0).translate((0, 0, -1.0))
    body = body.cut(hang)
    return body


def build_gauge_swatch():
    """A plate with a large square WINDOW (a stitch-gauge counter you lay over
    knitting) plus a column of a few needle holes along one edge."""
    n = min(len(_sizes), 6)
    subset = _sizes[:n]
    max_r = (subset[-1] if subset else 6.0) / 2.0 + clear
    edge_col_w = max_r * 2.0 + 8.0
    plate_w = window + 12.0 + edge_col_w
    plate_h = window + 16.0
    body = _rounded_plate(plate_w, plate_h, plate_th, 3.0)

    # Central-left square window (through, vented).
    win = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-edge_col_w / 2.0, 0, 0))
        .rect(window, window)
        .extrude(plate_th + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(win)

    # Column of needle holes down the right edge.
    col_x = plate_w / 2.0 - edge_col_w / 2.0
    y0 = -(window / 2.0) + max_r
    step = window / max(1, n - 1) if n > 1 else 0.0
    cutter = None
    for i, s in enumerate(subset):
        r = s / 2.0 + clear
        y = y0 + i * step
        h = cq.Workplane("XY").circle(r).extrude(plate_th + 2.0).translate((col_x, y, -1.0))
        cutter = h if cutter is None else cutter.union(h)
    if cutter is not None:
        body = body.cut(cutter)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "disc_gauge":
    result = build_disc_gauge()
elif target_part == "gauge_swatch":
    result = build_gauge_swatch()
else:
    result = build_ruler_gauge()
