"""
DIN Module Carrier — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Snaps a bare PCB or electronics module onto standard top-hat DIN rail (TS35,
DIN EN 60715) — the backbone of control panels, consumer units and enclosures.
The carrier presents a bay that holds the PCB and grabs the two rolled rail lips
from behind: one hook is a rigid reference face, the opposite hook is carried on
a cantilever SPRING BEAM (a compliant mechanism) so a printed clip grips through
geometry, not permanently strained plastic — avoiding the creep and fatigue that
kill rigid printed snaps.

Modes are dispatched via `target_part`:
  * "module_carrier" — DIN clip back + a walled PCB bay with corner posts.
  * "terminal_block" — a narrow DIN foot carrying a screw-terminal-style block.
  * "wide_carrier"   — a double-width bay for a larger module.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bay_w`).
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


# ── DIN TS35 rail (DIN EN 60715) ─────────────────────────────────────────────
RAIL_SPAN = 35.0     # width across the two lips (catch-to-catch)
RAIL_DEPTH = 7.5     # how far the top-hat stands off the panel
LIP_GRIP = 5.0       # rolled-lip turn-back (the hook grip depth)


# ── Parameters ───────────────────────────────────────────────────────────────
bay_w        = float(PARAM(lambda: bay_w,      45.0))    # PCB bay width  (X, along rail-normal)
bay_h        = float(PARAM(lambda: bay_h,      30.0))    # PCB bay height (Z, above the plate)
pcb_w        = float(PARAM(lambda: pcb_w,      40.0))    # PCB width held in the bay
pcb_th       = float(PARAM(lambda: pcb_th,      1.6))    # PCB thickness (slot width)
wall         = float(PARAM(lambda: wall,        2.4))    # bay wall thickness
plate_th     = float(PARAM(lambda: plate_th,    4.0))    # mount-plate thickness (Z base)
spring_thick = float(PARAM(lambda: spring_thick, 2.0))   # compliant beam thickness (stiffness)

target_part  = str(PARAM(lambda: target_part, "module_carrier"))

# ── Clamp ranges so extreme UI values still build watertight ─────────────────
bay_w = max(RAIL_SPAN - 5.0, min(bay_w, 120.0))
bay_h = max(8.0, min(bay_h, 80.0))
pcb_w = max(8.0, min(pcb_w, bay_w - 4.0))
pcb_th = max(0.8, min(pcb_th, 4.0))
wall = max(1.6, min(wall, 6.0))
plate_th = max(2.5, min(plate_th, 10.0))
spring_thick = max(1.0, min(spring_thick, 6.0))

# ── Fixed geometry of the clip back ──────────────────────────────────────────
RAIL_AXIS = 24.0                  # length along the rail (Y)
HOOK_LEN = RAIL_AXIS
JAW_H = RAIL_DEPTH + 2.5
HOOK_WALL = 2.6
CATCH = max(1.5, min(LIP_GRIP - 1.0, 3.0))
CLEAR = 0.35


# ── Helpers ──────────────────────────────────────────────────────────────────
def _extrude_profile_xz(pts, length):
    """Close (x, z) points on XZ and extrude symmetrically about Y=0."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)


def _mount_plate(width):
    plate = cq.Workplane("XY").box(width, RAIL_AXIS, plate_th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(3.0, width / 6.0))
    except Exception:
        pass
    return plate


def _fixed_hook():
    """Rigid hook on the +X side (fixed reference jaw)."""
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
    """COMPLIANT sprung hook on the -X side: a slender folded cantilever that
    flexes outward over the lip and springs back to grip. Bend energy lives in
    the beam geometry, so the wall is never held in permanent strain (no creep).
    `spring_thick` sets the stiffness."""
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
        (x_out + t, plate_th - t - 3.0), (x_root_in, plate_th - t - 3.0),
    ]
    beam = _extrude_profile_xz(outer + inner, HOOK_LEN)
    relief = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_root_in, 0.0, plate_th - 1.0))
        .box(2.0, RAIL_AXIS + 2.0, 2.2, centered=(True, True, True))
    )
    try:
        beam = beam.cut(relief)
    except Exception:
        pass
    return beam


