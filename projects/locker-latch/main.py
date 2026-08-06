"""
Locker Latch — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Positive latches for RV and boat cabinet doors that stay shut under motion (a sprung
or cammed catch, not a friction magnet). The latch body screws to the frame; a strike
or the door edge engages a hooked catch so vibration and heel can't pop the door.

Three parts (dispatched via `target_part`):
  * "cam_latch"    — a quarter-turn cam latch: a base with a bored hub and a cam finger
                     that rotates behind a strike lip (turn to lock).
  * "spring_latch" — a body with a hooked catch on a printed-in cantilever spring beam
                     that snaps over the door edge and is released by pressing the tail.
  * "push_latch"   — a low-profile push-to-open bumper catch: a ramped nib on a short
                     flexure that the door edge deflects and drops behind.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `door_gap`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

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
target_part = str(PARAM(lambda: target_part, "cam_latch"))  # cam_latch|spring_latch|push_latch

door_gap   = float(PARAM(lambda: door_gap,   4.0))   # gap between door edge and frame (mm)
body_w     = float(PARAM(lambda: body_w,     36.0))  # latch body width (mm)
body_h     = float(PARAM(lambda: body_h,     22.0))  # latch body height (mm)
base_t     = float(PARAM(lambda: base_t,      6.0))  # base/mount thickness (mm)
screw_dia  = float(PARAM(lambda: screw_dia,   4.0))  # mounting screw clearance dia (mm)
hub_dia    = float(PARAM(lambda: hub_dia,     8.0))  # cam-latch spindle hub bore (mm)
cam_reach  = float(PARAM(lambda: cam_reach,  16.0))  # cam finger reach past the hub (mm)
spring_t   = float(PARAM(lambda: spring_t,    2.4))  # cantilever/flexure beam thickness (mm)
catch_hook = float(PARAM(lambda: catch_hook,  3.0))  # catch hook engagement depth (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
door_gap   = max(1.0, min(door_gap, 12.0))
body_w     = max(20.0, min(body_w, 80.0))
body_h     = max(14.0, min(body_h, 50.0))
base_t     = max(3.0, min(base_t, 12.0))
screw_dia  = max(2.5, min(screw_dia, 8.0))
hub_dia    = max(4.0, min(hub_dia, 16.0))
cam_reach  = max(8.0, min(cam_reach, 40.0))
spring_t   = max(1.6, min(spring_t, 5.0))
catch_hook = max(1.5, min(catch_hook, 8.0))


# ── Shared base ───────────────────────────────────────────────────────────────
def _mount_base(w, d):
    """A mounting base on XY (base at z=0, centred X/Y) with two countersunk-clearance
    screw holes on the X axis."""
    base = cq.Workplane("XY").box(w, d, base_t, centered=(True, True, False))
    sx = w / 2.0 - max(screw_dia, 5.0)
    for s in (-1.0, 1.0):
        hole = (
            cq.Workplane("XY")
            .center(s * sx, 0.0)
            .circle(screw_dia / 2.0)
            .extrude(base_t + 2.0)
            .translate((0, 0, -1.0))
        )
        # Shallow countersink cup on top.
        csk = (
            cq.Workplane("XY")
            .center(s * sx, 0.0)
            .circle(screw_dia * 0.9)
            .extrude(1.4)
            .translate((0, 0, base_t - 1.4))
        )
        base = base.cut(hole).cut(csk)
    return base


# ── Cam latch ─────────────────────────────────────────────────────────────────
def build_cam_latch():
    """A quarter-turn cam latch: a mount base with a raised bored hub and a flat cam
    finger that sweeps behind a strike lip when the spindle turns."""
    base = _mount_base(body_w, body_h)
    hub_or = hub_dia / 2.0 + 3.5
    hub_top = base_t + body_h * 0.5
    hub = (
        cq.Workplane("XY")
        .circle(hub_or)
        .extrude(hub_top)
    )
    bore = (
        cq.Workplane("XY")
        .rect(hub_dia, hub_dia)  # square drive so a printed spindle can't slip
        .extrude(hub_top + 2.0)
        .translate((0, 0, -1.0))
    )
    hub = hub.cut(bore)
    # Cam finger: a flat blade projecting from the hub top, offset so its far edge
    # sweeps behind a strike as it rotates.
    cam = (
        cq.Workplane("XY")
        .workplane(offset=hub_top - spring_t)
        .center(cam_reach / 2.0, 0.0)
        .box(cam_reach, hub_or * 1.4, spring_t, centered=(True, True, False))
    )
    lip = (
        cq.Workplane("XY")
        .workplane(offset=hub_top - spring_t)
        .center(cam_reach - spring_t, 0.0)
        .box(spring_t * 1.5, hub_or * 1.4, catch_hook + spring_t, centered=(True, True, False))
    )
    body = base.union(hub).union(cam).union(lip)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Spring latch ────────────────────────────────────────────────────────────
def build_spring_latch():
    """A body with a hooked catch carried on a printed cantilever beam. The door edge
    pushes past the ramped hook (beam flexes), then the hook drops behind the door.
    Pressing the tail past the body deflects the beam to release."""
    base = _mount_base(body_w, body_h)
    wall = base_t
    # Rear anchor wall the beam grows from.
    anchor = (
        cq.Workplane("XY")
        .center(-body_w / 2.0 + wall / 2.0, 0.0)
        .box(wall, body_h, body_h, centered=(True, True, False))
        .translate((0, 0, base_t))
    )
    # Cantilever beam: thin bar spanning most of the body length at mid height.
    beam_len = body_w - wall - door_gap
    beam_z = base_t + body_h * 0.45
    beam = (
        cq.Workplane("XY")
        .center(-body_w / 2.0 + wall + beam_len / 2.0, 0.0)
        .box(beam_len, body_h * 0.6, spring_t, centered=(True, True, False))
        .translate((0, 0, beam_z))
    )
    # Hooked catch at the free end: a block with an engagement lip toward the door (+X).
    hook_x = -body_w / 2.0 + wall + beam_len
    hook = (
        cq.Workplane("XY")
        .center(hook_x, 0.0)
        .box(catch_hook + spring_t, body_h * 0.6, catch_hook + spring_t * 2.0, centered=(True, True, False))
        .translate((0, 0, beam_z))
    )
    # Ramp the leading top edge so the door slides the beam down on close.
    try:
        hook = hook.edges(">X and >Z").chamfer(min(catch_hook, spring_t * 1.4))
    except Exception:
        pass
    body = base.union(anchor).union(beam).union(hook)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Push latch ────────────────────────────────────────────────────────────────
def build_push_latch():
    """A low-profile push-to-close bumper catch: a ramped nib on a short flexure that
    the door edge deflects and drops behind. Lower and wider than the spring latch."""
    w = body_w
    h = max(10.0, body_h * 0.55)
    base = _mount_base(w, h)
    # A shallow ramp block rising toward the door; a slot behind it forms the flexure.
    ramp = (
        cq.Workplane("XZ")
        .polyline([
            (0.0, 0.0),
            (w * 0.5, 0.0),
            (w * 0.5, catch_hook + spring_t),
            (0.0, catch_hook + spring_t + door_gap * 0.6),
        ])
        .close()
        .extrude(h)
        .translate((0, h / 2.0, base_t))
    )
    # Relief slot behind the ramp to let it flex (does not sever the base).
    slot = (
        cq.Workplane("XY")
        .center(w * 0.5 - spring_t * 1.5, 0.0)
        .box(spring_t, h * 0.7, catch_hook, centered=(True, True, False))
        .translate((0, 0, base_t + catch_hook))
    )
    body = base.union(ramp).cut(slot)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "spring_latch":
    result = build_spring_latch()
elif target_part == "push_latch":
    result = build_push_latch()
else:
    result = build_cam_latch()
