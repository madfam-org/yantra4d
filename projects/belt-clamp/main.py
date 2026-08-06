"""
Timing Belt Clamp / Tensioner — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Terminates or tensions a timing belt by gripping its teeth. The gripping face is a
comb of ridges cut to the belt's tooth pitch (GT2 = 2 mm, HTD-3M = 3 mm), so the
belt's valleys seat into the ridges and cannot pull out. Pick the belt profile;
the tooth pitch, ridge depth and jaw length follow.

Modes (dispatched via `target_part`):
  * "belt_clamp"  — a clamp body: a toothed jaw floor with side walls and bolt
                    holes; the belt lies teeth-down on the ridges and a plate (or
                    the mating frame) squeezes it down. Terminates a belt end.
  * "tensioner"   — a toothed grip on a body with a lengthwise adjustment SLOT, so
                    the clamp can slide to take up slack before the bolt is nipped.
  * "belt_joiner" — a bar with a toothed grip at EACH end (belt runs teeth-down)
                    to splice two belt ends into a closed loop.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `belt`).
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


# ── Belt table ───────────────────────────────────────────────────────────────
# pitch: tooth pitch (mm); ridge: mating ridge height (mm); belt_w: nominal belt
# width the jaw is sized for (mm).
BELT_TABLE = {
    "GT2-2mm": {"pitch": 2.0, "ridge": 0.75, "belt_w": 6.0},
    "HTD-3M":  {"pitch": 3.0, "ridge": 1.2,  "belt_w": 9.0},
}


def belt_spec(key):
    k = str(key).strip().upper().replace(" ", "")
    for name, spec in BELT_TABLE.items():
        if name.upper() == k:
            return spec
    return BELT_TABLE["GT2-2mm"]


# ── Parameters ───────────────────────────────────────────────────────────────
belt        = str(  PARAM(lambda: belt,      "GT2-2mm"))  # GT2-2mm | HTD-3M
teeth       = int(  PARAM(lambda: teeth,          6))     # gripping ridges per jaw
belt_w      = float(PARAM(lambda: belt_w,        7.0))    # channel width for the belt
wall        = float(PARAM(lambda: wall,          2.4))    # side-wall / body wall
floor       = float(PARAM(lambda: floor,         3.0))    # material under the tooth ridges
bolt_d      = float(PARAM(lambda: bolt_d,        3.4))    # clamp bolt clearance (≈ M3)
slot_len    = float(PARAM(lambda: slot_len,     16.0))    # tensioner adjustment slot length
mount_d     = float(PARAM(lambda: mount_d,       4.5))    # tensioner/joiner mounting hole (≈ M4)

target_part = str(  PARAM(lambda: target_part, "belt_clamp"))
# "belt_clamp" | "tensioner" | "belt_joiner"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = belt_spec(belt)
pitch = spec["pitch"]
ridge_h = spec["ridge"]
teeth = max(2, min(int(teeth), 40))
belt_w = max(spec["belt_w"] * 0.6, belt_w)
wall = max(1.6, wall)
floor = max(1.6, floor)
bolt_r = max(1.2, bolt_d / 2.0)

jaw_len = teeth * pitch                       # length of the toothed grip
channel_w = belt_w + 0.4                       # slight clearance for the belt
outer_w = channel_w + 2.0 * wall               # body width across the belt


def _tooth_comb(length, width, base_z):
    """A comb of triangular-ish ridges (peaks pointing +Z) at the belt pitch,
    running along +X from x=0 to x=length, spanning the given Y width, sitting on
    z=base_z. Ridges are trapezoidal prisms unioned onto a thin shared root so the
    result is a single watertight solid. The belt lies teeth-down and its valleys
    seat between ridges."""
    root_h = 0.6
    comb = (
        cq.Workplane("XY")
        .box(length, width, root_h, centered=(False, True, False))
        .translate((0, 0, base_z))
    )
    tw_top = pitch * 0.35
    tw_bot = pitch * 0.75
    n = int(length / pitch)
    for i in range(n):
        cx = (i + 0.5) * pitch
        # Trapezoid cross-section in XZ, extruded across Y → a ridge.
        ridge = (
            cq.Workplane("XZ")
            .workplane(offset=width / 2.0)
            .polyline([
                (cx - tw_bot / 2.0, base_z + root_h - 0.01),
                (cx + tw_bot / 2.0, base_z + root_h - 0.01),
                (cx + tw_top / 2.0, base_z + root_h + ridge_h),
                (cx - tw_top / 2.0, base_z + root_h + ridge_h),
            ])
            .close()
            .extrude(-width)
        )
        comb = comb.union(ridge)
    return comb


def _clamp_bolt_points(length):
    """Two clamp bolts flanking the toothed jaw along its length (outside the belt
    channel), at both ends of the grip."""
    y = channel_w / 2.0 + (outer_w - channel_w) / 4.0
    x0 = -(bolt_r + 1.5)
    x1 = length + (bolt_r + 1.5)
    return [(x0, -y), (x0, y), (x1, -y), (x1, y)]


def build_belt_clamp():
    """A U-channel clamp: a floor slab carrying the tooth comb, two side walls that
    guide the belt, and four bolt holes at the ends to squeeze a cover / frame
    onto the belt."""
    total_len = jaw_len + 2.0 * (bolt_r + 3.0)
    # Floor slab (clean blank), then tooth comb, then side walls, then bolts.
    floor_slab = (
        cq.Workplane("XY")
        .box(total_len, outer_w, floor, centered=(False, True, False))
        .translate((-(bolt_r + 3.0), 0, 0))
    )
    fr = min(bolt_r + 1.0, outer_w / 2.0 - 0.5)
    if fr > 0.2:
        floor_slab = floor_slab.edges("|Z").fillet(fr)

    body = floor_slab.union(_tooth_comb(jaw_len, channel_w, floor))

    # Side walls guiding the belt (rise above the ridge tops).
    wall_h = floor + ridge_h + 1.2
    for sy in (-1, 1):
        yc = sy * (channel_w / 2.0 + wall / 2.0)
        side = (
            cq.Workplane("XY")
            .box(jaw_len, wall, wall_h, centered=(False, True, False))
            .translate((0, yc, 0))
        )
        body = body.union(side)

    # Clamp bolts through the ends.
    pts = _clamp_bolt_points(jaw_len)
    cutter = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(bolt_r)
        .extrude(floor + 4.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(cutter)
    return body


def build_tensioner():
    """A toothed grip on a solid body with a lengthwise adjustment slot at the far
    end. The slot lets the whole clamp slide along a frame bolt to take up belt
    slack; the clamp bolts still nip the belt onto the teeth."""
    grip_len = jaw_len + 2.0 * (bolt_r + 3.0)
    total_len = grip_len + slot_len + wall + 6.0
    base = (
        cq.Workplane("XY")
        .box(total_len, outer_w, floor, centered=(False, True, False))
        .translate((-(bolt_r + 3.0), 0, 0))
    )
    fr = min(bolt_r + 1.0, outer_w / 2.0 - 0.5)
    if fr > 0.2:
        base = base.edges("|Z").fillet(fr)
    body = base.union(_tooth_comb(jaw_len, channel_w, floor))

    # Side walls over the toothed section only.
    wall_h = floor + ridge_h + 1.2
    for sy in (-1, 1):
        yc = sy * (channel_w / 2.0 + wall / 2.0)
        side = (
            cq.Workplane("XY")
            .box(jaw_len, wall, wall_h, centered=(False, True, False))
            .translate((0, yc, 0))
        )
        body = body.union(side)

    # Clamp bolts (nip the belt).
    pts = _clamp_bolt_points(jaw_len)
    body = body.cut(
        cq.Workplane("XY").pushPoints(pts).circle(bolt_r)
        .extrude(floor + 4.0).translate((0, 0, -1.0))
    )

    # Adjustment SLOT at the far end: an obround (two holes + a bridging box).
    slot_x0 = grip_len - (bolt_r + 3.0) + wall + 2.0
    sr = max(1.5, mount_d / 2.0)
    slot_cut = (
        cq.Workplane("XY")
        .box(slot_len, 2.0 * sr, floor + 4.0, centered=(False, True, False))
        .translate((slot_x0, 0, -1.0))
    )
    ends = (
        cq.Workplane("XY")
        .pushPoints([(slot_x0, 0), (slot_x0 + slot_len, 0)])
        .circle(sr).extrude(floor + 4.0).translate((0, 0, -1.0))
    )
    body = body.cut(slot_cut).cut(ends)
    return body


def build_belt_joiner():
    """A flat bar with a tooth comb at EACH end (belt runs teeth-down along the
    top), plus clamp bolts at each grip, to splice two belt ends into a loop."""
    gap = pitch * 2.0                            # smooth centre span
    grip = jaw_len
    total_len = 2.0 * grip + gap + 2.0 * (bolt_r + 3.0)
    base = (
        cq.Workplane("XY")
        .box(total_len, outer_w, floor, centered=(False, True, False))
        .translate((-(bolt_r + 3.0), 0, 0))
    )
    fr = min(bolt_r + 1.0, outer_w / 2.0 - 0.5)
    if fr > 0.2:
        base = base.edges("|Z").fillet(fr)

    body = base.union(_tooth_comb(grip, channel_w, floor))
    body = body.union(_tooth_comb(grip, channel_w, floor).translate((grip + gap, 0, 0)))

    # Side walls run the full toothed length.
    wall_h = floor + ridge_h + 1.2
    span = 2.0 * grip + gap
    for sy in (-1, 1):
        yc = sy * (channel_w / 2.0 + wall / 2.0)
        side = (
            cq.Workplane("XY")
            .box(span, wall, wall_h, centered=(False, True, False))
            .translate((0, yc, 0))
        )
        body = body.union(side)

    # Clamp bolts at both grips.
    y = channel_w / 2.0 + (outer_w - channel_w) / 4.0
    xs = [-(bolt_r + 1.5), grip + gap + grip + (bolt_r + 1.5)]
    pts = [(xs[0], -y), (xs[0], y), (xs[1], -y), (xs[1], y)]
    body = body.cut(
        cq.Workplane("XY").pushPoints(pts).circle(bolt_r)
        .extrude(floor + 4.0).translate((0, 0, -1.0))
    )
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tensioner":
    result = build_tensioner()
elif target_part == "belt_joiner":
    result = build_belt_joiner()
else:  # "belt_clamp"
    result = build_belt_clamp()
