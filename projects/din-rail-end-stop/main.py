"""
DIN Rail End Stop — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The parts that terminate a rail, rather than ride on it.

The commons has seven cartridges that clip TO DIN EN 60715 TS35 rail — modules,
relays, terminal combs, covers, busbar supports, dev-board trays, clips. Not one
of them addresses THE RAIL: nothing stops a row of modules sliding along it,
nothing spaces two groups apart, and nothing fills an empty way in a consumer
unit so fingers and dust stay out. A rail with no end stop is a rail whose
contents migrate every time the cabinet is transported.

Seven existing members mate a single rail interface, at the lowest build effort
in the tranche — this is the largest genuine-standard edge yield per unit of
work in the whole wave.

Modes are dispatched via `target_part`:
  * "end_stop"     — the terminating bracket: clip back, a tall stop face, and
                     an optional marker-card slot.
  * "rail_spacer"  — a low spacer that fills a gap between two groups of
                     modules, with a comb of cable slots across its top.
  * "blank_module" — a blank on the modular device pitch, filling an empty way
                     so the busbar behind it is not open to a finger.

Rail geometry is not invented here: RAIL_SPAN / LIP_GRIP / CLEAR and the hook
profile mirror `din-module`'s published geometry exactly, so an end stop and a
module grip the same rail identically.

Watertightness strategy:
  * The body width ALWAYS contains the hooks. Deriving it from a user dimension
    alone lets a narrow body sit entirely inside the hook span — the hooks then
    touch nothing, and the result is three separate watertight solids that no
    watertightness check would catch.
  * Union OVERLAPS, never tangents: hooks reach up into the body they fuse to.
  * Every slot is bounded INSIDE the blank with a margin that scales, and slot
    counts are derived from the space that survives the margin rather than
    picked first and trimmed.
  * No sealed void: the blank module is solid, not hollow.
  * No fillet on any edge a slot has touched.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── DIN EN 60715 TS35 top-hat rail ───────────────────────────────────────────
# Mirrors `din-module`'s published constants exactly.
RAIL_SPAN = 35.0
LIP_GRIP = 5.0
CLEAR = 0.35
HOOK_WALL = 2.6

# DIN 43880 modular device pitch: one module unit is 17.5 mm along the rail.
# That pitch is the defining figure of the format and is asserted; the front
# height and depth are exposed as sliders with common defaults instead, because
# they vary by depth class and were not confirmed against a primary table.
MODULE_PITCH = 17.5

OVERLAP = 1.0


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "end_stop"))
rail_depth_class = str(PARAM(lambda: rail_depth_class, "ts35_7v5"))
label_slot = str(PARAM(lambda: label_slot, "slot"))

width = float(PARAM(lambda: width, 10.0))
stop_h = float(PARAM(lambda: stop_h, 40.0))
module_units = float(PARAM(lambda: module_units, 1.0))
module_h = float(PARAM(lambda: module_h, 45.0))
module_depth = float(PARAM(lambda: module_depth, 45.0))
plate_th = float(PARAM(lambda: plate_th, 3.0))
spring_thick = float(PARAM(lambda: spring_thick, 2.0))
cable_slots = float(PARAM(lambda: cable_slots, 3.0))

width = max(4.0, min(width, 40.0))
stop_h = max(12.0, min(stop_h, 70.0))
module_units = max(1.0, min(round(module_units), 8.0))
module_h = max(25.0, min(module_h, 70.0))
module_depth = max(20.0, min(module_depth, 80.0))
plate_th = max(2.5, min(plate_th, 8.0))
spring_thick = max(1.2, min(spring_thick, 4.0))
cable_slots = max(0.0, min(round(cable_slots), 8.0))

RAIL_DEPTH = 15.0 if rail_depth_class == "ts35_15" else 7.5
JAW_H = RAIL_DEPTH + 2.5
CATCH = max(1.5, min(LIP_GRIP - 1.0, 3.0))

# The body must ALWAYS contain the hooks. A body narrower than the hook span
# would sit entirely between them: the hooks would then touch nothing, and the
# render would be three separate watertight solids — a failure `is_watertight`
# cannot see, because each of the three is perfectly closed.
MIN_BODY_W = RAIL_SPAN + 2.0 * HOOK_WALL + 4.0

if target_part == "blank_module":
    BODY_W = max(module_h, MIN_BODY_W)
    BODY_L = module_units * MODULE_PITCH
else:
    BODY_W = MIN_BODY_W
    BODY_L = width

HOOK_LEN = BODY_L


# ── Rail hooks (mirroring din-module) ────────────────────────────────────────
def _extrude_profile_xz(pts, length):
    """Close (x, z) points on XZ and extrude symmetrically about Y = 0."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)


def _fixed_hook():
    """Rigid hook on the +X side (the fixed reference jaw)."""
    x_in = RAIL_SPAN / 2.0 - CLEAR
    x_wall = RAIL_SPAN / 2.0 + HOOK_WALL
    x_catch = x_in - CATCH
    pts = [
        (x_catch, plate_th), (x_wall, plate_th),
        (x_wall, -JAW_H), (x_catch, -JAW_H),
        (x_catch, -JAW_H + HOOK_WALL), (x_in, -JAW_H + HOOK_WALL),
        (x_in, 0.0), (x_catch, 0.0),
    ]
    return _extrude_profile_xz(pts, HOOK_LEN)


