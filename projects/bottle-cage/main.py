"""
Bike Bottle Cage — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A water-bottle cage that bolts to a bicycle frame's standard water-bottle bosses
(two M5 threaded bosses at 64 mm spacing). Sized by the bottle diameter so the
cradle grips a 73 mm bidon (or any size). The bolt pattern is the shared
interface — every frame in the world exposes it.

Three parts (dispatched by `target_part`):
  * "cage"             — a classic side-entry cage: two curved band loops on a
                         spine, open at the front so the bottle springs in/out.
  * "top_entry_cage"   — a fuller wrap with a single upper retaining loop and a
                         bottom cup; the bottle drops in from the top.
  * "accessory_mount"  — a boss-mounted plate that carries a multitool / CO2 /
                         spares canister instead of a bottle.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bottle_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cage"))  # cage|top_entry|accessory

bottle_dia = float(PARAM(lambda: bottle_dia, 73.0))  # bottle diameter (mm) — 73 std
boss_space = float(PARAM(lambda: boss_space, 64.0))  # M5 boss vertical spacing (mm)
band_w     = float(PARAM(lambda: band_w,     12.0))  # cradle band width (mm)
band_t     = float(PARAM(lambda: band_t,      4.0))  # cradle band thickness (mm)
spine_w    = float(PARAM(lambda: spine_w,    18.0))  # backbone spine width (mm)
grip       = float(PARAM(lambda: grip,      210.0))  # front wrap of each band (deg)
bolt_dia   = float(PARAM(lambda: bolt_dia,    5.5))  # M5 clearance hole dia (mm)
tool_dia   = float(PARAM(lambda: tool_dia,   40.0))  # accessory canister diameter (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
bottle_dia = max(45.0, min(bottle_dia, 90.0))
boss_space = max(40.0, min(boss_space, 80.0))
band_w     = max(8.0, min(band_w, 25.0))
band_t     = max(3.0, min(band_t, 8.0))
spine_w    = max(12.0, min(spine_w, 30.0))
grip       = max(180.0, min(grip, 300.0))
bolt_dia   = max(4.5, min(bolt_dia, 8.0))
tool_dia   = max(20.0, min(tool_dia, 70.0))

R = bottle_dia / 2.0            # bottle radius (band inner)
band_ro = R + band_t            # band outer radius


# ── Helpers ──────────────────────────────────────────────────────────────────
def c_band(z_center):
    """A C-shaped cradle band centred on the bottle axis (Z) at height z_center,
    wrapping `grip` degrees with its mouth facing +X (front, where the bottle
    springs in). Built as a full ring annulus with a pie mouth cut out."""
    ring = (
        cq.Workplane("XY")
        .circle(band_ro).circle(R)
        .extrude(band_w)
        .translate((0, 0, z_center - band_w / 2.0))
    )
    open_deg = 360.0 - grip
    if open_deg > 1.0:
        a0 = math.radians(-open_deg / 2.0)
        a1 = math.radians(open_deg / 2.0)
        am = 0.0
        cutter = (
            cq.Workplane("XY")
            .moveTo(0, 0)
            .lineTo((band_ro + 4.0) * math.cos(a0), (band_ro + 4.0) * math.sin(a0))
            .threePointArc(
                ((band_ro + 4.0) * math.cos(am), (band_ro + 4.0) * math.sin(am)),
                ((band_ro + 4.0) * math.cos(a1), (band_ro + 4.0) * math.sin(a1)),
            )
            .close()
            .extrude(band_w + 2.0)
            .translate((0, 0, z_center - band_w / 2.0 - 1.0))
        )
        ring = ring.cut(cutter)
    return ring


def spine_bar(z_lo, z_hi):
    """A flat backbone spine running up the back (−X side) of the bottle, joining
    the bands and carrying the boss holes. A vertical plate tangent to the bands."""
    height = z_hi - z_lo
    return (
        cq.Workplane("XY")
        .box(band_t + 2.0, spine_w, height, centered=(True, True, False))
        .translate((-(R + band_t / 2.0) + 0.5, 0, z_lo))
    )


def boss_plate(z_center):
    """The frame-mount plate on the back of the spine with two M5 clearance holes
    at `boss_space` spacing (centred on z_center), bored along −X into the frame."""
    plate_h = boss_space + 2.5 * bolt_dia
    plate_t = band_t + 3.0
    plate = (
        cq.Workplane("XY")
        .box(plate_t, spine_w, plate_h, centered=(True, True, False))
        .translate((-(R + band_t) - plate_t / 2.0 + 1.0, 0, z_center - plate_h / 2.0))
    )
    r = bolt_dia / 2.0
    for z in [z_center - boss_space / 2.0, z_center + boss_space / 2.0]:
        cutter = (
            cq.Workplane("YZ")
            .circle(r)
            .extrude(plate_t + 6.0)
            .translate((-(R + band_t) - plate_t - 3.0, 0, z))
        )
        plate = plate.cut(cutter)
    return plate


def base_cup():
    """A shallow closed cup the bottle base sits in (bottom of the cage)."""
    cup_h = band_w
    cup = (
        cq.Workplane("XY")
        .circle(band_ro).circle(R)
        .extrude(cup_h)
    )
    floor = (
        cq.Workplane("XY")
        .circle(band_ro)
        .extrude(band_t)
    )
    return cup.union(floor)


# ── Part builders ────────────────────────────────────────────────────────────
def build_cage():
    """Classic side-entry cage: an upper and lower C-band on a spine, plus a base
    cup, with the boss plate on the back."""
    total_h = boss_space + bottle_dia * 0.55
    z_lo = 0.0
    z_hi = total_h
    upper_z = z_hi - band_w * 1.2
    lower_z = z_lo + bottle_dia * 0.28

    body = base_cup()
    body = body.union(c_band(lower_z))
    body = body.union(c_band(upper_z))
    body = body.union(spine_bar(z_lo, z_hi))
    body = body.union(boss_plate((z_lo + z_hi) / 2.0))
    return body


def build_top_entry_cage():
    """Top-entry: a deep base cup and one broad upper retaining loop; the bottle
    drops in from the top and is held by the loop + cup."""
    total_h = boss_space + bottle_dia * 0.7
    z_lo = 0.0
    z_hi = total_h
    # Deeper base cup.
    deep_h = bottle_dia * 0.45
    cup = (
        cq.Workplane("XY")
        .circle(band_ro).circle(R)
        .extrude(deep_h)
    )
    floor = cq.Workplane("XY").circle(band_ro).extrude(band_t)
    body = cup.union(floor)
    # Single broad upper loop (wider band, wraps more).
    global grip, band_w
    saved_grip, saved_bw = grip, band_w
    grip = min(300.0, grip + 40.0)
    band_w = band_w * 1.6
    body = body.union(c_band(z_hi - band_w * 0.7))
    grip, band_w = saved_grip, saved_bw
    body = body.union(spine_bar(z_lo, z_hi))
    body = body.union(boss_plate((z_lo + z_hi) / 2.0))
    return body


def build_accessory_mount():
    """A boss-mounted holder for a tool/CO2/spares canister of `tool_dia` instead
    of a bottle — a short deep cup with a retaining strap loop and the boss plate."""
    r = tool_dia / 2.0
    ro = r + band_t
    cup_h = tool_dia * 0.9
    cup = cq.Workplane("XY").circle(ro).circle(r).extrude(cup_h)
    floor = cq.Workplane("XY").circle(ro).extrude(band_t)
    body = cup.union(floor)
    # Upper retaining loop (a full closed ring, since a canister is captive).
    loop = (
        cq.Workplane("XY")
        .circle(ro).circle(r)
        .extrude(band_w)
        .translate((0, 0, cup_h - band_w))
    )
    body = body.union(loop)
    # Spine + boss plate, sized to this smaller diameter.
    height = cup_h
    spine = (
        cq.Workplane("XY")
        .box(band_t + 2.0, spine_w, height, centered=(True, True, False))
        .translate((-(r + band_t / 2.0) + 0.5, 0, 0))
    )
    body = body.union(spine)
    plate_h = boss_space + 2.5 * bolt_dia
    plate_t = band_t + 3.0
    plate = (
        cq.Workplane("XY")
        .box(plate_t, spine_w, plate_h, centered=(True, True, False))
        .translate((-(r + band_t) - plate_t / 2.0 + 1.0, 0, height / 2.0 - plate_h / 2.0))
    )
    br = bolt_dia / 2.0
    for z in [height / 2.0 - boss_space / 2.0, height / 2.0 + boss_space / 2.0]:
        cutter = (
            cq.Workplane("YZ")
            .circle(br)
            .extrude(plate_t + 6.0)
            .translate((-(r + band_t) - plate_t - 3.0, 0, z))
        )
        plate = plate.cut(cutter)
    body = body.union(plate)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "top_entry_cage":
    result = build_top_entry_cage()
elif target_part == "accessory_mount":
    result = build_accessory_mount()
else:
    result = build_cage()
