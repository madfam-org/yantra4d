"""
Glasses Holders — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holders for glasses and sunglasses, all built around one temple-cradle interface
(a sprung V-notch that grips an eyewear temple arm). A visor clip for the car sun
visor, a wall hook, and a desk stand. Every part is one watertight solid built by
cutting the cradle notch and a mount feature from a body.

Modes (dispatched via `target_part`):
  * "visor_clip" — a spring clip that slides onto a car sun visor, carrying a
                   temple cradle so glasses hang from the visor.
  * "wall_hook"  — a screw-mounted wall plate with a temple cradle hook.
  * "desk_stand" — a weighted-footprint stand with an upright temple cradle so
                   glasses perch on a desk.

The `mount` select mirrors the three modes for UI discovery; `target_part` (the
per-part id the platform injects) is the authority for which part is built.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `temple_w`).
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
temple_w    = float(PARAM(lambda: temple_w,    5.0))    # temple-arm width the cradle grips (mm)
temple_t    = float(PARAM(lambda: temple_t,    4.0))    # temple-arm thickness (mm)
wall        = float(PARAM(lambda: wall,        3.0))    # wall thickness (mm)
visor_t     = float(PARAM(lambda: visor_t,    18.0))    # sun-visor thickness the clip grips (mm)
cradle_w    = float(PARAM(lambda: cradle_w,   16.0))    # cradle width along the temple (mm)
stand_h     = float(PARAM(lambda: stand_h,    70.0))    # desk-stand upright height (mm)
mount       = str(  PARAM(lambda: mount, "visor-clip"))  # visor-clip|wall|desk-stand (UI mirror)

target_part = str(  PARAM(lambda: target_part, "visor_clip"))  # visor_clip|wall_hook|desk_stand

# ── Safe clamps ──────────────────────────────────────────────────────────────
temple_w = max(2.0, min(temple_w, 12.0))
temple_t = max(2.0, min(temple_t, 10.0))
wall     = max(2.0, min(wall, 6.0))
visor_t  = max(6.0, min(visor_t, 40.0))
cradle_w = max(8.0, min(cradle_w, 40.0))
stand_h  = max(35.0, min(stand_h, 140.0))


# ── Shared temple-cradle helper ───────────────────────────────────────────────
def temple_cradle(width):
    """A sprung cradle block that grips an eyewear temple arm. A rounded block
    with a U-notch (opening up in +Z) sized to the temple cross-section plus a
    small clearance; the printed side walls flex to pinch the arm. Returns a
    cq.Workplane centred in X/Y with its base at z=0. The U opening is along Z,
    the arm lies along Y (through the block width). Shared across all mounts so
    every holder grips the same temple interface."""
    notch_w = temple_w + 0.6
    notch_d = temple_t + 0.8
    block_w = notch_w + 2.0 * wall
    block_h = notch_d + wall
    block = cq.Workplane("XY").box(block_w, width, block_h, centered=(True, True, False))
    try:
        block = block.edges("|Y").fillet(min(wall, 2.0))
    except Exception:
        pass
    # U-notch cut from the top.
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .box(notch_w, width + 2.0, notch_d + block_h, centered=(True, True, False))
    )
    try:
        notch = notch.edges("|Y").fillet(min(notch_w * 0.3, 1.2))
    except Exception:
        pass
    block = block.cut(notch)
    # Retaining lips at the notch mouth (small inward nibs that snap over the arm).
    for sx in (-1.0, 1.0):
        lip = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (notch_w / 2.0 - 0.3), 0, block_h - 0.8))
            .box(1.0, width * 0.9, 1.0, centered=(True, True, True))
        )
        block = block.union(lip)
    return block, block_w, block_h


def rounded_block(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


# ── Part builders ─────────────────────────────────────────────────────────────
def build_visor_clip():
    """A C-clip that slides onto a car sun visor, with a temple cradle on the
    front. The C is a side profile extruded across the cradle width — inherently
    watertight — and the cradle is unioned to the clip's front face."""
    gap = visor_t + 1.0
    depth = gap + 2.0 * wall
    height = 40.0
    spine = wall
    lip = wall * 1.4

    # C profile (open toward -X where the visor slides in), in XZ, extruded along Y.
    pts = [
        (0.0, 0.0),
        (depth, 0.0),
        (depth, height),
        (0.0, height),
        (0.0, height - lip),
        (depth - spine, height - lip),
        (depth - spine, lip),
        (0.0, lip),
    ]
    clip = (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .extrude(cradle_w)
        .translate((0, cradle_w / 2.0, 0))
    )
    try:
        clip = clip.edges("|Y").fillet(min(spine * 0.4, 1.0))
    except Exception:
        pass

    # Temple cradle on the +X (front) face, near mid height.
    cradle, cw, ch = temple_cradle(cradle_w)
    # cradle base at z=0 opening up; rotate so it hangs off the front face opening
    # downward (arm horizontal). Place it protruding in +X.
    cradle = cradle.rotate((0, 0, 0), (0, 1, 0), 180)   # opening now faces -Z
    cradle = cradle.translate((depth + ch / 2.0, 0, height * 0.5))
    # Small boss to bridge cradle to clip.
    boss = rounded_block(wall * 2.0 + 2.0, cradle_w * 0.8, ch, 1.0)
    boss = boss.rotate((0, 0, 0), (0, 1, 0), -90)
    boss = boss.translate((depth, 0, height * 0.5))
    body = clip.union(boss).union(cradle)
    return body


