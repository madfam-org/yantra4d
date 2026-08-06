"""
Instrument Wall Hook — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall hanger that cradles a stringed instrument by its neck between two arms
that reach under the headstock. Sized by the neck width so the cradle fits the
instrument exactly; a screw-through back plate mounts it into a wall stud.

Three parts (dispatched by `target_part`):
  * "guitar_hook"  — full-size cradle for a guitar / bass neck.
  * "violin_hook"  — a narrower cradle for a violin / viola / ukulele neck.
  * "multi_hook"   — a wider back plate carrying TWO cradles side by side.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `neck_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

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
target_part = str(PARAM(lambda: target_part, "guitar_hook"))  # guitar|violin|multi

neck_w      = float(PARAM(lambda: neck_w,      52.0))  # neck width at the nut (mm)
arm_gap     = float(PARAM(lambda: arm_gap,     32.0))  # vertical opening for the neck (mm)
arm_thick   = float(PARAM(lambda: arm_thick,   12.0))  # cradle arm thickness (mm)
reach       = float(PARAM(lambda: reach,       55.0))  # how far the arms stick out (mm)
plate_w     = float(PARAM(lambda: plate_w,     70.0))  # back plate width (mm)
plate_h     = float(PARAM(lambda: plate_h,     90.0))  # back plate height (mm)
plate_t     = float(PARAM(lambda: plate_t,      8.0))  # back plate thickness (mm)
screw_dia   = float(PARAM(lambda: screw_dia,    5.0))  # stud-screw clearance dia (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
neck_w    = max(18.0, min(neck_w, 90.0))
arm_gap   = max(18.0, min(arm_gap, 70.0))
arm_thick = max(6.0, min(arm_thick, 22.0))
reach     = max(30.0, min(reach, 110.0))
plate_t   = max(5.0, min(plate_t, 16.0))
screw_dia = max(3.0, min(screw_dia, 9.0))
# Plate must comfortably contain the cradle mouth.
plate_w   = max(neck_w + 2.0 * arm_thick + 8.0, min(plate_w, 260.0))
plate_h   = max(arm_gap + 40.0, min(plate_h, 200.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def back_plate(w, h, t):
    """Vertical wall plate in the XZ face: thickness along +Y (into the wall at
    y=0 back face → y=-t), centred in X, base at z=0. Its four outer vertical
    (|Z) corners are rounded here — filleting the plate BEFORE the cradle union
    keeps the operation on clean isolated edges (a whole-assembly fillet grazes
    the cradle seam and tessellates non-watertight for some proportions)."""
    plate = (
        cq.Workplane("XY")
        .box(w, t, h, centered=(True, True, False))
        .translate((0, -t / 2.0, 0))
    )
    r = min(6.0, w * 0.15, h * 0.15)
    if r > 0.3:
        try:
            plate = plate.edges("|Z").fillet(r)
        except Exception:
            pass
    return plate


def stud_holes(body, w, h, t, cx):
    """Two vertical stud screws through the plate at column x=cx (bored +Y)."""
    r = screw_dia / 2.0
    inset = max(16.0, screw_dia + 10.0)
    zs = [inset, h - inset]
    for z in zs:
        cutter = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(t + 6.0)
            .translate((cx, 3.0, z))
        )
        body = body.cut(cutter)
    return body


def cradle_arm(cx, base_z):
    """One neck cradle centred at plate column x=cx, whose neck opening floor is
    at z=base_z. Two prongs (top + bottom) reach out +Y with an up-turned lip so
    the neck cannot slip out. Built as solid blocks + a rounded trough."""
    half = neck_w / 2.0
    prong_w = arm_thick
    # Bottom prong: a shelf the neck rests on, with a raised front lip.
    lip_h = arm_thick + 6.0
    shelf = (
        cq.Workplane("XY")
        .box(neck_w + 2.0 * prong_w, reach, arm_thick, centered=(True, False, False))
        .translate((cx, 0, base_z))
    )
    # Raised front lip across the mouth end so a neck cannot roll off.
    lip = (
        cq.Workplane("XY")
        .box(neck_w + 2.0 * prong_w, arm_thick, lip_h, centered=(True, False, False))
        .translate((cx, reach - arm_thick, base_z))
    )
    # Two side walls that cup the neck sides (the "arms").
    side_l = (
        cq.Workplane("XY")
        .box(prong_w, reach, arm_gap + arm_thick, centered=(False, False, False))
        .translate((cx - half - prong_w, 0, base_z))
    )
    side_r = (
        cq.Workplane("XY")
        .box(prong_w, reach, arm_gap + arm_thick, centered=(False, False, False))
        .translate((cx + half, 0, base_z))
    )
    arm = shelf.union(lip).union(side_l).union(side_r)
    # Soften the neck-contact channel: cut a half-round trough along the shelf so
    # the neck rests on a rounded saddle instead of a hard edge. The scoop bottom
    # is seated `dip` mm ABOVE the shelf floor so a solid floor always remains
    # under it (a scoop that cut through the floor would leave a knife edge and
    # tessellate non-watertight).
    trough_r = min(half * 0.9, (arm_gap + arm_thick) * 0.5)
    dip = 1.2
    trough = (
        cq.Workplane("XZ")
        .circle(trough_r)
        .extrude(reach + 2.0)
        .translate((cx, -1.0, base_z + dip + trough_r))
    )
    try:
        arm = arm.cut(trough)
    except Exception:
        pass
    return arm


def build_one(cx, base_z):
    return cradle_arm(cx, base_z)


# ── Part builders ────────────────────────────────────────────────────────────
def build_guitar_hook():
    body = back_plate(plate_w, plate_h, plate_t)
    base_z = (plate_h - (arm_gap + arm_thick)) / 2.0
    body = body.union(build_one(0.0, base_z))
    body = stud_holes(body, plate_w, plate_h, plate_t, 0.0)
    return body


def build_violin_hook():
    # A narrower cradle on a smaller plate (violin / ukulele necks).
    global neck_w, plate_w, plate_h, reach
    neck_w = min(neck_w, 40.0)
    reach = min(reach, 48.0)
    pw = max(neck_w + 2.0 * arm_thick + 6.0, 56.0)
    ph = max(arm_gap + 34.0, 74.0)
    body = back_plate(pw, ph, plate_t)
    base_z = (ph - (arm_gap + arm_thick)) / 2.0
    body = body.union(build_one(0.0, base_z))
    body = stud_holes(body, pw, ph, plate_t, 0.0)
    return body


def build_multi_hook():
    # Two cradles side by side on one wide plate.
    span = neck_w + 2.0 * arm_thick + 26.0
    pw = max(plate_w, 2.0 * span + 10.0)
    ph = plate_h
    body = back_plate(pw, ph, plate_t)
    base_z = (ph - (arm_gap + arm_thick)) / 2.0
    cxs = [-span / 2.0, span / 2.0]
    for cx in cxs:
        body = body.union(build_one(cx, base_z))
        body = stud_holes(body, pw, ph, plate_t, cx)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "violin_hook":
    result = build_violin_hook()
elif target_part == "multi_hook":
    result = build_multi_hook()
else:
    result = build_guitar_hook()
