"""
Broom / Tool Wall Gripper — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A sprung-jaw gripper that holds a cylindrical tool handle (broom, mop, rake,
push-broom) by friction against a wall. The jaw is a C whose mouth is slightly
NARROWER than the handle: pushing the handle in spreads the compliant arms, and
their springback grips it. A back plate with screw holes fixes it to the wall.

Two parts (dispatched through `target_part`):
  * "gripper"        — a single sprung-jaw gripper on a screw-mount plate.
  * "gripper_strip"  — a horizontal strip of `count` grippers on one shared
                       plate, so a row of tools hangs from a single rail.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `handle_dia`).
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
target_part = str(PARAM(lambda: target_part, "gripper"))  # gripper | gripper_strip

handle_dia = float(PARAM(lambda: handle_dia, 25.0))       # tool handle diameter (mm)
mouth_factor = float(PARAM(lambda: mouth_factor, 0.78))   # mouth width ÷ handle_dia (<1 to snap)
jaw_wall = float(PARAM(lambda: jaw_wall, 3.0))            # thickness of the compliant arms
jaw_depth = float(PARAM(lambda: jaw_depth, 16.0))         # jaw depth along the handle axis

plate_thick = float(PARAM(lambda: plate_thick, 4.0))      # wall plate thickness
plate_margin = float(PARAM(lambda: plate_margin, 8.0))    # plate material around the jaw
screw_dia = float(PARAM(lambda: screw_dia, 4.5))         # wall-screw clearance hole

count = int(PARAM(lambda: count, 3))                     # grippers in a strip
spacing = float(PARAM(lambda: spacing, 70.0))            # centre-to-centre spacing (strip)

# Sanitize
handle_dia = max(6.0, handle_dia)
jaw_wall = max(1.6, jaw_wall)
mouth_factor = max(0.5, min(0.95, mouth_factor))
count = max(2, min(8, count))

r_handle = handle_dia / 2.0
r_out = r_handle + jaw_wall                                # outer radius of the jaw ring


# ── Jaw geometry ──────────────────────────────────────────────────────────────
def _jaw(depth):
    """One sprung C-jaw, axis along Y (handle direction). The jaw ring is an
    annulus with a front mouth removed; the mouth is narrower than the handle so
    the arms must flex to admit it. Base sits at z=0; the handle centre is at
    z = r_out. Returns the jaw as a solid."""
    ring = (
        cq.Workplane("XZ")
        .circle(r_out)
        .circle(r_handle)
        .extrude(depth)
        .translate((0, -depth / 2.0, r_out))
    )
    # Mouth opening on the front (+... actually top) — remove a slot whose width
    # is the mouth width, from the top of the ring down past the centre so the
    # handle can be pushed in from above.
    mouth_w = mouth_factor * handle_dia
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, r_out + r_handle * 0.5))
        .box(mouth_w, depth + 2.0, r_out * 2.0, centered=(True, True, False))
    )
    jaw = ring.cut(mouth)
    # Flare the mouth lips outward slightly so the handle self-guides in.
    jaw = _flare_lips(jaw, depth, mouth_w)
    return jaw


def _flare_lips(jaw, depth, mouth_w):
    """Add two small chamfered lead-in tabs at the mouth so the handle centres
    itself. Non-fatal if the fillet/chamfer fails."""
    lip_h = min(jaw_wall * 1.5, r_out * 0.5)
    for sx in (-1, 1):
        lip = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (mouth_w / 2.0 + jaw_wall / 2.0), 0, 2.0 * r_out - lip_h))
            .box(jaw_wall, depth, lip_h, centered=(True, True, False))
        )
        try:
            jaw = jaw.union(lip)
        except Exception:
            pass
    return jaw


def _wall_plate(width, height):
    """Flat wall plate: front face at y=0, thickness toward -Y, base at z=0.
    The jaw grows from the front face toward +Y (away from the wall)."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -plate_thick, 0))
        .box(width, plate_thick, height, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Y").fillet(min(plate_margin / 2.0, 4.0))
    except Exception:
        pass
    return plate


def _screw_holes(plate, xs, height, width):
    """Bore wall-screw clearance holes through the plate (through -Y). Holes at
    each x in `xs`, vertically near top and bottom of the plate."""
    r = screw_dia / 2.0
    if r <= 0.05:
        return plate
    zs = [max(r + 2.0, plate_margin), height - max(r + 2.0, plate_margin)]
    if zs[1] - zs[0] < 4.0:
        zs = [height / 2.0]
    for x in xs:
        for z in zs:
            bore = (
                cq.Workplane("XZ")
                .center(x, z)
                .circle(r)
                .extrude(-(plate_thick + 2.0))
                .translate((0, 1.0, 0))
            )
            plate = plate.cut(bore)
    return plate


# ── Part builders ─────────────────────────────────────────────────────────────
def build_gripper():
    """One jaw on a single-hole-column plate."""
    depth = max(handle_dia * 0.5, jaw_depth)
    width = handle_dia + 2.0 * (jaw_wall + plate_margin)
    height = 2.0 * r_out + 2.0 * plate_margin

    plate = _wall_plate(width, height)
    plate = _screw_holes(plate, [0.0], height, width)

    # Jaw centred on the plate; handle centre at z = plate_margin + r_out.
    jaw = _jaw(depth).translate((0, 0, plate_margin))
    body = plate.union(jaw)
    return body


def build_gripper_strip():
    """`count` jaws on one shared plate, evenly spaced along X."""
    depth = max(handle_dia * 0.5, jaw_depth)
    pitch = max(handle_dia + 2.0 * jaw_wall + 6.0, spacing)
    width = (count - 1) * pitch + handle_dia + 2.0 * (jaw_wall + plate_margin)
    height = 2.0 * r_out + 2.0 * plate_margin

    plate = _wall_plate(width, height)

    x0 = -(count - 1) * pitch / 2.0
    xs = [x0 + i * pitch for i in range(count)]
    plate = _screw_holes(plate, xs, height, width)

    body = plate
    for x in xs:
        jaw = _jaw(depth).translate((x, 0, plate_margin))
        body = body.union(jaw)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "gripper_strip":
    result = build_gripper_strip()
else:
    result = build_gripper()
