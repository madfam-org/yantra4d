"""
Motor Soft-Mount Pod — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A vibration-isolating motor pod for FPV / RC brushless motors. The motor bolts
to a top plate carrying the standard square hole pattern (9×9 M2, 16×16 or 19×19
M3); the plate clamps onto the arm/boom. In "soft" mode flex slots decouple the
motor plate from the clamp so airframe vibration is damped (print in TPU for the
compliant version); "rigid" is a solid pod; "skid" adds a stubby landing foot.

Reuses the shared `motor_bolt_points()` / `motor_screw_d()` helper — the same
motor bolt-pattern interface used across the drone Commons (prop-guard,
motor-soft-mount, landing-skid).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `motor_pattern`).
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


# ── Shared motor bolt-pattern interface (reused across the drone Commons) ─────
MOTOR_PATTERNS = {"16x16": 16.0, "19x19": 19.0, "9x9": 9.0}


def motor_bolt_points(pattern):
    """Return the 4 (x,y) motor-screw centres for a square NxN mount pattern."""
    s = MOTOR_PATTERNS.get(pattern, 16.0)
    h = s / 2.0
    return [(h, h), (h, -h), (-h, h), (-h, -h)]


def motor_screw_d(pattern):
    """Screw clearance diameter: 9x9 boards use M2, 16/19 use M3."""
    return 2.4 if pattern == "9x9" else 3.4


def motor_span(pattern):
    """Diagonal-ish footprint span (mm) covered by the pattern."""
    return MOTOR_PATTERNS.get(pattern, 16.0)


# ── Parameters ───────────────────────────────────────────────────────────────
motor_pattern = str(PARAM(lambda: motor_pattern, "16x16"))   # 16x16 | 19x19 | 9x9
plate_thick   = float(PARAM(lambda: plate_thick,   4.0))     # motor plate thickness (Z)
bore_d        = float(PARAM(lambda: bore_d,       10.0))     # central shaft/bell clearance bore
arm_width     = float(PARAM(lambda: arm_width,    12.0))     # frame arm/boom width to clamp
arm_thick     = float(PARAM(lambda: arm_thick,     5.0))     # frame arm thickness (clamp depth)
clamp_wall    = float(PARAM(lambda: clamp_wall,    3.0))     # clamp wall around the arm
iso_gap       = float(PARAM(lambda: iso_gap,       2.4))     # isolation gap (soft mode)
flex_slots    = int(  PARAM(lambda: flex_slots,      3))     # number of TPU flex slots per side
foot_dia      = float(PARAM(lambda: foot_dia,     16.0))     # landing-foot diameter (skid mode)
foot_drop     = float(PARAM(lambda: foot_drop,    14.0))     # how far the foot drops below the pod

target_part   = str(PARAM(lambda: target_part, "soft_mount"))
# "soft_mount" | "rigid_mount" | "skid_mount"


# ── Derived / clamped geometry ───────────────────────────────────────────────
span = motor_span(motor_pattern)
plate_w = span + 12.0                       # plate footprint (square), motor holes + rim
plate_w = max(plate_w, bore_d + 8.0)
screw_r = max(0.8, motor_screw_d(motor_pattern) / 2.0)
bore_r = max(1.0, min(bore_d / 2.0, plate_w / 2.0 - screw_r - 3.0))
clamp_h = arm_thick + 2.0 * clamp_wall      # outer clamp block height
clamp_w = arm_width + 2.0 * clamp_wall      # outer clamp block width


def _motor_plate():
    """Square motor plate with the standard bolt pattern + central bore.
    Top face at z=0, body extends downward to z=-plate_thick."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -plate_thick / 2.0))
        .box(plate_w, plate_w, plate_thick, centered=(True, True, True))
    )
    try:
        plate = plate.edges("|Z").fillet(min(3.0, plate_w / 2.0 - 0.6))
    except Exception:
        pass
    # Central bore for the motor bell / shaft.
    plate = (
        plate.faces(">Z").workplane()
        .circle(bore_r).cutThruAll()
    )
    # Motor screw holes.
    plate = (
        plate.faces(">Z").workplane()
        .pushPoints(motor_bolt_points(motor_pattern))
        .circle(screw_r).cutThruAll()
    )
    return plate


