"""
Board Wall Rack — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall bracket that holds a ski, snowboard, or SUP paddle by cradling it in a
horizontal slot sized to the board/shaft thickness. Print a pair and mount them
apart to carry a board flat against the wall. The board slot is the shared
interface; three variants set the slot width and arm length.

Three parts (dispatched by `target_part`):
  * "ski_rack"       — a narrow-slot arm for skis (holds a pair on edge).
  * "snowboard_rack" — a wider-slot, longer arm for a snowboard laid flat.
  * "paddle_rack"    — a small cradle arm for a SUP/kayak paddle shaft.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `slot_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
target_part = str(PARAM(lambda: target_part, "ski_rack"))  # ski|snowboard|paddle

slot_w    = float(PARAM(lambda: slot_w,   28.0))  # board thickness the slot holds (mm)
arm_len   = float(PARAM(lambda: arm_len,  90.0))  # how far the arm reaches out (mm)
arm_w     = float(PARAM(lambda: arm_w,    40.0))  # arm width along the wall (mm)
wall      = float(PARAM(lambda: wall,      6.0))  # bracket wall thickness (mm)
plate_h   = float(PARAM(lambda: plate_h,  90.0))  # wall plate height (mm)
screw_dia = float(PARAM(lambda: screw_dia, 5.0))  # wall screw clearance (mm)
lip_h     = float(PARAM(lambda: lip_h,    22.0))  # front retaining lip height (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
slot_w    = max(8.0, min(slot_w, 90.0))
arm_len   = max(45.0, min(arm_len, 220.0))
arm_w     = max(20.0, min(arm_w, 120.0))
wall      = max(4.0, min(wall, 12.0))
plate_h   = max(50.0, min(plate_h, 200.0))
screw_dia = max(3.5, min(screw_dia, 10.0))
lip_h     = max(10.0, min(lip_h, 60.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def wall_plate(w, h, t):
    """Vertical wall plate in the XZ face; thickness along +Y into wall (y:0→−t),
    centred in X, base at z=0. Rounded outer vertical corners."""
    plate = (
        cq.Workplane("XY")
        .box(w, t, h, centered=(True, True, False))
        .translate((0, -t / 2.0, 0))
    )
    r = min(5.0, w * 0.15, h * 0.15)
    if r > 0.3:
        try:
            plate = plate.edges("|Z").fillet(r)
        except Exception:
            pass
    return plate


def screw_holes(body, w, h, t):
    """Two vertical screw holes through the plate (bored +Y)."""
    r = screw_dia / 2.0
    inset = max(14.0, screw_dia + 8.0)
    for z in [inset, h - inset]:
        cutter = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(t + 6.0)
            .translate((0, 3.0, z))
        )
        body = body.cut(cutter)
    return body


def build_bracket(slot, reach, aw, lip):
    """A wall bracket: a plate, a horizontal arm reaching out at mid-height with a
    board slot cut into its top, and an up-turned front lip retaining the board."""
    pw = max(aw, slot + 2.0 * wall + 6.0)
    ph = plate_h
    body = wall_plate(pw, ph, wall + 2.0)

    # Arm at mid-height reaching +Y.
    arm_z = ph * 0.42
    arm_h = slot + 2.0 * wall            # arm tall enough to hold the slot
    arm = (
        cq.Workplane("XY")
        .box(aw, reach, arm_h, centered=(True, False, False))
        .translate((0, 0, arm_z))
    )
    body = body.union(arm)

    # Board slot: an open channel cut into the TOP of the arm, running +Y, so the
    # board drops in edge-down. Leave `wall` of floor beneath and side walls.
    slot_cut = (
        cq.Workplane("XY")
        .box(slot, reach - wall, arm_h, centered=(True, False, False))
        .translate((0, wall, arm_z + wall))
    )
    body = body.cut(slot_cut)

    # Up-turned front lip so the board cannot slide off the end.
    front_lip = (
        cq.Workplane("XY")
        .box(aw, wall, lip, centered=(True, False, False))
        .translate((0, reach, arm_z))
    )
    body = body.union(front_lip)

    # Gusset under the arm for strength (triangular brace to the plate).
    gus = (
        cq.Workplane("YZ")
        .polyline([(0, 0), (reach * 0.6, 0), (0, -arm_z * 0.8)]).close()
        .extrude(wall)
        .translate((-wall / 2.0, 0, arm_z))
    )
    body = body.union(gus)

    body = screw_holes(body, pw, ph, wall + 2.0)
    # Soften the slot mouth so it doesn't scratch the board (non-fatal).
    try:
        body = body.edges("|Y and >Z").fillet(min(2.0, wall * 0.3))
    except Exception:
        pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_ski_rack():
    # Narrow slot for skis (a pair rests on edge); shorter arm.
    return build_bracket(slot_w, arm_len, arm_w, lip_h)


def build_snowboard_rack():
    # Wider slot and longer arm for a snowboard laid flat.
    s = max(slot_w, 30.0)
    return build_bracket(s + 10.0, max(arm_len, 120.0), max(arm_w, 55.0), lip_h)


def build_paddle_rack():
    # Small cradle for a paddle shaft; narrow slot, short arm.
    s = min(slot_w, 45.0)
    return build_bracket(min(s, 40.0), min(arm_len, 70.0), min(arm_w, 45.0), max(lip_h, 18.0))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "snowboard_rack":
    result = build_snowboard_rack()
elif target_part == "paddle_rack":
    result = build_paddle_rack()
else:
    result = build_ski_rack()
