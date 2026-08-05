"""
Car Vent / Dash Phone Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A phone/accessory mount that clips onto a car A/C vent blade (fin). The clip is a
J-hook that hangs over the horizontal blade of thickness `blade_t`, with a sprung
back leg that presses against the blade for a friction hold.

Three parts (dispatched via `target_part`):
  * "cradle_mount"   — vent clip + an adjustable phone cradle (a floor lip + two
                       side arms sized to `phone_w`).
  * "magnetic_mount" — vent clip + a disc carrying magnet pockets (for a magnetic
                       phone plate).
  * "clip_only"      — just the vent-blade clip (a spare / a base to build on).

The clip geometry is the shared CDG interface: a hook whose throat opening equals
`blade_t` + clearance so it grips real vent fins.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `blade_t`).
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
target_part = str(PARAM(lambda: target_part, "cradle_mount"))  # cradle_mount|magnetic_mount|clip_only
grip        = str(PARAM(lambda: grip,         "cradle"))        # cradle | magnetic | clip

blade_t     = float(PARAM(lambda: blade_t,     2.0))   # vent-blade (fin) thickness the clip grips
clip_w      = float(PARAM(lambda: clip_w,     22.0))   # clip width across the blade
clip_drop   = float(PARAM(lambda: clip_drop,  18.0))   # how far the hook hangs down the front of the blade
clip_clear  = float(PARAM(lambda: clip_clear,  0.3))   # throat clearance so it slides onto the blade
wall        = float(PARAM(lambda: wall,        3.0))   # clip / body wall thickness
phone_w     = float(PARAM(lambda: phone_w,    72.0))   # phone width for the cradle arms
magnet_d    = float(PARAM(lambda: magnet_d,    8.1))   # magnet pocket diameter (8 mm magnet + slop)
magnet_h    = float(PARAM(lambda: magnet_h,    2.1))   # magnet pocket depth (2 mm magnet + slop)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
blade_t    = max(0.8, min(blade_t, 8.0))
clip_w     = max(10.0, min(clip_w, 45.0))
clip_drop  = max(8.0, min(clip_drop, 40.0))
clip_clear = max(0.0, min(clip_clear, 1.0))
wall       = max(2.0, min(wall, 6.0))
phone_w    = max(50.0, min(phone_w, 95.0))
magnet_d   = max(4.0, min(magnet_d, 20.0))
magnet_h   = max(1.0, min(magnet_h, 6.0))

THROAT = blade_t + clip_clear          # hook opening
BACK_DROP = clip_drop * 0.7            # sprung back leg is a bit shorter than the front


# ── Vent-blade clip (shared CDG interface) ───────────────────────────────────
def build_clip():
    """A J-hook clip hanging over a horizontal vent blade.

    Built as a swept-ish channel profile in the XZ plane (X = depth toward the car
    interior, Z = up), extruded along Y for `clip_w`. The blade lies in the throat.
    Returns (solid, front_face_x, front_face_z_center) so a body can attach to the
    front (the face pointing at the phone/user)."""
    # The top of the blade sits at z=0 (the hook wraps over it from above).
    # Profile points (XZ), going around the J. The blade occupies the throat between
    # z=0 (top leg underside) and z=-THROAT (back leg / underside). Front is +X.
    x_back = 0.0                             # back plane (against the vent, +X toward user)
    x_front = wall                           # front wall thickness of the vertical spine
    # Vertical spine goes from the top leg down `clip_drop` on the FRONT of the blade.
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (x_back, THROAT),                       # top of the top leg (back edge)
            (x_front + THROAT + wall, THROAT),      # top leg reaches over the blade to the front
            (x_front + THROAT + wall, -clip_drop),  # down the front spine
            (x_front + THROAT, -clip_drop),         # inner front spine
            (x_front + THROAT, 0.0),                 # inner: throat top (blade rests here)
            (x_front, 0.0),                          # ... but we want the throat clear:
            (x_front, -BACK_DROP),                   # sprung back leg goes down behind the blade
            (x_back, -BACK_DROP),
        ])
        .close()
    )
    clip = prof.extrude(clip_w / 2.0, both=True)
    front_x = x_front + THROAT + wall
    return clip, front_x, (THROAT - clip_drop) / 2.0


# ── Accessory bodies (attach to the clip front) ──────────────────────────────
def _cradle(front_x, z_mid):
    """A phone cradle: a bottom lip and two side arms sized to `phone_w`. Rises from
    a back plate bonded to the clip front."""
    plate_h = 40.0
    plate_w = min(phone_w + 2.0 * wall + 6.0, 110.0)
    plate_t = wall
    back = (
        cq.Workplane("XY")
        .box(plate_w, plate_t, plate_h, centered=(True, True, True))
        .translate((0, front_x + plate_t / 2.0, z_mid - 6.0))
    )
    body = back
    # Bottom lip: an L catching the phone's lower edge.
    lip = (
        cq.Workplane("XY")
        .box(plate_w, 16.0, wall, centered=(True, True, True))
        .translate((0, front_x + 8.0, z_mid - 6.0 - plate_h / 2.0 + wall / 2.0))
    )
    lip_wall = (
        cq.Workplane("XY")
        .box(plate_w, wall, 10.0, centered=(True, True, True))
        .translate((0, front_x + 16.0 - wall / 2.0, z_mid - 6.0 - plate_h / 2.0 + 5.0))
    )
    body = body.union(lip).union(lip_wall)
    # Two side arms hugging the phone width.
    for sx in (-1.0, 1.0):
        arm = (
            cq.Workplane("XY")
            .box(wall, 14.0, plate_h * 0.7, centered=(True, True, True))
            .translate((sx * (phone_w / 2.0), front_x + 7.0, z_mid - 6.0))
        )
        cap = (
            cq.Workplane("XY")
            .box(6.0, wall, plate_h * 0.7, centered=(True, True, True))
            .translate((sx * (phone_w / 2.0 - 3.0 + wall / 2.0), front_x + 14.0 - wall / 2.0, z_mid - 6.0))
        )
        body = body.union(arm).union(cap)
    return body


def _magnetic(front_x, z_mid):
    """A disc bonded to the clip front, carrying magnet pockets on its FRONT face for
    a magnetic phone plate."""
    disc_r = 18.0
    disc_t = wall + magnet_h + 0.8
    disc = (
        cq.Workplane("XZ")
        .circle(disc_r)
        .extrude(disc_t)
        .translate((0, front_x, z_mid - 6.0))
    )
    # Magnet pockets: a ring of pockets opening on the front face (max Y).
    pocket_ring_r = disc_r * 0.55
    n = 4
    pts = []
    for i in range(n):
        ang = (2.0 * math.pi * i) / n
        px = pocket_ring_r * math.cos(ang)
        pz = pocket_ring_r * math.sin(ang)
        pts.append((px, pz))
    for (px, pz) in pts:
        pocket = (
            cq.Workplane("XZ")
            .circle(magnet_d / 2.0)
            .extrude(-(magnet_h + 0.2))
            .translate((px, front_x + disc_t, (z_mid - 6.0) + pz))
        )
        disc = disc.cut(pocket)
    # A centre pocket too.
    center = (
        cq.Workplane("XZ")
        .circle(magnet_d / 2.0)
        .extrude(-(magnet_h + 0.2))
        .translate((0, front_x + disc_t, z_mid - 6.0))
    )
    disc = disc.cut(center)
    return disc


# ── Part builders ────────────────────────────────────────────────────────────
def build_cradle_mount():
    clip, front_x, z_mid = build_clip()
    body = clip.union(_cradle(front_x, z_mid))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_magnetic_mount():
    clip, front_x, z_mid = build_clip()
    body = clip.union(_magnetic(front_x, z_mid))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_clip_only():
    clip, _front_x, _z_mid = build_clip()
    return clip


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "magnetic_mount":
    result = build_magnetic_mount()
elif target_part == "clip_only":
    result = build_clip_only()
else:
    result = build_cradle_mount()
