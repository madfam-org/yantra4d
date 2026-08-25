"""
Pneumatic Barb Port — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The connector that makes the soft-pneumatic family interoperable. A printable
hose-barb port sized by the INNER diameter of the silicone/PU tubing it grips:
a stack of shallow tapered barb ridges over a through-bore, on a base that is
either a bolt-through flange, a plain boss to be welded/glued into an actuator
wall, or a straight barb-to-barb coupler for splicing two tubes.

The barb series (2 / 3 / 4 mm tube ID) is the SHARED inlet interface for
`bellows-actuator`, `pneu-net-finger`, `suction-cup-bellows` and
`vacuum-manifold-block` — a port generated at one `tube_id` mates every
cartridge in the family generated at the same `tube_id`.

Modes:
  - flange_port   : barb on a round bolt-through flange (mounts to a chamber wall)
  - boss_port     : barb on a plain cylindrical boss (press/glue into a bore)
  - barb_coupler  : symmetric barb-to-barb straight splice

Watertight strategy: every body is ONE revolved/extruded solid with a single
through-bore cut last. Barb ridges are lofted annular collars unioned onto the
stem, never separate floating rings; the flange is a disc unioned coaxially.
All derived dimensions are clamped so the bore can never reach or exceed the
outer wall at any parameter extreme.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Printed barbs are for LOW-PRESSURE pneumatics (soft actuators, vacuum). Print
solid-ish (>=4 perimeters) and check for leaks before pressurising.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "flange_port"))
# "flange_port" | "boss_port" | "barb_coupler"

tube_id   = float(PARAM(lambda: tube_id,    3.0))   # tubing INNER diameter (mm)
barb_count = int(PARAM(lambda: barb_count,  3))     # number of barb ridges
barb_pitch = float(PARAM(lambda: barb_pitch, 3.0))  # axial spacing of ridges
barb_rise  = float(PARAM(lambda: barb_rise,  0.7))  # how far a ridge stands proud
bore       = float(PARAM(lambda: bore,       1.6))  # air passage through-bore dia
wall       = float(PARAM(lambda: wall,       1.6))  # stem wall around the bore
flange_dia = float(PARAM(lambda: flange_dia, 16.0)) # bolt flange outer diameter
flange_th  = float(PARAM(lambda: flange_th,  3.0))  # flange plate thickness
bolt_dia   = float(PARAM(lambda: bolt_dia,   3.4))  # M3 clearance
bolt_count = int(PARAM(lambda: bolt_count,   2))    # bolts around the flange

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_id    = max(1.5, min(tube_id, 10.0))
barb_count = max(1, min(barb_count, 8))
barb_pitch = max(1.6, min(barb_pitch, 8.0))
barb_rise  = max(0.2, min(barb_rise, 2.0))
bore       = max(0.8, min(bore, 8.0))
wall       = max(0.8, min(wall, 4.0))
flange_dia = max(8.0, min(flange_dia, 60.0))
flange_th  = max(1.5, min(flange_th, 10.0))
bolt_dia   = max(1.5, min(bolt_dia, 8.0))
bolt_count = max(0, min(bolt_count, 8))

# ── Derived, clamped so the solid can never self-destruct ────────────────────
# The stem must be thick enough to hold the bore. Stem OD is driven by the tube
# ID (slight interference so the tube stretches over it).
STEM_R = max(tube_id / 2.0, bore / 2.0 + wall)
# Bore can never eat the stem wall: leave >= 0.6 mm of material per side.
BORE_R = min(bore / 2.0, STEM_R - 0.6)
BORE_R = max(0.35, BORE_R)
BARB_R = STEM_R + barb_rise
STEM_L = barb_pitch * (barb_count + 0.6) + 1.5   # stem length covering all barbs

# Flange must always be wider than the barb crest plus a bolt land.
FLANGE_R = max(flange_dia / 2.0, BARB_R + bolt_dia + 2.4)
BOLT_ORBIT = (BARB_R + FLANGE_R) / 2.0
# Bolt hole must fit between barb crest and flange rim.
BOLT_R = min(bolt_dia / 2.0, (FLANGE_R - BARB_R) / 2.0 - 0.5)
BOLT_R = max(0.5, BOLT_R)


# ── Helpers ──────────────────────────────────────────────────────────────────
def barbed_stem(z0, length, flip=False):
    """A plain stem cylinder from z0 with `barb_count` tapered ridges unioned on.

    Each ridge is a loft from a full-radius circle to the stem radius — a cone
    that points AWAY from the insertion end, so the tube slides on and locks.
    Returned as one fused solid (no bore yet)."""
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(STEM_R)
        .extrude(length)
    )
    ridge_h = min(barb_pitch * 0.75, barb_rise * 3.0 + 0.8)
    for i in range(barb_count):
        # Ridge base measured from the free (insertion) end of the stem.
        d = 1.0 + i * barb_pitch
        zb = (z0 + length - d - ridge_h) if not flip else (z0 + d)
        # Keep the whole ridge inside the stem span.
        zb = max(z0 + 0.2, min(zb, z0 + length - ridge_h - 0.2))
        if not flip:
            r_lo, r_hi = BARB_R, STEM_R
        else:
            r_lo, r_hi = STEM_R, BARB_R
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(r_lo)
            .workplane(offset=ridge_h)
            .circle(r_hi)
            .loft(ruled=True)
        )
        body = body.union(ridge)
    return body


def through_bore(z0, z1):
    """The single air passage, cut last so the result stays one shell."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 - 1.0))
        .circle(BORE_R)
        .extrude((z1 - z0) + 2.0)
    )


