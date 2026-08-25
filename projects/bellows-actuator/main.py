"""
Pneumatic Bellows Actuator — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The base primitive of soft robotics. A convoluted (accordion) bellows: a hollow
column of alternating large/small annular convolutions that extends when
pressurised and returns elastically when vented. Printed in TPU it is a
single-piece linear actuator with no sliding seal, no rod, and no lubricant.

The stroke axis (+Z) is published as a CDG linear-motion interface, so a gripper
assembly can bolt a jaw to the moving cap and know its travel envelope. The
inlet is the shared barb series from `pneumatic-barb-port` (same `tube_id`),
which is also what `pneu-net-finger` and `vacuum-manifold-block` speak.

Modes:
  - bellows       : the bare convoluted column, capped both ends, barb inlet in
                    the fixed (bottom) cap.
  - bellows_flange: the same column on a bolt-through base flange so it mounts
                    to a frame; the moving cap carries a bolt boss.
  - end_cap       : just the moving cap — a plate with the tool bolt pattern,
                    printable separately in a rigid material.

Watertight strategy: the convoluted wall is built as ONE revolved solid from a
closed 2-D polyline (outer profile out-and-back, inner profile back down), then
the caps are unioned coaxially and the single barb bore is cut last. No lofted
shells, no thin-wall shelling — the profile carries the wall thickness
explicitly, so the result is always one closed manifold body.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

LOW-PRESSURE only (soft actuators run well under 2 bar). Print in TPU with
100% wall coverage; test for leaks before loading.
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
target_part = str(PARAM(lambda: target_part, "bellows"))
# "bellows" | "bellows_flange" | "end_cap"

outer_dia   = float(PARAM(lambda: outer_dia,  34.0))  # convolution crest diameter
inner_dia   = float(PARAM(lambda: inner_dia,  24.0))  # convolution root diameter
convolutions = int(PARAM(lambda: convolutions, 6))    # number of accordion folds
conv_pitch  = float(PARAM(lambda: conv_pitch,  6.0))  # axial height per fold
wall        = float(PARAM(lambda: wall,        1.2))  # bellows membrane thickness
cap_th      = float(PARAM(lambda: cap_th,      3.0))  # end-cap plate thickness
tube_id     = float(PARAM(lambda: tube_id,     3.0))  # inlet tubing inner dia (barb series)
bore        = float(PARAM(lambda: bore,        1.6))  # inlet air passage diameter
flange_dia  = float(PARAM(lambda: flange_dia, 48.0))  # base flange outer diameter
bolt_dia    = float(PARAM(lambda: bolt_dia,    3.4))  # M3 clearance
bolt_count  = int(PARAM(lambda: bolt_count,    4))    # bolts in base flange

# ── Clamps ───────────────────────────────────────────────────────────────────
outer_dia    = max(12.0, min(outer_dia, 120.0))
inner_dia    = max(6.0,  min(inner_dia, 110.0))
convolutions = max(2,    min(convolutions, 16))
conv_pitch   = max(3.0,  min(conv_pitch, 20.0))
wall         = max(0.6,  min(wall, 4.0))
cap_th       = max(1.5,  min(cap_th, 10.0))
tube_id      = max(1.5,  min(tube_id, 10.0))
bore         = max(0.8,  min(bore, 8.0))
flange_dia   = max(10.0, min(flange_dia, 200.0))
bolt_dia     = max(1.5,  min(bolt_dia, 8.0))
bolt_count   = max(0,    min(bolt_count, 12))

# ── Derived, clamped ─────────────────────────────────────────────────────────
# Crest must always clear the root by at least two wall thicknesses plus a
# printable fold radius, otherwise the convolution collapses into a tube.
R_OUT = outer_dia / 2.0
R_IN = min(inner_dia / 2.0, R_OUT - (wall * 2.0 + 0.8))
R_IN = max(2.0, R_IN)
# The bore of the column (the air volume) is inside the root radius.
R_LUMEN = max(1.0, R_IN - wall)
# Half-pitch is the axial run of one out-and-back leg.
HP = conv_pitch / 2.0
COL_H = conv_pitch * convolutions

# Inlet barb geometry (shared series with pneumatic-barb-port).
STEM_R = max(tube_id / 2.0, bore / 2.0 + 0.8)
BORE_R = min(bore / 2.0, STEM_R - 0.6, R_LUMEN - 0.4)
BORE_R = max(0.35, BORE_R)
BARB_R = STEM_R + 0.7
STEM_L = 9.0

# Base flange must clear the crest plus a bolt land.
FLANGE_R = max(flange_dia / 2.0, R_OUT + bolt_dia + 3.0)
BOLT_ORBIT = (R_OUT + FLANGE_R) / 2.0
BOLT_R = min(bolt_dia / 2.0, (FLANGE_R - R_OUT) / 2.0 - 0.6)
BOLT_R = max(0.5, BOLT_R)


# ── Helpers ──────────────────────────────────────────────────────────────────
def convoluted_profile():
    """Closed 2-D polyline in the XZ half-plane, revolved to make the bellows.

    Walks UP the outer face crest-to-root, then back DOWN the inner face offset
    inward by `wall`. Returns a list of (r, z) points forming a closed loop.
    Because the loop is explicitly closed and never crosses itself (R_IN is
    clamped to leave 2*wall of separation), the revolve is always one solid.
    """
    out = []
    z = 0.0
    out.append((R_IN, z))
    for _ in range(convolutions):
        out.append((R_OUT, z + HP))
        z += conv_pitch
        out.append((R_IN, z))
    # Now walk back down the inner face, offset inward by `wall`.
    inn = []
    z = COL_H
    inn.append((R_IN - wall, z))
    for _ in range(convolutions):
        inn.append((R_OUT - wall, z - HP))
        z -= conv_pitch
        inn.append((R_IN - wall, z))
    return out + inn


def bellows_column():
    """The convoluted wall as one revolved solid, sitting on Z=0."""
    pts = convoluted_profile()
    prof = cq.Workplane("XZ").polyline(pts).close()
    return prof.revolve(360.0, (0, 0, 0), (0, 1, 0))


def inlet_barb(z0):
    """The barb stem for the fixed cap, pointing DOWN from z0 (‑Z)."""
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0 - STEM_L))
        .circle(STEM_R)
        .extrude(STEM_L)
    )
    ridge_h = 2.0
    for i in range(2):
        zb = z0 - STEM_L + 1.0 + i * 3.2
        zb = max(z0 - STEM_L + 0.2, min(zb, z0 - ridge_h - 0.2))
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(STEM_R)
            .workplane(offset=ridge_h)
            .circle(BARB_R)
            .loft(ruled=True)
        )
        stem = stem.union(ridge)
    return stem


def bolt_ring(z0, z1):
    if bolt_count < 1:
        return None
    tool = None
    for k in range(bolt_count):
        ang = 2.0 * math.pi * k / bolt_count
        h = (
            cq.Workplane("XY")
            .transformed(
                offset=cq.Vector(
                    BOLT_ORBIT * math.cos(ang), BOLT_ORBIT * math.sin(ang), z0 - 1.0
                )
            )
            .circle(BOLT_R)
            .extrude((z1 - z0) + 2.0)
        )
        tool = h if tool is None else tool.union(h)
    return tool


# ── Part builders ────────────────────────────────────────────────────────────
def build_bellows(with_flange=False):
    """Convoluted column with a fixed bottom cap (barb inlet) and a moving top
    cap. Optionally a bolt-through base flange under the fixed cap."""
    base_h = cap_th
    body = None

    if with_flange:
        flange = cq.Workplane("XY").circle(FLANGE_R).extrude(cap_th)
        body = flange
        base_h = cap_th

    # Fixed bottom cap: a full disc the size of the root circle so it welds the
    # column shut.
    bottom = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, 0 if not with_flange else cap_th))
        .circle(R_IN)
        .extrude(cap_th)
    )
    body = bottom if body is None else body.union(bottom)

    z_col = (cap_th if not with_flange else 2.0 * cap_th)
    col = bellows_column().translate((0, 0, z_col))
    body = body.union(col)

    # Moving top cap.
    top = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_col + COL_H))
        .circle(R_IN)
        .extrude(cap_th)
    )
    body = body.union(top)

    # Base flange bolt holes.
    if with_flange:
        holes = bolt_ring(0.0, cap_th)
        if holes is not None:
            body = body.cut(holes)

    # Inlet barb hanging below the fixed cap, plus the single through-bore.
    body = body.union(inlet_barb(0.0))
    passage = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -STEM_L - 1.0))
        .circle(BORE_R)
        .extrude(STEM_L + z_col + 1.5)
    )
    body = body.cut(passage)

    # Hollow the column: one lumen from just above the fixed cap to just below
    # the moving cap. The convoluted wall already carries its own thickness, so
    # this only clears the middle.
    lumen = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_col - 0.01))
        .circle(R_LUMEN)
        .extrude(COL_H + 0.02)
    )
    body = body.cut(lumen)
    return body


def build_end_cap():
    """The moving cap on its own: a disc with a central relief and a small bolt
    pattern for attaching a tool/jaw."""
    cap_r = R_IN
    body = cq.Workplane("XY").circle(cap_r).extrude(cap_th * 1.6)
    n = max(2, min(bolt_count if bolt_count >= 2 else 3, 8))
    orbit = max(BOLT_R + 1.2, cap_r * 0.55)
    orbit = min(orbit, cap_r - BOLT_R - 1.0)
    if orbit > BOLT_R + 0.6:
        tool = None
        for k in range(n):
            ang = 2.0 * math.pi * k / n
            h = (
                cq.Workplane("XY")
                .transformed(
                    offset=cq.Vector(
                        orbit * math.cos(ang), orbit * math.sin(ang), -1.0
                    )
                )
                .circle(BOLT_R)
                .extrude(cap_th * 1.6 + 2.0)
            )
            tool = h if tool is None else tool.union(h)
        if tool is not None:
            body = body.cut(tool)
    try:
        body = body.faces(">Z").edges().chamfer(min(0.8, cap_th * 0.4))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bellows_flange":
    result = build_bellows(with_flange=True)
elif target_part == "end_cap":
    result = build_end_cap()
else:  # "bellows"
    result = build_bellows(with_flange=False)
