"""
Label / Tape Dispenser — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A tape / label-roll dispenser parametric on the roll's CORE inner diameter. The
roll slips over a printed spindle (a solid post sized to the core minus a slip
clearance — the "socket" is the spindle's outer surface). Three distinct forms
dispatched by `target_part`:

  * "roll_holder"   — a weighted base with two upright side walls carrying a
                      horizontal spindle between them; the roll spins freely on
                      the spindle. A simple free-spin holder.
  * "desk_dispenser"— the same base + spindle plus a forward tear ramp with a
                      saw-tooth cutting edge, so tape pulls forward and tears
                      cleanly across the teeth (a desktop tape dispenser).
  * "wall_spindle"  — a wall bracket: a flat screw plate with a single
                      cantilevered spindle the roll slides onto from the open
                      end (a wall-mounted paper/tape roll arm).

Reference dimensions (why the defaults are what they are):
  - A standard desktop / office tape roll has a 1 inch = 25.4 mm core.
  - Big packing-tape and some label rolls use a 3 inch = 76.2 mm core.
  `core_dia` defaults to 25.4 mm; the spindle is `core_dia - clearance`.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `core_dia`).
  - Read them via PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
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
core_dia   = float(PARAM(lambda: core_dia,   25.4))   # tape roll CORE inner Ø (mm) — 1in=25.4, 3in=76.2
roll_w     = float(PARAM(lambda: roll_w,     25.0))   # roll width along the spindle (mm)
roll_od    = float(PARAM(lambda: roll_od,    75.0))   # roll outer Ø (sets base/upright height, mm)
clearance  = float(PARAM(lambda: clearance,   0.8))   # spindle slip clearance under the core (mm)
wall       = float(PARAM(lambda: wall,        4.0))   # base / upright / plate thickness (mm)
base_len   = float(PARAM(lambda: base_len,   90.0))   # base length front-to-back (mm)
blade_ramp = float(PARAM(lambda: blade_ramp, 30.0))   # tear-ramp length (desk_dispenser, mm)
teeth      = int(  PARAM(lambda: teeth,        9))    # saw-tooth count on the tear edge (desk_dispenser)
screw_dia  = float(PARAM(lambda: screw_dia,   4.5))   # wall screw clearance Ø (wall_spindle, mm)

target_part = str(PARAM(lambda: target_part, "roll_holder"))  # roll_holder | desk_dispenser | wall_spindle

# ── Clamps / derived values ──────────────────────────────────────────────────
core_dia   = max(10.0, min(core_dia, 120.0))
roll_w     = max(6.0, min(roll_w, 120.0))
roll_od    = max(core_dia + 8.0, min(roll_od, 200.0))
clearance  = max(0.2, min(clearance, 3.0))
wall       = max(2.5, min(wall, 12.0))
base_len   = max(roll_od * 0.7, min(base_len, 260.0))
blade_ramp = max(12.0, min(blade_ramp, 80.0))
teeth      = max(3, min(teeth, 30))
screw_dia  = max(2.5, min(screw_dia, 8.0))

spindle_dia = max(4.0, core_dia - clearance)     # solid spindle the roll spins on
axis_z      = roll_od / 2.0 + wall               # spindle axis height (roll clears the base)
upright_h   = axis_z + spindle_dia / 2.0 + wall  # side wall height
inner_gap   = roll_w + 2.0                        # space between uprights for the roll
base_w      = inner_gap + 2.0 * wall              # base / upright span across the spindle


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


def _spindle_along_y(dia, length, x, z):
    """A solid cylinder whose axis runs along +Y, centred in Y, at (x, z)."""
    return (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(x, z, -length / 2.0))
        .circle(dia / 2.0)
        .extrude(length)
    )


def base_plate():
    """Flat base with rounded top corners (filleted BEFORE anything is unioned)."""
    body = _box(base_len, base_w, wall)
    try:
        body = body.edges("|Z").fillet(min(wall * 1.2, base_w / 6.0, base_len / 6.0))
    except Exception:
        pass
    return body


def two_uprights_and_spindle():
    """Base + two upright SIDE walls (left/right in Y) + a spindle running along
    Y that pierces BOTH walls.

    The spindle is a solid post; the roll slips over its OUTSIDE and spins in the
    `inner_gap` between the walls. The post spans the full base width so it is
    buried deep in both side walls (large overlap, never a tangent seam), giving
    one watertight solid. The spindle axis sits toward the back so the front of
    the base is clear for a tear ramp."""
    body = base_plate()
    # Side walls at ±(inner_gap/2 + wall/2) in Y, running along X (thin in Y).
    uy = inner_gap / 2.0 + wall / 2.0
    axis_x = -base_len / 2.0 + max(roll_od / 2.0 + wall, base_len * 0.35)
    wall_len = roll_od + 2.0 * wall            # front-to-back length of each side wall
    up_l = _box(wall_len, wall, upright_h, x=axis_x, y=-uy)
    up_r = _box(wall_len, wall, upright_h, x=axis_x, y=+uy)
    body = body.union(up_l).union(up_r)
    # Spindle runs along Y at (axis_x, axis_z), long enough to bury into both
    # side walls with a solid overlap of `wall` on each side.
    spindle = _spindle_along_y(spindle_dia, inner_gap + 2.0 * wall, axis_x, axis_z)
    body = body.union(spindle)
    return body, axis_x


def tear_ramp():
    """A forward ramp ending in a saw-tooth cutting edge (solid teeth unioned).
    Returns a solid Workplane sitting on the base, opening toward +X (front).

    Each tooth is a triangular prism whose BASE is embedded below the lip's top
    face (by `embed`) so it always overlaps the lip solid — a tangent (coincident)
    union would otherwise shear off a zero-volume sliver body."""
    ramp_h = axis_z * 0.55
    ramp_x0 = base_len / 2.0 - blade_ramp
    # Solid ramp block sitting on the base (overlaps the base's z=0..wall volume).
    ramp = _box(blade_ramp, base_w, wall, x=ramp_x0 + blade_ramp / 2.0)
    # A raised solid lip at the very front. Teeth are formed by CUTTING V-notches
    # into its top from above (upward-open cuts) — cutting into a solid can never
    # produce a floating body, unlike unioning many small tangent prisms.
    lip_x = base_len / 2.0 - wall * 0.8
    lip = _box(wall * 1.6, base_w, ramp_h, x=lip_x)
    body = ramp.union(lip)
    try:
        body = body.clean()
    except Exception:
        pass
    n = teeth
    pitch = base_w / n
    notch_depth = min(ramp_h * 0.45, pitch * 0.7)
    lip_top = wall + ramp_h
    # One V-notch cut centred on each tooth boundary, opening out of the top face.
    # A box rotated 45° about X presents a downward-pointing corner into the lip
    # top, carving a clean V; the teeth are the ridges left between the notches.
    for i in range(n + 1):
        yc = -base_w / 2.0 + i * pitch
        wedge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(lip_x, yc, lip_top))
            .transformed(rotate=cq.Vector(45, 0, 0))
            .box(wall * 3.0, notch_depth * 1.6, notch_depth * 1.6,
                 centered=(True, True, True))
        )
        body = body.cut(wedge)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_roll_holder():
    body, _ = two_uprights_and_spindle()
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_desk_dispenser():
    body, _ = two_uprights_and_spindle()
    body = body.union(tear_ramp())
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wall_spindle():
    """Wall bracket: a flat screw plate standing in the YZ plane with a single
    cantilevered spindle the roll slides onto from the open end."""
    plate_w = base_w
    plate_h = upright_h
    # Back plate: thickness in X, stands against the wall at x=0.
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(wall / 2.0, 0, 0))
        .box(wall, plate_w, plate_h, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|X").fillet(min(wall, plate_w / 6.0))
    except Exception:
        pass
    body = plate
    # Cantilevered spindle out along +X at axis height (open outer end).
    spindle_len = roll_w + 8.0
    spindle = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, axis_z, wall - 0.02))
        .circle(spindle_dia / 2.0)
        .extrude(spindle_len)
    )
    # A retaining end cap (slightly larger disc) so the roll doesn't slide off,
    # with a lead-in chamfer so it can still be pushed on.
    cap = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, axis_z, wall - 0.02 + spindle_len - wall))
        .circle(spindle_dia / 2.0 + 3.0)
        .extrude(wall)
    )
    try:
        cap = cap.faces(">X").edges().chamfer(min(2.0, spindle_dia * 0.15))
    except Exception:
        pass
    body = body.union(spindle).union(cap)
    # Screw holes through the plate (bored along +X), two vertical.
    inset = max(screw_dia + 5.0, 10.0)
    dz = plate_h / 2.0 - inset
    for zc in (plate_h / 2.0 - dz, plate_h / 2.0 + dz):
        cutter = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, zc, -2.0))
            .circle(screw_dia / 2.0)
            .extrude(wall + 4.0)
        )
        body = body.cut(cutter)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "desk_dispenser":
    result = build_desk_dispenser()
elif target_part == "wall_spindle":
    result = build_wall_spindle()
else:
    result = build_roll_holder()
