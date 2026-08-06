"""
Solar Panel Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Brackets and tilt legs for portable/framed solar panels on a boat, RV, van, or ground
setup. A corner bracket clamps the panel's aluminium edge frame and bolts to a surface;
a tilt leg props the panel at a chosen angle; a low-profile Z-bracket fixes it flat to a
roof. Sized by the panel edge (frame) thickness so it fits common 25–40 mm frames.

Three parts (dispatched via `target_part`):
  * "corner_bracket" — an L-corner cap that grips two panel edges and bolts down.
  * "tilt_leg"       — an adjustable prop leg: a foot + a strut set to `tilt_angle`
                       ending in an edge clip that grabs the panel frame.
  * "z_bracket"      — a low-profile Z mount: bolts flat to a roof, steps up, and its top
                       flange overlaps and clamps the panel frame edge.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `edge_t`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "corner_bracket"))  # corner_bracket|tilt_leg|z_bracket

edge_t     = float(PARAM(lambda: edge_t,     35.0))   # panel edge-frame thickness (mm)
grip_depth = float(PARAM(lambda: grip_depth, 14.0))   # how far the cap wraps over the panel face (mm)
wall       = float(PARAM(lambda: wall,        5.0))   # bracket wall thickness (mm)
bolt_dia   = float(PARAM(lambda: bolt_dia,    5.0))   # mounting bolt clearance dia (mm)
leg_len    = float(PARAM(lambda: leg_len,   120.0))   # tilt strut length (mm)
tilt_angle = float(PARAM(lambda: tilt_angle, 30.0))   # tilt-leg prop angle from horizontal (deg)
fit        = float(PARAM(lambda: fit,         0.3))   # clearance so the frame slides into the grip (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
edge_t     = max(15.0, min(edge_t, 50.0))
grip_depth = max(6.0, min(grip_depth, 30.0))
wall       = max(3.0, min(wall, 12.0))
bolt_dia   = max(2.5, min(bolt_dia, 10.0))
leg_len    = max(50.0, min(leg_len, 260.0))
tilt_angle = max(5.0, min(tilt_angle, 60.0))
fit        = max(0.0, min(fit, 1.0))

slot_t = edge_t + fit                      # frame slot width
cap_w  = slot_t + 2.0 * wall               # outside width across the gripped edge
mount_w = 40.0                             # nominal mounting-foot width (Y)


# ── Edge grip channel (a C-section that hugs the panel frame edge) ───────────
def _edge_grip(length):
    """A C-channel of `length` (along the panel edge, +Y) that slides onto the frame
    edge: a slot of width `slot_t` and depth `grip_depth`, walled on three sides. Built
    solid then the slot is cut. Returns a solid centred in Y, back wall at x=0, opening
    toward +X."""
    total_x = grip_depth + wall
    total_z = slot_t + 2.0 * wall
    block = (
        cq.Workplane("XY")
        .box(total_x, length, total_z, centered=(False, True, False))
    )
    # Slot: open toward +X, leaving a back wall (x:[0,wall]) and top/bottom walls.
    slot = (
        cq.Workplane("XY")
        .box(grip_depth + 1.0, length + 2.0, slot_t, centered=(False, True, False))
        .translate((wall, 0, wall))
    )
    return block.cut(slot)


def _bolt_foot(width, depth):
    """A flat bolt-down foot (a plate on XY, base z=0) with two clearance holes on Y."""
    foot = cq.Workplane("XY").box(width, depth, wall, centered=(True, True, False))
    sy = depth / 2.0 - max(bolt_dia, 5.0)
    for s in (-1.0, 1.0):
        hole = (
            cq.Workplane("XY").center(0.0, s * sy).circle(bolt_dia / 2.0)
            .extrude(wall + 2.0).translate((0, 0, -1.0))
        )
        foot = foot.cut(hole)
    return foot


# ── Corner bracket ────────────────────────────────────────────────────────────
def build_corner_bracket():
    """An L-corner cap: two edge grips meeting at 90° (grabbing the two panel edges that
    meet at a corner), fused to a bolt-down foot below."""
    arm = 46.0  # grip length along each edge
    grip_x = _edge_grip(arm).translate((0, arm / 2.0, 0))   # opens +X, runs +Y
    # Second grip rotated 90° about Z so it opens +Y and runs +X (the perpendicular edge).
    grip_y = _edge_grip(arm).rotate((0, 0, 0), (0, 0, 1), 90).translate((arm / 2.0, 0, 0))
    corner = grip_x.union(grip_y)
    # Bolt foot centred under the corner.
    foot = _bolt_foot(mount_w, mount_w).translate((arm * 0.32, arm * 0.32, 0))
    body = corner.union(foot)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Tilt leg ──────────────────────────────────────────────────────────────────
def build_tilt_leg():
    """An adjustable prop: a bolt-down foot, an angled strut rising at `tilt_angle`, and
    an edge clip at the top that grabs the panel frame. The strut is a solid bar so it is
    robust and watertight."""
    foot = _bolt_foot(mount_w, 46.0)
    rad = math.radians(tilt_angle)
    strut_w = wall * 2.2
    # Strut as an upright bar, then tilted about Y and dropped so its base fuses to the foot.
    strut = (
        cq.Workplane("XY")
        .box(strut_w, strut_w, leg_len, centered=(True, True, False))
    )
    strut = strut.rotate((0, 0, 0), (0, 1, 0), 90.0 - tilt_angle)
    # After tilt, translate so the lower end sits inside the foot for a volumetric fuse.
    strut = strut.translate((-leg_len * 0.5 * math.cos(rad) + strut_w * 0.5, 0, wall * 0.5))
    # Top edge clip: a short grip channel oriented to catch a horizontal frame edge.
    top_x = -leg_len * math.cos(rad) + strut_w * 0.5
    top_z = leg_len * math.sin(rad) + wall * 0.5
    clip = _edge_grip(mount_w).rotate((0, 0, 0), (0, 0, 1), 90)
    clip = clip.translate((top_x, 0, top_z))
    body = foot.union(strut)
    # Only fuse the clip if it lands above the foot (it always does for tilt>=5).
    body = body.union(clip)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Z-bracket ─────────────────────────────────────────────────────────────────
def build_z_bracket():
    """A low-profile Z mount: a bottom foot bolts to the roof, a vertical web steps up by
    the frame thickness, and a top flange reaches back over the panel frame to clamp it
    flat. All prismatic — robust and watertight."""
    step_h = edge_t + wall            # step height clears the frame
    foot_d = 40.0
    reach = grip_depth + wall
    # Bottom foot (roof side), opening toward +X.
    foot = _bolt_foot(mount_w, foot_d)
    # Vertical web rising at the back of the foot.
    web = (
        cq.Workplane("XY")
        .box(wall, foot_d, step_h, centered=(True, True, False))
        .translate((-mount_w / 2.0 + wall / 2.0, 0, 0))
    )
    # Top flange reaching forward over the frame at height step_h.
    flange = (
        cq.Workplane("XY")
        .box(reach, foot_d, wall, centered=(False, True, False))
        .translate((-mount_w / 2.0, 0, step_h - wall))
    )
    # A downstop lip at the flange tip presses the frame edge.
    lip = (
        cq.Workplane("XY")
        .box(wall, foot_d, min(wall + 2.0, step_h * 0.5), centered=(False, True, False))
        .translate((-mount_w / 2.0 + reach - wall, 0, step_h - wall - min(wall + 2.0, step_h * 0.5)))
    )
    body = foot.union(web).union(flange).union(lip)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tilt_leg":
    result = build_tilt_leg()
elif target_part == "z_bracket":
    result = build_z_bracket()
else:
    result = build_corner_bracket()