def build_wall_hook():
    """A wall plate with two screw holes and a temple cradle standing off the
    front, so glasses hang on a wall."""
    plate_w = cradle_w + 2.0 * wall + 6.0
    plate_h = 46.0
    plate = (
        cq.Workplane("XY")
        .box(wall, plate_w, plate_h, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|X").fillet(min(wall, 2.0))
    except Exception:
        pass
    # Two screw holes through the plate (X direction).
    for sz in (-1.0, 1.0):
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, plate_h * 0.5 + sz * plate_h * 0.32, 0))
            .cylinder(wall + 4.0, 2.2)
        )
        # countersink cone on the front.
        plate = plate.cut(hole)

    # Temple cradle protruding from the front (+X) at mid height, opening down.
    cradle, cw, ch = temple_cradle(cradle_w)
    cradle = cradle.rotate((0, 0, 0), (0, 1, 0), 180)
    cradle = cradle.translate((wall + ch / 2.0 + 4.0, 0, plate_h * 0.5))
    # Arm to hold the cradle out from the wall.
    arm = rounded_block(ch + 4.0, cradle_w * 0.7, ch, 1.5)
    arm = arm.rotate((0, 0, 0), (0, 1, 0), -90)
    arm = arm.translate((wall, 0, plate_h * 0.5))
    body = plate.union(arm).union(cradle)
    return body


def build_desk_stand():
    """A desk stand: a wide flat foot with an upright post carrying a temple
    cradle at the top, so glasses perch upright on a desk. One watertight solid."""
    foot_w = 46.0
    foot_d = 60.0
    foot_h = wall * 2.5
    foot = rounded_block(foot_w, foot_d, foot_h, min(foot_w * 0.15, 6.0))

    # Upright post rising from the back of the foot.
    post_t = max(wall * 2.0, 6.0)
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -foot_d / 2.0 + post_t, foot_h))
        .box(cradle_w + 2.0 * wall, post_t, stand_h, centered=(True, True, False))
    )
    try:
        post = post.edges("|Z").fillet(min(post_t * 0.4, 2.0))
    except Exception:
        pass
    body = foot.union(post)

    # Temple cradle at the top of the post, opening up so glasses rest in it.
    cradle, cw, ch = temple_cradle(cradle_w)
    cradle = cradle.translate((0, -foot_d / 2.0 + post_t, foot_h + stand_h))
    body = body.union(cradle)

    # Lightening window in the post.
    win = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -foot_d / 2.0 + post_t, foot_h + stand_h * 0.5))
        .box(cradle_w * 0.5, post_t + 2.0, stand_h * 0.4, centered=(True, True, True))
    )
    body = body.cut(win)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_part = target_part
if _part == "visor_clip" and mount in ("wall", "desk-stand"):
    # Honor the mount select when target_part is left at the default.
    _part = "wall_hook" if mount == "wall" else "desk_stand"

if _part == "wall_hook":
    result = build_wall_hook()
elif _part == "desk_stand":
    result = build_desk_stand()
else:
    result = build_visor_clip()
