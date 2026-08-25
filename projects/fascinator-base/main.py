"""Fascinator Base — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The small millinery base a fascinator is built on: a shallow disc or dome with a flat
sewing brim, a pair of slots underneath that a hair comb's spine slides into, and a ring of
sew holes around the brim so sinamay, feathers, veiling and trim are stitched on rather
than hot-glued.

Millinery practice: commercial fascinator bases are buckram or sinamay-covered card in a
handful of diameters — 60, 80, 100, 120 mm — with one crown height and no comb provision at
all (you sew a comb on with a needle and a lot of patience). The base is what carries
everything: trim sews to the brim, and a comb anchors the whole thing to the head. A
printed base gets the diameter and the crown right for the head and the outfit, and gets a
comb slot that matches the comb actually on hand.

`dome_h` below 1 mm gives a flat plate base — the kind worn tilted on the side of the head;
raising it gives the pillbox-style domed base that sits over the crown. The dome is a
revolved profile with a FLAT apex ring (never a closed pole: a pole singularity tessellates
as degenerate slivers and reads non-watertight) and the shell's hollow opens downward, so
it drains and prints without a bridge.

Modes (dispatched via `target_part`):
  * "base" — one fascinator base.
  * "pair" — two bases on the plate (a fascinator and its matching mini, or a spare).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `base_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
base_dia  = float(PARAM(lambda: base_dia,  90.0))  # base outside diameter (mm)
dome_h    = float(PARAM(lambda: dome_h,    14.0))  # crown rise above the brim (mm)
base_t    = float(PARAM(lambda: base_t,     2.4))  # shell wall thickness (mm)
brim_w    = float(PARAM(lambda: brim_w,     9.0))  # flat sewing brim width (mm)
sew_holes = int(  PARAM(lambda: sew_holes,   16))  # perimeter sew holes (count)
hole_dia  = float(PARAM(lambda: hole_dia,   2.0))  # sew hole diameter (mm)
comb_w    = float(PARAM(lambda: comb_w,    38.0))  # hair comb spine width (mm)
comb_t    = float(PARAM(lambda: comb_t,     2.2))  # hair comb spine thickness (mm)

target_part = str(PARAM(lambda: target_part, "base"))  # base|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
base_dia  = max(40.0, min(base_dia, 200.0))
dome_h    = max(0.0, min(dome_h, base_dia * 0.45))
base_t    = max(1.2, min(base_t, 6.0))
sew_holes = max(0, min(sew_holes, 48))
hole_dia  = max(1.0, min(hole_dia, 4.0))
comb_w    = max(15.0, min(comb_w, base_dia * 0.75))
comb_t    = max(1.2, min(comb_t, 5.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
base_r = base_dia / 2.0
# The brim is the flat sewing land; it must be wide enough to hold the hole ring with wall
# on both sides, and never wider than most of the radius.
brim_w = max(hole_dia + 3.0, min(brim_w, base_r * 0.6))
sew_r = base_r - brim_w / 2.0                  # hole ring runs down the brim centreline
hole_dia = min(hole_dia, max(0.8, brim_w - 2.4))
crown_r = base_r - brim_w                      # the dome springs from here
# Flat apex ring: never a closed pole. Big enough to tessellate cleanly at any size.
apex_r = max(2.5, min(crown_r * 0.15, 10.0))
# Comb slot pair: two parallel through-slots that the comb's spine threads.
slot_l = min(comb_w, crown_r * 1.9)
slot_w = comb_t + 0.4                          # running clearance on the spine
slot_pitch = max(slot_w * 2.5, min(base_dia * 0.22, 24.0))
# A flat plate needs enough meat to hold a slot; a dome carries its own wall.
plate_t = max(base_t, comb_t + 1.6)
is_dome = dome_h >= 1.0


def _pt(r, a):
    """Polar to cartesian on XY."""
    return (r * math.cos(a), r * math.sin(a))


def _quarter_ellipse(r0, z0, r1, z1, n=10):
    """Points walking a quarter ellipse from (r0, z0) at 0 deg to (r1, z1) at 90 deg.

    Sampled as a polyline rather than a three-point arc, because a circular arc through
    the two ends overshoots the stated crown height by several per cent.
    """
    a, b = r0 - r1, z1 - z0
    return [
        (r1 + a * math.cos(math.pi / 2.0 * i / n), z0 + b * math.sin(math.pi / 2.0 * i / n))
        for i in range(1, n + 1)
    ]


def _flat_blank():
    """A flat plate base, chamfered on the clean blank before any cuts."""
    disc = cq.Workplane("XY").circle(base_r).extrude(plate_t)
    try:
        disc = disc.edges(">Z").chamfer(min(plate_t * 0.3, 0.8))
    except Exception:
        pass
    return disc


def _dome_blank():
    """A domed shell with a flat sewing brim: ONE revolved profile, upright about Y.

    The closed profile runs rim edge -> brim top -> outer dome -> flat apex ring -> inner
    dome -> underside, so the revolve yields exactly one solid whose hollow opens downward.
    """
    t = base_t
    ri = max(0.8, crown_r - t)
    hi = max(t + 0.4, dome_h - t)
    wp = (
        cq.Workplane("XZ")
        .moveTo(base_r, 0.0)
        .lineTo(base_r, t)
        .lineTo(crown_r, t)
    )
    for p in _quarter_ellipse(crown_r, t, apex_r, dome_h):
        wp = wp.lineTo(*p)
    wp = wp.lineTo(apex_r, hi)
    # Inner surface, walked back outward from the apex to the brim.
    inner = _quarter_ellipse(ri, t, apex_r, hi)
    inner = [(ri, t)] + inner[:-1]
    for p in reversed(inner):
        wp = wp.lineTo(*p)
    return (
        wp.lineTo(ri, 0.0)
        .lineTo(base_r, 0.0)
        .close()
        .revolve(360.0, (0, 0, 0), (0, 1, 0))
    )


def _sew_ring_cutter():
    """One pushPoints op cutting the whole perimeter sew-hole ring straight through."""
    if sew_holes <= 0:
        return None
    pts = [_pt(sew_r, 2.0 * math.pi * i / sew_holes) for i in range(sew_holes)]
    depth = max(dome_h, plate_t) + 10.0
    return (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(hole_dia / 2.0)
        .extrude(depth)
        .translate((0, 0, -5.0))
    )


def _comb_slot_cutter():
    """The comb-slot pair: two parallel through-slots the comb spine threads.

    Cut straight down through the base so both openings are free — the slot drains and
    prints without a bridge.
    """
    depth = max(dome_h, plate_t) + 10.0
    slots = None
    for sign in (-1.0, 1.0):
        slot = (
            cq.Workplane("XY")
            .rect(slot_l, slot_w)
            .extrude(depth)
            .translate((0, sign * slot_pitch / 2.0, -5.0))
        )
        # Round the slot ends so the comb spine does not catch on a square corner.
        try:
            slot = slot.edges("|Z").fillet(min(slot_w * 0.45, 0.9))
        except Exception:
            pass
        slots = slot if slots is None else slots.union(slot)
    return slots


def build_base():
    """One fascinator base: blank, comb slots, perimeter sew-hole ring."""
    body = _dome_blank() if is_dome else _flat_blank()
    slots = _comb_slot_cutter()
    if slots is not None:
        body = body.cut(slots)
    ring = _sew_ring_cutter()
    if ring is not None:
        body = body.cut(ring)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    one = build_base()
    gap = max(6.0, base_dia * 0.08)
    off = base_r + gap / 2.0
    asm = cq.Assembly()
    asm.add(one.translate((-off, 0, 0)), name="base_a", color=cq.Color("#c4b0c8"))
    asm.add(one.translate((off, 0, 0)), name="base_b", color=cq.Color("#b4a0b8"))
    result = asm
else:
    result = build_base()