def _arm_clamp(z_top):
    """A clamp block that grips the frame arm, with a rectangular arm slot and a
    print-in-place split gap. Its top sits at `z_top` (fuses into the pod above).
    Boom runs along X (so the arm slides through in X)."""
    block = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - clamp_h / 2.0))
        .box(plate_w, clamp_w, clamp_h, centered=(True, True, True))
    )
    # Arm slot: rectangular channel through X.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - clamp_h / 2.0))
        .box(plate_w + 2.0, arm_width, arm_thick, centered=(True, True, True))
    )
    block = block.cut(slot)
    # Clamp split (a thin kerf from the bottom up to the arm slot so it flexes
    # onto the boom and a zip-tie / screw pinches it).
    kerf = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - clamp_h + (clamp_h - arm_thick) / 4.0))
        .box(plate_w + 2.0, 1.2, (clamp_h - arm_thick) / 2.0, centered=(True, True, True))
    )
    block = block.cut(kerf)
    return block


def _neck(z_top, z_bot, width):
    """Solid neck column joining the motor plate down to the clamp/foot."""
    h = z_top - z_bot
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, (z_top + z_bot) / 2.0))
        .box(width, width, h, centered=(True, True, True))
    )


def _flex_slots(z_top, z_bot):
    """Horizontal slots cut through the neck to make it compliant (soft mode).
    Slots run through Y, stacked in Z between the plate and the clamp."""
    cutter = None
    h = z_top - z_bot
    if flex_slots < 1 or h <= 3.0:
        return None
    step = h / (flex_slots + 1)
    slot_w = max(0.8, min(iso_gap, step * 0.5))
    for i in range(1, flex_slots + 1):
        z = z_bot + i * step
        # Alternate slot entry side (comb pattern) for real compliance.
        x_off = (plate_w * 0.25) if (i % 2 == 0) else (-plate_w * 0.25)
        s = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x_off, 0, z))
            .box(plate_w * 0.75, arm_width + 4.0, slot_w, centered=(True, True, True))
        )
        cutter = s if cutter is None else cutter.union(s)
    return cutter


def build_pod(mode):
    """Assemble motor plate + neck + (clamp | foot). `mode` selects flex/rigid/skid."""
    plate = _motor_plate()

    # Geometry stack (Z): plate top at 0, plate bottom at -plate_thick.
    z_plate_bot = -plate_thick
    neck_width = max(arm_width, span * 0.6)

    if mode == "skid_mount":
        # Neck down to a landing foot.
        z_foot_top = z_plate_bot - foot_drop
        neck = _neck(z_plate_bot, z_foot_top, neck_width)
        foot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z_foot_top - 2.0))
            .circle(max(3.0, foot_dia / 2.0))
            .extrude(-4.0)
        )
        try:
            foot = foot.edges("<Z").fillet(min(2.0, foot_dia / 4.0))
        except Exception:
            pass
        body = plate.union(neck).union(foot)
        return body

    # soft / rigid: neck down to an arm clamp.
    z_clamp_top = z_plate_bot - (iso_gap if mode == "soft_mount" else 0.0)
    clamp = _arm_clamp(z_clamp_top)
    neck = _neck(z_plate_bot + 0.01, z_clamp_top, neck_width)

    if mode == "soft_mount":
        # Compliant comb neck: horizontal slots let the motor plate float on the
        # clamp so airframe vibration is damped (print the flex version in TPU).
        neck_slots = _flex_slots(z_plate_bot, z_clamp_top)
        if neck_slots is not None:
            neck = neck.cut(neck_slots)
    body = plate.union(neck).union(clamp)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rigid_mount":
    result = build_pod("rigid_mount")
elif target_part == "skid_mount":
    result = build_pod("skid_mount")
else:  # "soft_mount"
    result = build_pod("soft_mount")
