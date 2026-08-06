"""
Sewing Machine Foot / Guide — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Seam guides and simple presser-foot aids. The functional interface is the
machine SHANK (the bar the presser foot mounts to) — low-shank machines sit
3/4 in (19 mm) from bar to needle plate, high-shank 1-1/4 in (32 mm). The guide
either snaps onto the shank via a screw-clamp, or bolts to the needle plate as a
seam fence.

Modes:
  - shank_guide  : a screw-clamp collar that grips the presser-bar shank and
    carries an adjustable seam finger beside the needle (the snap interface).
  - seam_gauge   : a bed plate that screws to the needle plate with an obround
    slot, giving an adjustable straight seam fence at a set distance.
  - edge_guide   : a right-angle edge fence with a thumbscrew slot, to run fabric
    along a fixed edge for quilting/topstitching.

Watertight strategy:
  The shank clamp is a split collar: a solid block with a through-bore (the shank
  passes through, open both ends → vented) and a saw slit to a set-screw hole —
  no trapped cavity. Seam fences are extruded plates with obround adjustment
  slots (open through the plate). Screw holes are through-holes. Blanks are
  fillet-cleaned BEFORE feature cuts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Shank standards (nominal geometry, mm) ───────────────────────────────────
SHANK_STD = {
    # bar_to_plate = distance from bar bottom to needle plate (defines mount
    # height); bar_d = presser-bar shank diameter the collar grips.
    "low":  {"bar_to_plate": 19.0, "bar_d": 5.0},
    "high": {"bar_to_plate": 32.0, "bar_d": 5.0},
}


def shank_geo(name):
    return SHANK_STD.get(name, SHANK_STD["low"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "shank_guide"))
# "shank_guide" | "seam_gauge" | "edge_guide"

shank_type = str(PARAM(lambda: shank_type, "low"))     # low | high shank
bar_clear  = float(PARAM(lambda: bar_clear, 0.3))      # shank bore fit slop (per side)
seam_dist  = float(PARAM(lambda: seam_dist, 12.0))     # seam allowance distance (mm)
screw_d    = float(PARAM(lambda: screw_d, 4.2))        # mount / set screw hole (mm)
wall       = float(PARAM(lambda: wall, 4.0))           # body wall thickness (mm)
fence_h    = float(PARAM(lambda: fence_h, 16.0))       # edge-guide fence height (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
shank_type = shank_type if shank_type in SHANK_STD else "low"
bar_clear  = max(0.0, min(bar_clear, 1.0))
seam_dist  = max(3.0, min(seam_dist, 40.0))
screw_d    = max(2.5, min(screw_d, 6.0))
wall       = max(3.0, min(wall, 8.0))
fence_h    = max(8.0, min(fence_h, 30.0))

_g = shank_geo(shank_type)
_bar_r = _g["bar_d"] / 2.0 + bar_clear


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _rounded_block(length, width, height, fillet_r, centered_z=False):
    """A rounded-rectangle block, fillet-cleaned BEFORE feature cuts."""
    blk = cq.Workplane("XY").box(length, width, height, centered=(True, True, centered_z))
    try:
        blk = blk.edges("|Z").fillet(min(fillet_r, min(length, width) / 2.0 - 0.5))
    except Exception:
        pass
    return blk


def _obround_slot_z(length, width, depth, x, y, z0):
    """A vertical obround (stadium) through-slot cutter, centred at (x,y), from
    z0 up by depth. Obround (slot2D) is far more mesh-robust than a slot made of
    a fan of arcs."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z0))
        .slot2D(length, width, angle=0)
        .extrude(depth)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_shank_guide():
    """A split screw-clamp collar that grips the presser-bar shank and carries an
    adjustable seam finger beside the needle. The collar bore is a through-hole
    (vented); a saw slit + set-screw pinch it onto the bar (no trapped void)."""
    coll_r = _bar_r + wall
    coll_h = max(14.0, _g["bar_to_plate"] * 0.6)

    # Collar body (a rounded block so a set-screw boss can sit on one face).
    body = _rounded_block(coll_r * 2.0 + 2.0, coll_r * 2.0, coll_h, 3.0)

    # Vertical through-bore for the presser-bar shank (open top and bottom).
    bore = cq.Workplane("XY").circle(_bar_r).extrude(coll_h + 2.0).translate((0, 0, -1.0))
    body = body.cut(bore)

    # Saw slit from the +X face into the bore so the collar can pinch closed.
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(coll_r, 0, -1.0))
        .rect(coll_r * 2.0, 1.4)
        .extrude(coll_h + 2.0)
    )
    body = body.cut(slit)

    # Cross set-screw hole across the slit (through the +X boss into the bore
    # region), so tightening it clamps the collar on the bar.
    setscrew = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, coll_h / 2.0, coll_r))
        .circle(screw_d / 2.0)
        .extrude(-coll_r * 2.5)
    )
    body = body.cut(setscrew)

    # Seam finger: a solid arm reaching out to +Y and down to the plate level,
    # ending in a short vertical fence the fabric edge rides against.
    arm_len = seam_dist + coll_r + 2.0
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, coll_r * 0.5, 0))
        .box(wall, arm_len, wall, centered=(True, False, False))
    )
    # Drop a short fence at the far end of the arm.
    fence = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, coll_r * 0.5 + arm_len - wall, 0))
        .box(wall + 4.0, wall, coll_h * 0.7, centered=(True, False, False))
    )
    body = body.union(arm).union(fence)
    return body