def _pcb_bay(width):
    """A walled bay on top of the plate with two vertical PCB slots (front & back
    walls slotted) so a board slides in edge-on. Built above the plate top."""
    z0 = plate_th
    outer = (
        cq.Workplane("XY").workplane(offset=z0)
        .box(width, RAIL_AXIS, bay_h, centered=(True, True, False))
    )
    # Hollow the interior, leaving four walls.
    inner = (
        cq.Workplane("XY").workplane(offset=z0 - 0.5)
        .box(width - 2.0 * wall, RAIL_AXIS - 2.0 * wall, bay_h + 1.0,
             centered=(True, True, False))
    )
    bay = outer.cut(inner)

    # A pair of PCB retention slots on the inner faces of the +/-Y walls: a thin
    # groove the board edge sits in. Represented as thin gaps left in a pair of
    # ribs so the board is captured. Add two ribs with a slot between them.
    rib_z = z0 + 2.0
    for sy in (-1.0, 1.0):
        yface = sy * (RAIL_AXIS / 2.0 - wall)
        rib = (
            cq.Workplane("XY").workplane(offset=rib_z)
            .transformed(offset=cq.Vector(0, yface - sy * (pcb_th + 1.5), 0))
            .box(pcb_w + 2.0, 1.4, bay_h - 3.0, centered=(True, True, False))
        )
        bay = bay.union(rib)
    return bay


# ── Builders ─────────────────────────────────────────────────────────────────
def build_module_carrier():
    body = _mount_plate(max(bay_w, RAIL_SPAN + 8.0))
    body = body.union(_fixed_hook())
    body = body.union(_spring_hook())
    body = body.union(_pcb_bay(bay_w))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_terminal_block():
    """A narrow DIN foot carrying a solid block drilled with a row of wire bores
    and screw pilot holes — a printed terminal-block body / marker carrier."""
    width = RAIL_SPAN + 8.0
    body = _mount_plate(width)
    body = body.union(_fixed_hook())
    body = body.union(_spring_hook())

    block_h = max(12.0, bay_h * 0.6)
    block = (
        cq.Workplane("XY").workplane(offset=plate_th)
        .box(width - 6.0, RAIL_AXIS - 2.0, block_h, centered=(True, True, False))
    )
    body = body.union(block)

    # A row of horizontal wire bores through the block along Y, plus vertical
    # screw pilots from the top — grouped cuts for speed / watertightness.
    n = max(2, int((width - 12.0) // 6.0))
    xs = [-(width - 12.0) / 2.0 + i * ((width - 12.0) / (n - 1)) for i in range(n)]
    wire = (
        cq.Workplane("XZ").workplane(offset=RAIL_AXIS / 2.0 + 1.0)
        .pushPoints([(x, plate_th + block_h * 0.4) for x in xs])
        .circle(1.6).extrude(RAIL_AXIS + 2.0)
    )
    body = body.cut(wire)
    pilots = (
        cq.Workplane("XY").workplane(offset=plate_th + block_h + 0.5)
        .pushPoints([(x, 0.0) for x in xs]).circle(1.3).extrude(-block_h * 0.7)
    )
    body = body.cut(pilots)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wide_carrier():
    """Double-width bay for a larger module; hooks stay on the 35 mm rail span,
    centred, while the plate and bay run wide."""
    width = max(bay_w, RAIL_SPAN + 40.0)
    body = _mount_plate(width)
    body = body.union(_fixed_hook())
    body = body.union(_spring_hook())
    body = body.union(_pcb_bay(width))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "module_carrier": build_module_carrier,
    "terminal_block": build_terminal_block,
    "wide_carrier": build_wide_carrier,
}

result = _dispatch.get(target_part, build_module_carrier)()