def _spring_hook():
    """COMPLIANT sprung hook on the -X side: a folded cantilever that flexes out
    over the lip and springs back. The bend energy lives in the beam, so the
    wall is never held in permanent strain and the stop does not creep off the
    rail over years in a warm cabinet."""
    t = spring_thick
    x_lip = -RAIL_SPAN / 2.0
    x_out = x_lip - CLEAR
    x_root_in = x_lip + 7.0
    x_catch = x_out + CATCH
    outer = [
        (x_root_in, plate_th), (x_out, plate_th),
        (x_out, -JAW_H), (x_catch, -JAW_H),
    ]
    inner = [
        (x_catch, -JAW_H + t), (x_out + t, -JAW_H + t),
        (x_out + t, plate_th - t - 2.0), (x_root_in, plate_th - t - 2.0),
    ]
    return _extrude_profile_xz(outer + inner, HOOK_LEN)


def with_hooks(body):
    return body.union(_fixed_hook()).union(_spring_hook())


def _side_pocket(y_sign, depth, size_x, size_z, z0):
    """A tool that recesses a SIDE face by `depth` and runs 1 mm past it.

    Running past the face is the whole point. A tool sized `depth + 1` but
    CENTRED on the material stops short of the face and leaves an internal
    cavity — the solid is then perfectly watertight and has two bodies, because
    trimesh counts the cavity's inner shell as a body of its own. That is the
    sealed-void trap, and it is invisible to every watertightness check."""
    y_face = y_sign * (BODY_L / 2.0)
    y_lo = y_face - y_sign * depth
    centre_y = (y_lo + (y_face + y_sign * 1.0)) / 2.0
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, centre_y, z0))
        .box(size_x, depth + 1.0, size_z, centered=(True, True, False))
    )


def cut_label(body, z_face, face_w, face_l, depth):
    """Recess a marker card into a face, bounded inside it with a real margin.

    A rail whose modules are not labelled is a rail nobody will touch, and a
    label taped to a printed part falls off in a warm cabinet."""
    if label_slot != "slot":
        return body
    margin = 3.0
    sw = face_w - 2.0 * margin
    sl = face_l - 2.0 * margin
    if sw < 6.0 or sl < 4.0 or depth < 0.8:
        return body
    tool = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, z_face - depth))
        .box(sw, sl, depth + 1.0, centered=(True, True, False))
    )
    try:
        return body.cut(tool)
    except Exception:
        return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_end_stop():
    """The terminating bracket: clip back, a tall stop face, a marker recess."""
    body = (
        cq.Workplane("XY")
        .box(BODY_W, BODY_L, stop_h, centered=(True, True, False))
    )
    body = with_hooks(body)

    # Lighten the tall face without opening it: a bounded pocket on ONE side,
    # never a through window, so the stop face stays continuous.
    pocket_d = min(max(1.5, plate_th * 0.5), BODY_L * 0.35)
    pw = BODY_W - 2.0 * 5.0
    ph = stop_h - plate_th - 8.0
    if pw > 8.0 and ph > 8.0 and pocket_d >= 1.0:
        try:
            body = body.cut(_side_pocket(1.0, pocket_d, pw, ph, plate_th + 4.0))
        except Exception:
            pass

    body = cut_label(body, stop_h, BODY_W, BODY_L, min(1.2, plate_th * 0.4))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_rail_spacer():
    """A low spacer between two groups of modules, combed for cable routing."""
    height = max(plate_th + 4.0, plate_th + 6.0)
    body = (
        cq.Workplane("XY")
        .box(BODY_W, BODY_L, height, centered=(True, True, False))
    )
    body = with_hooks(body)

    # Cable comb across the top. The count is derived from the space that
    # actually survives the end margins — a count picked first and trimmed later
    # is how a slot ends up cutting through the wall it was meant to sit inside.
    n = int(cable_slots)
    if n >= 1:
        margin = 4.0
        avail = BODY_W - 2.0 * margin
        slot_w = min(4.0, max(1.6, BODY_L * 0.5))
        pitch = avail / n
        if pitch >= slot_w + 1.5 and avail > 0:
            depth = min(height - plate_th - 1.0, height * 0.5)
            if depth >= 1.0:
                pts = [(-avail / 2.0 + pitch * (i + 0.5), 0.0) for i in range(n)]
                for (x, _y) in pts:
                    tool = (
                        cq.Workplane("XY")
                        .transformed(offset=cq.Vector(x, 0.0, height - depth))
                        .box(slot_w, BODY_L + 2.0, depth + 1.0,
                             centered=(True, True, False))
                    )
                    try:
                        body = body.cut(tool)
                    except Exception:
                        pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_blank_module():
    """A blank on the modular device pitch, filling an empty way.

    Solid, not hollow: a shelled blank would seal a void, and a sealed void
    meshes as two bodies however valid the kernel reports the solid to be."""
    body = (
        cq.Workplane("XY")
        .box(BODY_W, BODY_L, module_depth, centered=(True, True, False))
    )
    body = with_hooks(body)

    # Two bounded finger recesses so the blank can be pulled out of a live
    # board without a screwdriver near a busbar.
    grip_d = min(2.0, BODY_L * 0.3)
    if grip_d >= 0.8 and module_depth > 14.0:
        for sign in (-1.0, 1.0):
            try:
                body = body.cut(_side_pocket(sign, grip_d, BODY_W - 10.0, 6.0,
                                             module_depth - 10.0))
            except Exception:
                pass

    body = cut_label(body, module_depth, BODY_W, BODY_L, min(1.2, 1.2))

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "end_stop": build_end_stop,
    "rail_spacer": build_rail_spacer,
    "blank_module": build_blank_module,
}

result = _dispatch.get(target_part, build_end_stop)()
