"""
Sharps Container Lid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Turns any bucket, jar, or carboy into a sharps container. A press-on lid with a
ONE-WAY BAFFLE: the drop slot is offset from the internal chute mouth, so a
needle goes in and cannot be shaken, tipped, or fished back out. A separate
NEEDLE-HUB SLOT in the top face lets a syringe hub be twisted off and dropped
without the user touching the needle — the slot is parameterised on hub
diameter, not on any one syringe brand.

The bore series is the SAME bucket/carboy bore already used across the commons,
so a lid generated at a given `bore_dia` fits the same vessel a carboy cap or
bucket lid was generated for.

Modes:
  - baffle_lid : press-on lid with the offset one-way baffle chute + hub slot.
  - screw_lid  : the same baffle on a coarse-thread cap for a threaded carboy.
  - closure_cap: a plain solid cap that seals a FULL container before disposal —
                 the second half of the safety story.

Watertight strategy: the lid is ONE revolved/extruded solid. The skirt is a
single annular cut; the chute is a solid tube UNIONED into the underside before
its own bore is cut, so the baffle never floats; the drop slot and hub slot are
full-depth cuts through the top plate only. Every derived radius is clamped so
the chute can never intersect the skirt wall at any parameter extreme.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

This is a printable HARM-REDUCTION aid, not a certified FDA/NOM sharps
container. It does not replace regulated clinical waste handling; use it where
the regulated option is genuinely unavailable, and dispose of the sealed
container through a proper waste stream.
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
target_part = str(PARAM(lambda: target_part, "baffle_lid"))
# "baffle_lid" | "screw_lid" | "closure_cap"

bore_dia   = float(PARAM(lambda: bore_dia,  95.0))   # vessel mouth OUTER diameter
clearance  = float(PARAM(lambda: clearance,  0.4))   # per-side press-fit gap
wall       = float(PARAM(lambda: wall,       2.6))   # skirt wall thickness
skirt_h    = float(PARAM(lambda: skirt_h,   14.0))   # how far the skirt grips down
top_th     = float(PARAM(lambda: top_th,     3.2))   # top plate thickness
slot_w     = float(PARAM(lambda: slot_w,    22.0))   # drop-slot width
slot_l     = float(PARAM(lambda: slot_l,    30.0))   # drop-slot length
chute_off  = float(PARAM(lambda: chute_off, 16.0))   # baffle offset — the one-way trick
chute_h    = float(PARAM(lambda: chute_h,   22.0))   # internal chute depth
hub_dia    = float(PARAM(lambda: hub_dia,    7.6))   # needle-hub diameter (Luer ~7.5 mm)
thread_pitch = float(PARAM(lambda: thread_pitch, 6.0))  # coarse thread pitch (screw_lid)

# ── Clamps ───────────────────────────────────────────────────────────────────
bore_dia     = max(30.0, min(bore_dia, 320.0))
clearance    = max(0.0,  min(clearance, 2.0))
wall         = max(1.5,  min(wall, 10.0))
skirt_h      = max(4.0,  min(skirt_h, 60.0))
top_th       = max(1.5,  min(top_th, 12.0))
slot_w       = max(4.0,  min(slot_w, 120.0))
slot_l       = max(4.0,  min(slot_l, 200.0))
chute_off    = max(2.0,  min(chute_off, 150.0))
chute_h      = max(4.0,  min(chute_h, 120.0))
hub_dia      = max(2.0,  min(hub_dia, 30.0))
thread_pitch = max(2.0,  min(thread_pitch, 20.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
R_IN = bore_dia / 2.0 + clearance      # skirt inner radius (over the vessel rim)
R_OUT = R_IN + wall                    # lid outer radius

# The slot must fit inside the top plate with a real land at the rim.
LAND = wall + 2.0
SLOT_W = min(slot_w, 2.0 * (R_IN - LAND) * 0.9)
SLOT_W = max(2.0, SLOT_W)
SLOT_L = min(slot_l, 2.0 * (R_IN - LAND) * 0.9)
SLOT_L = max(2.0, SLOT_L)

# The chute mouth is OFFSET from the slot. Both must stay inside the land, so
# the offset is capped by how much room is left.
MAX_OFF = max(0.0, (R_IN - LAND) - max(SLOT_W, SLOT_L) / 2.0)
OFF = min(chute_off, MAX_OFF)

# Chute cross-section: a tube that swallows the slot and is walled.
CH_IN_W = SLOT_W + 1.5
CH_IN_L = SLOT_L + 1.5
CH_W = CH_IN_W + 2.0 * wall
CH_L = CH_IN_L + 2.0 * wall
# The chute hangs from the underside of the top plate; it must fit inside the
# skirt bore even after being shifted by OFF.
half_diag = math.hypot(CH_W, CH_L) / 2.0
FITS = (half_diag + OFF) <= (R_IN - 0.8)
CHUTE_H = min(chute_h, 200.0)

# Hub slot: a keyhole in the top plate, placed on the far side from the drop
# slot so a hub twist-off never lands over the open chute.
HUB_R = hub_dia / 2.0
HUB_SLOT_L = HUB_R * 3.2
HUB_X = -(R_IN - LAND - HUB_R - 1.0)
HUB_OK = HUB_X < -(max(SLOT_W, SLOT_L) / 2.0 + HUB_R + 2.0) and HUB_R > 0.5

TOTAL_H = top_th + skirt_h


# ── Helpers ──────────────────────────────────────────────────────────────────
def lid_blank():
    """Solid disc + skirt as ONE body: an outer cylinder with an annular
    recess cut for the vessel rim, leaving a top plate."""
    body = cq.Workplane("XY").circle(R_OUT).extrude(TOTAL_H)
    recess = (
        cq.Workplane("XY")
        .circle(R_IN)
        .extrude(skirt_h + 0.1)
    )
    return body.cut(recess)


def drop_slot(z0, z1):
    """The rounded drop slot through the top plate, centred at +OFF/2 in X."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(OFF / 2.0, 0, z0 - 0.5))
        .rect(SLOT_W, SLOT_L)
        .extrude((z1 - z0) + 1.0)
    )


