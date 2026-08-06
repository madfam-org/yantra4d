"""
Router Template Guide — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Template-routing guide bushings and adapters. A guide bushing drops into the
router's sub-base through the standard Porter-Cable-pattern flange hole; its
barrel rides against a template edge while the bit passes through the centre, so
the cut follows the template offset by the bushing wall. The FUNCTIONAL interface
is the universal router-bushing flange (1-3/8 in / 34.9 mm OD, dropping into the
1-3/16 in sub-base recess) — the de-facto open standard shared across router
brands via adapter plates.

Bushing reference (Porter-Cable universal pattern, imperial):
  flange OD  = 1-3/8 in = 34.93 mm   flange seat = 1-3/16 in = 30.16 mm
  flange thk ≈ 0.150 in = 3.8 mm     barrel ODs in 1/16 in steps
Common barrel ODs (OD → typical bit clearance): 5/16, 3/8, 7/16, 1/2, 5/8, 3/4 in.

Modes (dispatched via `target_part`):
  * "guide_bushing"    — the bushing: a flange + a projecting barrel with a
                         through bore for the bit; the barrel rides the template.
  * "baseplate_adapter"— an adapter ring that seats the universal bushing flange
                         and mounts to a router sub-base by a bolt circle.
  * "offset_collar"    — a fixed collar that clamps over a barrel to enlarge its
                         effective OD, setting a precise template-to-cut offset.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Universal router-bushing flange (Porter-Cable pattern) ───────────────────
FLANGE_OD = 34.93      # 1-3/8 in flange outer diameter
SEAT_OD = 30.16        # 1-3/16 in sub-base recess the flange drops into
FLANGE_TH = 3.8        # flange thickness

# Barrel OD table (inch designation → mm OD).
BARREL_TABLE = {
    "5/16": 7.94,
    "3/8": 9.53,
    "7/16": 11.11,
    "1/2": 12.70,
    "5/8": 15.88,
    "3/4": 19.05,
}


def barrel_od(key):
    return BARREL_TABLE.get(str(key).strip(), BARREL_TABLE["1/2"])


# ── Parameters ───────────────────────────────────────────────────────────────
barrel      = str(  PARAM(lambda: barrel,     "1/2"))     # barrel OD designation
barrel_len  = float(PARAM(lambda: barrel_len,   8.0))     # barrel projection below the flange (mm)
bit_clear   = float(PARAM(lambda: bit_clear,    0.4))     # extra bit clearance in the bore (mm)
wall        = float(PARAM(lambda: wall,         2.0))     # barrel wall thickness (mm)
plate_dia   = float(PARAM(lambda: plate_dia,   90.0))     # adapter baseplate diameter (mm)
bolt_circle = float(PARAM(lambda: bolt_circle, 60.0))     # adapter mount bolt-circle dia (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,     4.5))     # adapter mount bolt clearance (mm)
hole_count  = int(  PARAM(lambda: hole_count,     3))     # adapter mount bolt count
offset      = float(PARAM(lambda: offset,       3.0))     # offset-collar added radius (mm)

target_part = str(PARAM(lambda: target_part, "guide_bushing"))  # guide_bushing|baseplate_adapter|offset_collar


# ── Derived / clamped geometry ───────────────────────────────────────────────
b_od = barrel_od(barrel)
wall = max(1.0, min(wall, 4.0))
bit_clear = max(0.0, min(bit_clear, 3.0))
# Bore = barrel OD minus two walls, plus bit clearance.
bore_d = max(2.0, b_od - 2.0 * wall + bit_clear)
barrel_len = max(3.0, min(barrel_len, 40.0))
plate_dia = max(FLANGE_OD + 12.0, min(plate_dia, 200.0))
bolt_circle = max(FLANGE_OD + 6.0, min(bolt_circle, plate_dia - 8.0))
bolt_dia = max(2.0, min(bolt_dia, 10.0))
hole_count = max(2, min(hole_count, 8))
offset = max(0.5, min(offset, 20.0))


# ── Builders ─────────────────────────────────────────────────────────────────
def build_guide_bushing():
    """The bushing: a flange disc (drops into the sub-base recess) with a
    projecting barrel below it and a bit-clearance bore through the whole part.
    Bore is open at both faces → no trapped void."""
    # Flange disc.
    body = cq.Workplane("XY").circle(FLANGE_OD / 2.0).extrude(FLANGE_TH)
    # A registration lip (the SEAT_OD portion) that centres in the recess — a
    # short step down from the flange underside, unioned so it is one solid.
    lip = (
        cq.Workplane("XY")
        .circle(SEAT_OD / 2.0)
        .extrude(-1.2)
    )
    body = body.union(lip)
    # Barrel projecting down from the lip.
    barrel_body = (
        cq.Workplane("XY")
        .circle(b_od / 2.0)
        .extrude(-(barrel_len + 1.2))
    )
    body = body.union(barrel_body)
    # Bit bore through the entire stack (flange top → barrel tip).
    total = FLANGE_TH + 1.2 + barrel_len
    bore = (
        cq.Workplane("XY")
        .circle(bore_d / 2.0)
        .extrude(-(total + 2.0))
        .translate((0, 0, FLANGE_TH + 1.0))
    )
    body = body.cut(bore)
    return body


def build_baseplate_adapter():
    """An adapter ring: a plate with the universal SEAT recess in the middle (so a
    standard bushing flange drops in) and a bolt circle to mount it to a router
    sub-base. A large centre clearance passes the barrel + bit."""
    t = max(4.0, FLANGE_TH + 2.0)
    body = cq.Workplane("XY").circle(plate_dia / 2.0).extrude(t)
    # Flange recess cut from the TOP so the bushing flange seats flush.
    recess = (
        cq.Workplane("XY")
        .circle(FLANGE_OD / 2.0 + 0.3)
        .extrude(-(FLANGE_TH + 0.01))
        .translate((0, 0, t + 0.005))
    )
    body = body.cut(recess)
    # Centre clearance through the plate for the barrel / bit.
    centre = (
        cq.Workplane("XY")
        .circle(SEAT_OD / 2.0)
        .extrude(t + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(centre)
    # Mount bolt circle.
    for k in range(hole_count):
        ang = math.radians(360.0 / hole_count * k)
        hx = (bolt_circle / 2.0) * math.cos(ang)
        hy = (bolt_circle / 2.0) * math.sin(ang)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, hy, -0.5))
            .circle(bolt_dia / 2.0)
            .extrude(t + 1.0)
        )
        body = body.cut(hole)
    return body


def build_offset_collar():
    """A fixed collar that clamps over a bushing barrel to enlarge its effective
    OD by `offset`, setting a precise template-to-cut offset. A split ring: a tube
    of (barrel OD → barrel OD + 2·offset) with a through bore matching the barrel,
    and a narrow radial slot so it springs onto the barrel."""
    inner_r = b_od / 2.0 + 0.15                 # slip fit over the barrel
    outer_r = inner_r + offset
    height = min(barrel_len, 10.0)
    body = cq.Workplane("XY").circle(outer_r).extrude(height)
    bore = cq.Workplane("XY").circle(inner_r).extrude(height + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)
    # Radial split slot (a thin box from the bore out through the wall).
    slot_w = max(1.0, offset * 0.4)
    slot = (
        cq.Workplane("XY")
        .box(outer_r + 1.0, slot_w, height + 2.0, centered=(False, True, False))
        .translate((0, 0, -1.0))
    )
    body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "baseplate_adapter":
    result = build_baseplate_adapter()
elif target_part == "offset_collar":
    result = build_offset_collar()
else:
    result = build_guide_bushing()
