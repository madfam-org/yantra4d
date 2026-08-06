"""
NATO Accessory Rail & Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The NATO accessory rail — a dovetail cross-section with ~44° flanks and small
safety notches that photo/video and firearms-adjacent accessory ecosystems
share for quick-release mounting. This cartridge builds a length of NATO rail
with mounting holes, a quick-release clamp that grips the rail dovetail, and a
rail adapter that carries a 1/4-20 face on the back of a rail section.

NATO rail geometry (nominal, dimensionally real):
  - rail top width      ≈ 21.2 mm  (the wide upper platform)
  - flank angle         ≈ 44°       (dovetail undercut from vertical)
  - rail height         ≈ 6.0 mm    (dovetail block height)
  - safety notch        ≈ 1.5 mm    slots across the top for a spring detent
  - the clamp jaw flanks match the 44° angle so tightening pulls the rail down
    into the fixed jaw (a self-centring dovetail grip).

Watertight strategy:
  The rail and both clamp jaws are extruded 2D cross-sections (the dovetail
  profile). The clamp's rail channel is a through-slot (open both ends → vents
  to outside). Safety notches are shallow open grooves. The clamp bolt is a
  through-hole. Every union overlaps into shared material; fillets (if any) are
  applied to clean blanks BEFORE feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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


# ── Parameters (NATO accessory rail standard) ────────────────────────────────
target_part = str(PARAM(lambda: target_part, "nato_rail_section"))
# "nato_rail_section" | "nato_clamp" | "rail_adapter"

rail_w = float(PARAM(lambda: rail_w, 21.2))         # rail top platform width (X)
flank_ang = float(PARAM(lambda: flank_ang, 44.0))   # dovetail flank angle (deg from vertical)
rail_h = float(PARAM(lambda: rail_h, 6.0))          # dovetail block height (Z)
rail_len = float(PARAM(lambda: rail_len, 50.0))     # rail length (Y)
notch_w = float(PARAM(lambda: notch_w, 1.5))        # safety notch width (mm)
notch_count = int(PARAM(lambda: notch_count, 3))    # number of safety notches

base_th = float(PARAM(lambda: base_th, 4.0))        # rail base plate thickness under the dovetail
mount_hole_d = float(PARAM(lambda: mount_hole_d, 4.5))  # rail mounting hole (M4 clearance)

clamp_clear = float(PARAM(lambda: clamp_clear, 0.35))   # clamp-to-rail fit slop (per side)
wall = float(PARAM(lambda: wall, 4.0))              # clamp wall / jaw thickness (mm)
clamp_bolt_d = float(PARAM(lambda: clamp_bolt_d, 5.2))  # clamp bolt clearance (M5)

face_hole_d = float(PARAM(lambda: face_hole_d, 6.6))    # 1/4-20 adapter face hole (mm)
face_th = float(PARAM(lambda: face_th, 6.0))        # adapter back-face thickness

# Clamp to sane ranges so extreme UI values never crash the kernel.
rail_w = max(12.0, min(rail_w, 40.0))
flank_ang = max(30.0, min(flank_ang, 55.0))
rail_h = max(3.0, min(rail_h, 14.0))
rail_len = max(15.0, min(rail_len, 200.0))
notch_w = max(0.8, min(notch_w, 4.0))
notch_count = max(0, min(notch_count, 12))
base_th = max(2.0, min(base_th, 12.0))
mount_hole_d = max(2.5, min(mount_hole_d, 8.0))
clamp_clear = max(0.1, min(clamp_clear, 0.8))
wall = max(2.5, min(wall, 10.0))
clamp_bolt_d = max(2.5, min(clamp_bolt_d, 8.0))
face_hole_d = max(3.0, min(face_hole_d, 10.0))
face_th = max(3.0, min(face_th, 15.0))

# Dovetail bottom width = top width + 2 * height * tan(flank). Because the flank
# undercuts, the BOTTOM is wider than the top (a proper dovetail that a jaw
# hooks under).
_flank_dx = rail_h * math.tan(math.radians(flank_ang))
rail_bot_w = rail_w + 2.0 * _flank_dx


# ── Cross-section primitives ─────────────────────────────────────────────────
def _dovetail_profile(top_w, height, flank_dx, extra_bottom=0.0):
    """The NATO dovetail cross-section in XZ, centred on X, base at z=0.
    Wider at the bottom (undercut). `extra_bottom` grows the very bottom for a
    clamp cut so the tool clears. Returns an extrudable Workplane profile."""
    htw = top_w / 2.0
    hbw = htw + flank_dx + extra_bottom
    pts = [
        (-hbw, 0.0),
        (hbw, 0.0),
        (htw, height),
        (-htw, height),
    ]
    return cq.Workplane("XZ").polyline(pts).close()


def _rail_solid(top_w, height, flank_dx, length):
    """The dovetail bar, centred on Y (spans -length/2 .. +length/2). An XZ
    sketch extrudes symmetrically via both=True so it never drifts off the
    plate it sits on."""
    return _dovetail_profile(top_w, height, flank_dx).extrude(length / 2.0, both=True)


# ── Part builders ────────────────────────────────────────────────────────────
def build_nato_rail_section():
    """A length of NATO rail: the dovetail bar sitting on a base plate, with
    safety notches across the top and mounting holes down the centre."""
    # Base plate under the dovetail (a touch wider than the dovetail bottom).
    plate_w = rail_bot_w + 2.0 * 2.0
    plate = (
        cq.Workplane("XY")
        .box(plate_w, rail_len, base_th, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(2.0, base_th - 0.2, plate_w / 2.0 - 0.5))
    except Exception:
        pass

    # Dovetail on top of the plate (centred on Y), overlapping down into it.
    rail = _rail_solid(rail_w, rail_h + 0.5, _flank_dx, rail_len).translate(
        (0, 0, base_th - 0.5)
    )
    body = plate.union(rail)

    # Safety notches: shallow transverse grooves across the top of the dovetail,
    # evenly spaced. Open grooves (vent to outside).
    if notch_count > 0:
        top_z = base_th - 0.5 + rail_h + 0.5
        step = rail_len / (notch_count + 1)
        for i in range(1, notch_count + 1):
            y = -rail_len / 2.0 + i * step
            notch = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, y, top_z - 1.5))
                .box(rail_w + 2.0 * _flank_dx + 2.0, notch_w, 2.0, centered=(True, True, False))
            )
            body = body.cut(notch)

    # Mounting holes through the plate (between notches), through-holes.
    hr = max(0.5, mount_hole_d / 2.0)
    nh = max(1, min(3, int(rail_len // 25)))
    if nh == 1:
        ys = [0.0]
    else:
        span = rail_len - 12.0
        ys = [-span / 2.0 + j * (span / (nh - 1)) for j in range(nh)]
    for y in ys:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, -0.01))
            .circle(hr)
            .extrude(base_th + 0.02)
        )
        body = body.cut(hole)
    return body


def build_nato_clamp():
    """A quick-release clamp that grips the rail dovetail: a body with a
    matching dovetail channel (grown by clearance) cut through it, split by a
    slit so one jaw flexes, closed by a cross bolt. A 1/4-20 face on top mounts
    an accessory to whatever rail it clamps."""
    ch_top_w = rail_w + 2.0 * clamp_clear
    ch_h = rail_h + clamp_clear

    body_w = rail_bot_w + 2.0 * wall
    body_h = ch_h + wall + 2.0
    body_len = min(rail_len, 26.0)

    block = (
        cq.Workplane("XY")
        .box(body_w, body_len, body_h, centered=(True, True, False))
    )
    try:
        block = block.edges("|Z").fillet(min(2.0, wall - 0.5))
    except Exception:
        pass

    # Dovetail channel, cut UP from the bottom, through both Y ends so the clamp
    # slides onto a rail end (open → vents to outside).
    ch_flank_dx = ch_h * math.tan(math.radians(flank_ang))
    chan = (
        _dovetail_profile(ch_top_w, ch_h, ch_flank_dx, extra_bottom=0.6)
        .extrude((body_len + 2.0) / 2.0, both=True)  # centred on Y, through both ends
        .translate((0, 0, -0.01))
    )
    body = block.cut(chan)

    # Flex slit: a vertical through-slot on ONE side reaching from the channel
    # roof up toward the top, letting that jaw open. Cut through Y.
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(body_w / 2.0 - wall * 0.5, 0, ch_h))
        .box(1.6, body_len + 2.0, body_h, centered=(True, True, False))
    )
    body = body.cut(slit)

    # Clamp bolt across X, through the flexing jaw above the channel.
    bolt_z = ch_h + (body_h - ch_h) * 0.5
    bolt = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, bolt_z, 0))
        .circle(max(0.5, clamp_bolt_d / 2.0))
        .extrude(body_w / 2.0 + 1.0, both=True)
    )
    body = body.cut(bolt)

    # 1/4-20 accessory hole into the top face (drilled from above → vented).
    hr = max(0.5, face_hole_d / 2.0)
    depth = min(body_h - ch_h - 1.0, body_h - 1.0)
    depth = max(2.5, depth)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, body_h - depth))
        .circle(hr)
        .extrude(depth + 1.0)
    )
    body = body.cut(hole)
    return body


def build_rail_adapter():
    """A short NATO rail section with a perpendicular accessory face on the back
    carrying a 1/4-20 hole — bridges a NATO-rail device to a 1/4-20 accessory or
    arm. The dovetail faces up; the face stands off the back edge."""
    sect_len = min(rail_len, 40.0)

    # Base plate + dovetail (reuse the rail-section geometry, shorter, no notches
    # so it reads distinctly from the rail_section mode).
    plate_w = rail_bot_w + 2.0 * 2.0
    plate = (
        cq.Workplane("XY")
        .box(plate_w, sect_len, base_th, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(2.0, base_th - 0.2))
    except Exception:
        pass
    rail = _rail_solid(rail_w, rail_h + 0.5, _flank_dx, sect_len).translate(
        (0, 0, base_th - 0.5)
    )
    body = plate.union(rail)

    # Accessory face: an upright wall at the -Y back edge, overlapping into the
    # plate, carrying a horizontal 1/4-20 hole.
    face_w = plate_w
    face_h = rail_h + base_th + 8.0
    face = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -sect_len / 2.0 - face_th / 2.0 + 0.5, 0))
        .box(face_w, face_th, face_h, centered=(True, True, False))
    )
    try:
        face = face.edges("|Y").fillet(min(3.0, face_th - 0.5))
    except Exception:
        pass
    body = body.union(face)

    # Horizontal 1/4-20 hole through the face (along Y), drilled from the back
    # face inward, leaving a ~0.8 mm floor → open, vented pocket. Built as a
    # Z-cylinder rotated to lie along Y, then positioned bracketing the back face.
    hr = max(0.5, face_hole_d / 2.0)
    back_y = -sect_len / 2.0 - face_th + 0.5   # rearmost face of the wall
    depth = face_th - 0.8
    hz = face_h * 0.55
    drill = (
        cq.Workplane("XY")
        .circle(hr)
        .extrude(depth + 1.0)                    # cylinder along +Z, length depth+1
        .rotate((0, 0, 0), (1, 0, 0), -90)       # lay it along +Y
        .translate((0, back_y - 1.0, hz))        # start 1 mm behind the back face
    )
    body = body.cut(drill)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "nato_clamp":
    result = build_nato_clamp()
elif target_part == "rail_adapter":
    result = build_rail_adapter()
else:
    result = build_nato_rail_section()
