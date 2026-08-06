"""
Universal Device Wall Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A fit-anything wall cradle for a rectangular device — a remote, router, network
switch, hub, or handset. The device envelope (W × D × H) drives a printable
pocket with a printer-clearance gap; a backplate screws (or sticks) to the wall.
Three `style` families, each its own studio mode:

  * "cradle_mount" — an open shelf: a floor + a low front lip that the device
                     drops into, back open to the wall. Easiest access.
  * "pocket_mount" — a deeper four-wall wrap around the device body, holding it
                     more securely with a front access scallop.
  * "strap_mount"  — a slim backplate with a raised band (bridge) that the device
                     tucks behind — the minimal-material option.

Shared across the batch: a bolt-pattern helper (`bolt_grid`) drills the two
wall-mount screw holes on the backplate the same way in every mode.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `dev_w`).
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
style       = str(PARAM(lambda: style, "cradle"))   # cradle|pocket|strap
target_part = str(PARAM(lambda: target_part, ""))   # studio dispatch (part id)

dev_w       = float(PARAM(lambda: dev_w,   60.0))    # device width  X (mm)
dev_d       = float(PARAM(lambda: dev_d,   25.0))    # device depth  Y — off the wall (mm)
dev_h       = float(PARAM(lambda: dev_h,  110.0))    # device height Z — up the wall (mm)

wall_t      = float(PARAM(lambda: wall_t,   3.0))    # cradle wall / backplate thickness (mm)
margin      = float(PARAM(lambda: margin,   4.0))    # side margin beyond the device (mm)
clearance   = float(PARAM(lambda: clearance, 0.6))   # per-side printer fit gap (mm)

lip_h       = float(PARAM(lambda: lip_h,   14.0))    # front lip / band height (mm)
screw_dia   = float(PARAM(lambda: screw_dia, 4.2))   # wall screw clearance dia (mm)
adhesive    = bool(PARAM(lambda: adhesive, False))   # skip screw holes (use adhesive pad)


# ── Style → studio part id ───────────────────────────────────────────────────
PART_FOR_STYLE = {
    "cradle": "cradle_mount",
    "pocket": "pocket_mount",
    "strap":  "strap_mount",
}
_part_ids = ("cradle_mount", "pocket_mount", "strap_mount")
if target_part in _part_ids:
    active_part = target_part
else:
    active_part = PART_FOR_STYLE.get(style, "cradle_mount")


# ── Safe clamps ──────────────────────────────────────────────────────────────
dev_w = max(15.0, dev_w)
dev_d = max(6.0, dev_d)
dev_h = max(15.0, dev_h)
wall_t = max(1.6, wall_t)
margin = max(2.0, margin)
clearance = max(0.0, min(clearance, 1.5))
screw_dia = max(2.0, min(screw_dia, 8.0))

# Interior pocket footprint (device + clearance on each side).
cav_w = dev_w + 2.0 * clearance          # X
cav_d = dev_d + 2.0 * clearance          # Y (off wall)
# Outer footprint on the wall face.
out_w = cav_w + 2.0 * wall_t + 2.0 * margin
# Backplate reaches the full device height plus a screw margin top & bottom.
plate_h = dev_h + 2.0 * (screw_dia + 3.0)
lip_h = max(4.0, min(lip_h, dev_h * 0.9))


# ── Shared plate + bolt-pattern helper (reused across the batch) ──────────────
def bolt_grid_y(solid, points, front_y, thru):
    """Cut screw holes running along +Y (through the backplate thickness) at each
    (x, z). The backplate's wall-facing surface is at y=0 and its front face at
    y=front_y; the bore starts behind the wall face and passes fully through."""
    if adhesive:
        return solid
    for (x, z) in points:
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, z, -1.0))
            .cylinder(thru + 2.0, screw_dia / 2.0)
        )
        solid = solid.cut(hole)
    return solid


def wall_screw_points():
    """Two screw holes on the vertical centreline, near the top and bottom of the
    backplate (spread wide for a stable two-point wall fix)."""
    z0 = screw_dia + 3.0
    z1 = plate_h - (screw_dia + 3.0)
    return [(0.0, z0), (0.0, z1)]


def backplate(thick_y):
    """The flat plate held against the wall: footprint out_w × plate_h, occupying
    Y:[0, thick_y] (y=0 is the wall face), centered in X, base at z=0."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, thick_y / 2.0, plate_h / 2.0))
        .box(out_w, thick_y, plate_h)
    )