def bolt_ring(z0, z1):
    """Bolt clearance holes around the flange, as one fused cutting tool."""
    if bolt_count < 1:
        return None
    tool = None
    for k in range(bolt_count):
        ang = 2.0 * math.pi * k / bolt_count
        x = BOLT_ORBIT * math.cos(ang)
        y = BOLT_ORBIT * math.sin(ang)
        h = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, z0 - 1.0))
            .circle(BOLT_R)
            .extrude((z1 - z0) + 2.0)
        )
        tool = h if tool is None else tool.union(h)
    return tool


# ── Part builders ────────────────────────────────────────────────────────────
def build_flange_port():
    """Barb stem rising from a round bolt-through flange plate."""
    flange = cq.Workplane("XY").circle(FLANGE_R).extrude(flange_th)
    body = flange.union(barbed_stem(flange_th, STEM_L))
    holes = bolt_ring(0.0, flange_th)
    if holes is not None:
        body = body.cut(holes)
    body = body.cut(through_bore(0.0, flange_th + STEM_L))
    return body


def build_boss_port():
    """Barb stem on a plain cylindrical boss for press/adhesive mounting."""
    boss_r = max(STEM_R + wall + 0.8, BARB_R + 0.8)
    boss_h = max(2.5, flange_th)
    boss = cq.Workplane("XY").circle(boss_r).extrude(boss_h)
    body = boss.union(barbed_stem(boss_h, STEM_L))
    body = body.cut(through_bore(0.0, boss_h + STEM_L))
    try:
        body = body.faces("<Z").edges().chamfer(min(0.6, boss_h * 0.3))
    except Exception:
        pass
    return body


def build_barb_coupler():
    """Symmetric barb-to-barb splice: two barbed stems back-to-back around a
    central collar that stops the tube."""
    collar_h = max(1.6, wall * 1.2)
    collar_r = BARB_R + 0.6
    collar = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, STEM_L))
        .circle(collar_r)
        .extrude(collar_h)
    )
    lower = barbed_stem(0.0, STEM_L, flip=True)
    upper = barbed_stem(STEM_L + collar_h, STEM_L, flip=False)
    body = collar.union(lower).union(upper)
    body = body.cut(through_bore(0.0, 2.0 * STEM_L + collar_h))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "boss_port":
    result = build_boss_port()
elif target_part == "barb_coupler":
    result = build_barb_coupler()
else:  # "flange_port"
    result = build_flange_port()