def chute_solid(z_top):
    """Solid outer body of the offset chute, hanging DOWN from the top plate.

    Offset by -OFF in X relative to the slot, so the path from slot to chute
    mouth is an S: a needle drops in, falls sideways down the chute, and cannot
    be shaken back up through the offset."""
    if not FITS or CHUTE_H < 0.5:
        return None
    z0 = z_top - CHUTE_H
    # The chute must OVERLAP the top plate, not merely touch its underside.
    # `z_top` is the plate's underside; extruding exactly CHUTE_H ends flush
    # with it, and a flush union is not a union: OCCT reports two solids and the
    # exported mesh is two bodies (a chute floating inside the lid). Extrude a
    # real distance INTO the plate — the drop slot and chute bore are cut
    # afterwards, so this extra material is removed where it must be anyway.
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-OFF / 2.0, 0, z0))
        .rect(CH_W, CH_L)
        .extrude(CHUTE_H + max(0.6, top_th * 0.6))
    )


def chute_bore(z_top):
    """The chute's own passage, cut AFTER the solid is unioned in.

    Deliberately stops at the plate's UNDERSIDE (z_top) and no higher. The drop
    slot overlaps the chute mouth in plan, so the slot alone breaches the plate
    and the needle has a path; carrying this bore up through the plate as well
    would open a second, straight-down hole over the chute — exactly the
    shake-back-out path the offset baffle exists to prevent.

    The extra material the chute solid now pushes into the plate is therefore
    removed by the slot where a path is wanted, and kept everywhere else."""
    if not FITS or CHUTE_H < 0.5:
        return None
    z0 = z_top - CHUTE_H - 0.5
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-OFF / 2.0, 0, z0))
        .rect(CH_IN_W, CH_IN_L)
        .extrude(CHUTE_H + 0.5)
    )


def hub_slot(z0, z1):
    """Keyhole for twisting a needle hub off a syringe: a round seat opening
    into a narrow neck that grips the hub flats."""
    if not HUB_OK:
        return None
    seat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(HUB_X, 0, z0 - 0.5))
        .circle(HUB_R)
        .extrude((z1 - z0) + 1.0)
    )
    neck_w = max(0.5, HUB_R * 0.72)
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(HUB_X + HUB_SLOT_L / 2.0, 0, z0 - 0.5))
        .rect(HUB_SLOT_L, neck_w)
        .extrude((z1 - z0) + 1.0)
    )
    return seat.union(neck)


# ── Part builders ────────────────────────────────────────────────────────────
def build_baffle_lid():
    """Press-on lid: skirt + top plate + offset chute + drop slot + hub slot."""
    body = lid_blank()
    z_top = TOTAL_H
    # Chute solid FIRST (union), so nothing floats.
    ch = chute_solid(skirt_h)
    if ch is not None:
        body = body.union(ch)
    # Now the cuts.
    body = body.cut(drop_slot(skirt_h, z_top))
    cb = chute_bore(skirt_h)
    if cb is not None:
        body = body.cut(cb)
    hs = hub_slot(skirt_h, z_top)
    if hs is not None:
        body = body.cut(hs)
    try:
        body = body.faces(">Z").edges("%CIRCLE").chamfer(min(0.8, top_th * 0.3))
    except Exception:
        pass
    return body


def build_screw_lid():
    """The same baffle on a coarse-thread cap: instead of a smooth skirt bore,
    the skirt carries a helical thread rib for a threaded carboy neck."""
    body = build_baffle_lid()
    # Coarse "buttress" retention: a stack of annular ribs on the skirt bore at
    # the thread pitch. Each rib is a full annulus grown INTO the skirt wall
    # (outer radius stays inside R_OUT), so the union can never breach the
    # skirt and the result is always one body. A swept helix would be prettier
    # but is kernel-version-fragile; the ring stack performs the same retention
    # on a printed lid and is deterministic at every parameter extreme.
    rib_r = min(wall * 0.30, thread_pitch * 0.22, 1.4)
    rib_r = max(0.3, rib_r)
    n = max(1, int((skirt_h - 1.0) // thread_pitch))
    for i in range(n):
        z = 0.6 + i * thread_pitch
        if z + 2.0 * rib_r > skirt_h - 0.4:
            break
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z))
            .circle(R_IN + 0.05)
            .circle(max(0.2, R_IN - rib_r))
            .extrude(2.0 * rib_r)
        )
        body = body.union(ring)
    return body


def build_closure_cap():
    """Plain solid cap that permanently seals a full container: same skirt fit,
    no openings, plus a raised grip ring on top."""
    body = lid_blank()
    grip_r = min(R_OUT - wall * 0.5, R_IN * 0.55)
    grip_r = max(1.0, grip_r)
    grip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, TOTAL_H - 0.2))
        .circle(grip_r)
        .circle(max(0.5, grip_r - max(1.5, wall)))
        .extrude(max(1.5, top_th * 0.8) + 0.2)
    )
    body = body.union(grip)
    try:
        body = body.faces(">Z").edges("%CIRCLE").chamfer(min(0.6, top_th * 0.25))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "screw_lid":
    result = build_screw_lid()
elif target_part == "closure_cap":
    result = build_closure_cap()
else:  # "baffle_lid"
    result = build_baffle_lid()