# ── Builders ─────────────────────────────────────────────────────────────────
def build_cradle():
    """Open shelf: a backplate against the wall, a floor slab projecting out, and
    a low front lip. The device drops in from the top; the back stays open."""
    body = backplate(wall_t)
    body = bolt_grid_y(body, wall_screw_points(), wall_t, wall_t)

    floor_depth = cav_d + wall_t          # from wall face out to the front lip
    floor = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, floor_depth / 2.0, wall_t / 2.0))
        .box(out_w, floor_depth, wall_t)
    )
    body = body.union(floor)

    # Front lip: a low wall at the front edge of the floor, holding the device in.
    lip_y = wall_t + cav_d
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, lip_y + wall_t / 2.0, lip_h / 2.0))
        .box(out_w, wall_t, lip_h)
    )
    # Short side ribs tie the lip to the backplate for rigidity.
    rib_w = wall_t
    rib_x = out_w / 2.0 - rib_w / 2.0
    ribs = None
    for sx in (-rib_x, rib_x):
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, (wall_t + lip_y) / 2.0, lip_h / 2.0))
            .box(rib_w, lip_y - wall_t + wall_t, lip_h)
        )
        ribs = rib if ribs is None else ribs.union(rib)
    body = body.union(lip)
    if ribs is not None:
        body = body.union(ribs)
    return body.clean()


def build_pocket():
    """Deeper four-wall wrap: a solid block sized to the outer footprint, hollowed
    to the device cavity from the top, with a front access scallop cut so the
    device can be pushed out with a thumb."""
    depth = cav_d + 2.0 * wall_t          # total Y depth of the wrap
    block = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, depth / 2.0, plate_h / 2.0))
        .box(out_w, depth, plate_h)
    )
    # Hollow the device cavity: open at the top, floor of thickness wall_t.
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, wall_t + cav_d / 2.0, wall_t + (plate_h) / 2.0))
        .box(cav_w, cav_d, plate_h + 2.0)
    )
    body = block.cut(cavity)
    body = bolt_grid_y(body, wall_screw_points(), depth, depth)

    # Front access scallop: a cylinder cut through the front wall at mid height.
    scallop_r = min(cav_w * 0.35, dev_h * 0.28)
    scallop = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, wall_t + dev_h * 0.55, depth))
        .cylinder(4.0 * wall_t, scallop_r)
    )
    body = body.cut(scallop)
    return body.clean()


def build_strap():
    """Minimal: a slim backplate with a single raised band (a bridge standing off
    the plate) that the device tucks behind. The band spans the device width and
    stands proud by the device depth + clearance."""
    body = backplate(wall_t)
    body = bolt_grid_y(body, wall_screw_points(), wall_t, wall_t)

    band_z = dev_h * 0.5                   # band centred at mid device height
    stand = cav_d + wall_t                 # how far the band sits off the wall
    band_w = cav_w + 2.0 * wall_t
    # Vertical uprights on each side, then a horizontal band bridging them.
    up_x = band_w / 2.0 - wall_t / 2.0
    uprights = None
    for sx in (-up_x, up_x):
        up = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, stand / 2.0, band_z))
            .box(wall_t, stand, lip_h)
        )
        uprights = up if uprights is None else uprights.union(up)
    bridge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, stand - wall_t / 2.0, band_z))
        .box(band_w, wall_t, lip_h)
    )
    body = body.union(uprights).union(bridge)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active_part == "pocket_mount":
    result = build_pocket()
elif active_part == "strap_mount":
    result = build_strap()
else:
    result = build_cradle()
