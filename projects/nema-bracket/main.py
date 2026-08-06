"""
NEMA Stepper Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Mounts a NEMA 17 or NEMA 23 stepper motor. The motor face carries the correct
square bolt pattern (NEMA 17: 31 mm square, M3; NEMA 23: 47.14 mm square, M4/M5)
plus a central pilot bore that clears the motor's raised boss and shaft. Pick the
motor by its NEMA size; the bolt square, pilot bore, and plate size follow.

Modes (dispatched via `target_part`):
  * "l_bracket"       — an L-mount: a vertical motor plate (motor bolts on the
                        face) joined to a horizontal base with its own mounting
                        bolt holes, gusseted at the corner.
  * "flat_bracket"    — a flat surface plate: the motor bolts through one face,
                        the plate itself bolts flat to a panel via corner holes.
  * "extrusion_mount" — a motor plate with a perpendicular foot sized to sit on
                        a 2020 aluminium T-slot extrusion (slot bolt holes).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `nema`).
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


# ── NEMA motor table ─────────────────────────────────────────────────────────
# body: motor body width (square, mm); bolt: bolt-square spacing (mm);
# bolt_d: mounting bolt clearance dia; pilot: central pilot-bore dia (clears the
# motor's raised register boss).
NEMA_TABLE = {
    "NEMA17": {"body": 42.3, "bolt": 31.0, "bolt_d": 3.4, "pilot": 23.0},
    "NEMA23": {"body": 57.0, "bolt": 47.14, "bolt_d": 5.2, "pilot": 38.5},
}


def nema_spec(key):
    k = str(key).strip().upper().replace(" ", "").replace("-", "")
    return NEMA_TABLE.get(k, NEMA_TABLE["NEMA17"])


# ── Parameters ───────────────────────────────────────────────────────────────
nema        = str(  PARAM(lambda: nema,      "NEMA17"))  # NEMA17 | NEMA23
plate_t     = float(PARAM(lambda: plate_t,      5.0))    # motor plate thickness
margin      = float(PARAM(lambda: margin,       6.0))    # material around the bolt square
base_len    = float(PARAM(lambda: base_len,    45.0))    # base / foot length (L & extrusion)
base_t      = float(PARAM(lambda: base_t,       5.0))    # base / foot thickness
base_bolt_d = float(PARAM(lambda: base_bolt_d,  5.2))    # base mounting bolt clearance (≈ M5)
gusset      = bool( PARAM(lambda: gusset,      True))    # add a corner gusset (L-bracket)
pilot_open  = bool( PARAM(lambda: pilot_open,  True))    # cut the central pilot bore

target_part = str(  PARAM(lambda: target_part, "l_bracket"))
# "l_bracket" | "flat_bracket" | "extrusion_mount"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = nema_spec(nema)
body_w = spec["body"]
bolt_sq = spec["bolt"]
bolt_d = spec["bolt_d"]
pilot_d = spec["pilot"]

plate_t = max(3.0, plate_t)
margin = max(3.0, margin)
base_t = max(3.0, base_t)
plate_side = bolt_sq + 2.0 * (bolt_d / 2.0 + margin)   # square motor plate side
plate_side = max(plate_side, body_w + 4.0)             # never smaller than the body
half = bolt_sq / 2.0
bolt_r = bolt_d / 2.0
base_bolt_r = max(1.5, base_bolt_d / 2.0)


# ── Helpers ──────────────────────────────────────────────────────────────────
def motor_bolt_points():
    """The four motor bolts on a square pattern, centred on the origin."""
    return [(-half, -half), (half, -half), (half, half), (-half, half)]


def motor_plate():
    """A square motor plate lying in XY (base at z=0), rounded verticals, with the
    four bolt holes and (optionally) the central pilot bore cut through. The plate
    is filleted while still a clean blank, BEFORE any holes are cut."""
    plate = (
        cq.Workplane("XY")
        .box(plate_side, plate_side, plate_t, centered=(True, True, False))
    )
    fr = min(bolt_r + 1.5, plate_side / 2.0 - 0.5)
    if fr > 0.2:
        plate = plate.edges("|Z").fillet(fr)   # fillet CLEAN blank first

    # Four motor bolts, grouped in one pushPoints cut.
    cutter = (
        cq.Workplane("XY")
        .pushPoints(motor_bolt_points())
        .circle(bolt_r)
        .extrude(plate_t + 2.0)
        .translate((0, 0, -1.0))
    )
    plate = plate.cut(cutter)

    if pilot_open:
        pilot = (
            cq.Workplane("XY")
            .circle(pilot_d / 2.0)
            .extrude(plate_t + 2.0)
            .translate((0, 0, -1.0))
        )
        plate = plate.cut(pilot)
    return plate


def base_slab(length, width, thick, hole_pts, hole_r):
    """A rectangular base/foot slab on XY (base at z=0). Filleted as a clean blank
    then drilled with the given hole points (grouped)."""
    slab = cq.Workplane("XY").box(length, width, thick, centered=(True, True, False))
    fr = min(hole_r + 1.5, width / 2.0 - 0.5, length / 2.0 - 0.5)
    if fr > 0.2:
        slab = slab.edges("|Z").fillet(fr)
    if hole_pts:
        cutter = (
            cq.Workplane("XY")
            .pushPoints(hole_pts)
            .circle(hole_r)
            .extrude(thick + 2.0)
            .translate((0, 0, -1.0))
        )
        slab = slab.cut(cutter)
    return slab


# ── Builders ─────────────────────────────────────────────────────────────────
def build_flat_bracket():
    """Just the flat motor plate, but with four extra corner holes so the plate
    itself can bolt flat onto a panel around the motor footprint."""
    plate = motor_plate()
    # Corner mounting holes, just inside the rounded corners.
    c = plate_side / 2.0 - (base_bolt_r + 2.5)
    corner_pts = [(-c, -c), (c, -c), (c, c), (-c, c)]
    cutter = (
        cq.Workplane("XY")
        .pushPoints(corner_pts)
        .circle(base_bolt_r)
        .extrude(plate_t + 2.0)
        .translate((0, 0, -1.0))
    )
    return plate.cut(cutter)


def build_l_bracket():
    """Vertical motor plate + horizontal base, sharing the bottom edge, with an
    optional triangular gusset. Motor bolts on the vertical face; base bolts down
    through the horizontal slab."""
    base_w = plate_side
    # Horizontal base: spans +X away from the plate; two mounting holes.
    hx = (plate_side / 2.0 + base_len) / 2.0 - (base_bolt_r + 2.5)
    hy = base_w / 2.0 - (base_bolt_r + 3.0)
    base_pts = [(hx, -hy), (hx, hy), (0.0, -hy), (0.0, hy)]
    base = base_slab(plate_side + base_len, base_w, base_t, base_pts, base_bolt_r)
    # Shift the base so its left edge sits under the plate, plate at X≈ -plate_side/2..
    base = base.translate((base_len / 2.0, 0, 0))

    # Vertical motor plate: rotate the XY plate up so it stands on the base's
    # left end. After +90° about Y the plate (was z:0..plate_t) occupies
    # x:-plate_t..0 and spans y & z symmetrically about the origin.
    plate = motor_plate()
    plate = plate.rotate((0, 0, 0), (0, 1, 0), 90.0)
    # Lift it to stand on the base top and align to the base's left end.
    plate = plate.translate((-base_len / 2.0, 0, plate_side / 2.0 + base_t))
    body = base.union(plate)

    if gusset:
        # Right-triangle gusset in the XZ plane bridging plate ↔ base.
        gl = min(base_len * 0.7, plate_side * 0.6)
        gz = min(plate_side * 0.6, gl)
        gw = min(plate_side * 0.5, body_w * 0.5)
        tri = (
            cq.Workplane("XZ")
            .workplane(offset=gw / 2.0)
            .polyline([(0, base_t), (gl, base_t), (0, base_t + gz)])
            .close()
            .extrude(-gw)
            .translate((-base_len / 2.0, 0, 0))
        )
        body = body.union(tri)
    return body


def build_extrusion_mount():
    """Motor plate standing vertically on a foot shaped to sit across a 2020
    aluminium T-slot extrusion. The foot has two bolt holes on 20 mm centres to
    drop M5 T-nuts into the extrusion slots."""
    foot_len = max(base_len, 40.0)
    foot_w = plate_side
    # 2020 extrusion: bolt into slots on a 20 mm-spaced grid along the foot.
    slot_pitch = 20.0
    n = max(2, int(foot_len // slot_pitch))
    start = -((n - 1) * slot_pitch) / 2.0
    foot_pts = []
    for i in range(n):
        x = start + i * slot_pitch
        foot_pts.append((x, 0.0))
    foot = base_slab(foot_len, foot_w, base_t, foot_pts, base_bolt_r)

    plate = motor_plate()
    plate = plate.rotate((0, 0, 0), (0, 1, 0), 90.0)
    plate = plate.translate((-foot_len / 2.0 + plate_t / 2.0,
                             0, plate_side / 2.0 + base_t))
    body = foot.union(plate)

    if gusset:
        gl = min(foot_len * 0.5, plate_side * 0.55)
        gz = min(plate_side * 0.6, gl)
        gw = min(plate_side * 0.5, body_w * 0.5)
        tri = (
            cq.Workplane("XZ")
            .workplane(offset=gw / 2.0)
            .polyline([(0, base_t), (gl, base_t), (0, base_t + gz)])
            .close()
            .extrude(-gw)
            .translate((-foot_len / 2.0 + plate_t, 0, 0))
        )
        body = body.union(tri)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "flat_bracket":
    result = build_flat_bracket()
elif target_part == "extrusion_mount":
    result = build_extrusion_mount()
else:  # "l_bracket"
    result = build_l_bracket()