def build_seam_gauge():
    """A bed plate that bolts to the needle plate through an obround slot, giving
    an adjustable straight seam fence at a set distance from the needle line."""
    plate_l = seam_dist + 30.0
    plate_w = 26.0
    base_th = wall
    body = _rounded_block(plate_l, plate_w, base_th, 3.0)

    # Obround adjustment slot along X (bolt to the needle plate, slide to set the
    # distance). Through the plate → vented.
    slot = _obround_slot_z(plate_l * 0.5, screw_d + 0.6, base_th + 2.0, 0.0, 0.0, -1.0)
    body = body.cut(slot)

    # A straight fence wall along one long edge at seam_dist from the far edge.
    fence_wall_h = 10.0
    fence = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_w / 2.0 - wall / 2.0, base_th))
        .box(plate_l, wall, fence_wall_h, centered=(True, True, False))
    )
    body = body.union(fence)
    return body


def build_edge_guide():
    """A right-angle edge fence with a thumbscrew slot; fabric runs along the
    fixed vertical edge for even topstitching / quilting margins."""
    base_l = seam_dist + 34.0
    base_w = 24.0
    base_th = wall
    body = _rounded_block(base_l, base_w, base_th, 3.0)

    # Thumbscrew obround slot along X (clamp to the bed, slide to set distance).
    slot = _obround_slot_z(base_l * 0.45, screw_d + 0.6, base_th + 2.0, -base_l * 0.15, 0.0, -1.0)
    body = body.cut(slot)

    # Tall vertical fence along one long edge — the fabric edge rides this.
    fence = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, base_w / 2.0 - wall / 2.0, base_th))
        .box(base_l, wall, fence_h, centered=(True, True, False))
    )
    try:
        fence = fence.edges("|X and >Z").fillet(min(wall * 0.4, 1.5))
    except Exception:
        pass
    body = body.union(fence)

    # A short lead-in ramp at one end of the fence so fabric feeds in smoothly.
    ramp = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(base_l / 2.0 - 6.0, base_w / 2.0 - wall / 2.0, base_th))
        .box(12.0, wall, fence_h)
    )
    try:
        ramp = ramp.faces(">X").edges(">Z").chamfer(min(fence_h * 0.6, 8.0))
    except Exception:
        pass
    body = body.union(ramp)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "seam_gauge":
    result = build_seam_gauge()
elif target_part == "edge_guide":
    result = build_edge_guide()
else:
    result = build_shank_guide()
