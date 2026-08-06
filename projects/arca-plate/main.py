"""
Arca-Swiss QR Plate & Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The Arca-Swiss tripod quick-release standard — a 38 mm dovetail with ~45° flanks
that most ball heads, L-brackets and plates share. This cartridge builds an Arca
QR plate with a 1/4-20 camera slot, a clamp jaw that grips the 38 mm dovetail,
and an L-bracket (an Arca plate that wraps up the camera side for instant
portrait mounting).

Arca-Swiss dovetail geometry (nominal, dimensionally real):
  - plate width         = 38.0 mm  (the wide upper platform, Arca standard)
  - flank angle         ≈ 45°       (the dovetail undercut from vertical)
  - plate/dovetail height ≈ 9.0 mm  (typical plate thickness incl. dovetail)
  - the clamp jaw flanks match 45° so tightening pulls the plate into the jaw.

Watertight strategy:
  Plate, clamp jaws and L-bracket are extruded 2D dovetail cross-sections.
  The camera slot is a through-slot along the plate (open both ends → vents to
  outside). The clamp channel is a through-channel. The 1/4-20 slot is an
  elongated through-hole in the plate; the clamp bolt is a through-hole. Every
  union overlaps into shared material; fillets are applied to clean blanks
  BEFORE feature cuts, wrapped in try/except.

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


# ── Parameters (Arca-Swiss 38 mm dovetail standard) ──────────────────────────
target_part = str(PARAM(lambda: target_part, "qr_plate"))
# "qr_plate" | "arca_clamp" | "l_bracket"

plate_w = float(PARAM(lambda: plate_w, 38.0))       # Arca dovetail platform width (X)
flank_ang = float(PARAM(lambda: flank_ang, 45.0))   # dovetail flank angle (deg from vertical)
plate_h = float(PARAM(lambda: plate_h, 9.0))        # plate/dovetail height (Z)
plate_len = float(PARAM(lambda: plate_len, 60.0))   # plate length (Y)

slot_w = float(PARAM(lambda: slot_w, 6.6))          # 1/4-20 camera slot width (mm)
slot_len = float(PARAM(lambda: slot_len, 24.0))     # slot travel length (mm)

clamp_clear = float(PARAM(lambda: clamp_clear, 0.35))   # clamp-to-plate fit slop (per side)
wall = float(PARAM(lambda: wall, 5.0))              # clamp wall / jaw thickness (mm)
clamp_bolt_d = float(PARAM(lambda: clamp_bolt_d, 5.2))  # clamp bolt clearance (M5)

leg_h = float(PARAM(lambda: leg_h, 55.0))           # L-bracket vertical leg height (mm)
leg_len = float(PARAM(lambda: leg_len, 40.0))       # L-bracket vertical leg length (Y)

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_w = max(28.0, min(plate_w, 60.0))
flank_ang = max(30.0, min(flank_ang, 55.0))
plate_h = max(5.0, min(plate_h, 16.0))
plate_len = max(30.0, min(plate_len, 140.0))
slot_w = max(3.0, min(slot_w, 10.0))
slot_len = max(8.0, min(slot_len, plate_len - 12.0))
clamp_clear = max(0.1, min(clamp_clear, 0.8))
wall = max(3.0, min(wall, 12.0))
clamp_bolt_d = max(2.5, min(clamp_bolt_d, 8.0))
leg_h = max(20.0, min(leg_h, 120.0))
leg_len = max(20.0, min(leg_len, 120.0))

_flank_dx = plate_h * math.tan(math.radians(flank_ang))
plate_bot_w = plate_w + 2.0 * _flank_dx


# ── Cross-section primitives ─────────────────────────────────────────────────
def _dovetail_profile(top_w, height, flank_dx, extra_bottom=0.0):
    """The Arca dovetail cross-section in XZ, centred on X, base at z=0. Wider at
    the bottom (undercut). `extra_bottom` grows the very bottom for clamp cuts."""
    htw = top_w / 2.0
    hbw = htw + flank_dx + extra_bottom
    pts = [
        (-hbw, 0.0),
        (hbw, 0.0),
        (htw, height),
        (-htw, height),
    ]
    return cq.Workplane("XZ").polyline(pts).close()


def _plate_bar(top_w, height, flank_dx, length):
    """The dovetail plate, centred on Y (spans -length/2 .. +length/2)."""
    return _dovetail_profile(top_w, height, flank_dx).extrude(length / 2.0, both=True)


def _slot_cut(width, length, z_top, depth):
    """An elongated 1/4-20 slot: a rounded rectangle (slot2D) bored down from
    above the top surface (vents to outside). Centred on X/Y; runs along Y."""
    overall = max(width + 0.1, length)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .slot2D(overall, width, angle=90)
        .extrude(depth + 1.0)
    )
    return slot


# ── Part builders ────────────────────────────────────────────────────────────
def build_qr_plate():
    """An Arca-Swiss QR plate: the 38 mm dovetail bar with an elongated 1/4-20
    slot so a camera bolts on anywhere along the slot. The dovetail faces DOWN
    (into a clamp); the camera mounts on the flat top."""
    # Build the dovetail, then flip so the wide platform is DOWN and the flat
    # top faces up for the camera. After flipping, the flat (camera) face is up.
    bar = _plate_bar(plate_w, plate_h, _flank_dx, plate_len)
    bar = bar.rotate((0, 0, 0), (0, 1, 0), 180).translate((0, 0, plate_h))
    # Now: flat top at z=plate_h (camera side, width = plate_w), dovetail flanks
    # opening downward to the wide base at z=0 (bottom width = plate_bot_w).

    # 1/4-20 camera slot through the flat top, down into the plate (vented).
    slot = _slot_cut(slot_w, slot_len, plate_h, plate_h - 1.2)
    body = bar.cut(slot)

    # Safety end-stops: small ridges are not needed; keep the plate clean.
    return body


def build_arca_clamp():
    """A clamp jaw block that grips the 38 mm Arca dovetail: a body with a
    matching dovetail channel (grown by clearance), a flex slit, and a cross
    bolt. A 1/4-20 hole underneath mounts the clamp to a head or plate."""
    ch_top_w = plate_w + 2.0 * clamp_clear
    ch_h = plate_h + clamp_clear
    ch_flank_dx = ch_h * math.tan(math.radians(flank_ang))
    ch_bot_w = ch_top_w + 2.0 * ch_flank_dx

    body_w = ch_bot_w + 2.0 * wall
    body_h = ch_h + wall + 2.0
    body_len = min(plate_len, 32.0)

    block = (
        cq.Workplane("XY")
        .box(body_w, body_len, body_h, centered=(True, True, False))
    )
    try:
        block = block.edges("|Z").fillet(min(2.5, wall - 0.5))
    except Exception:
        pass

    # Dovetail channel opening UPWARD (the plate drops in from the top), cut
    # through both Y ends (open → vents to outside). The channel is the plate
    # dovetail oriented flat-down: wide at top of channel? No — the plate sits
    # dovetail-DOWN, so the channel must be wide at BOTTOM to capture it. Cut a
    # dovetail whose wide part is UP (mouth) narrowing down is wrong; instead
    # the clamp captures the plate's downward-opening flanks, so the channel is
    # an upward-opening dovetail: narrow mouth at top, wider below.
    chan = (
        _dovetail_profile(ch_top_w, ch_h, ch_flank_dx, extra_bottom=0.0)
        .extrude((body_len + 2.0) / 2.0, both=True)
        .translate((0, 0, -0.01))
    )
    body = block.cut(chan)

    # Flex slit on one side reaching from the channel up toward the top.
    slit = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(body_w / 2.0 - wall * 0.5, 0, ch_h))
        .box(1.8, body_len + 2.0, body_h, centered=(True, True, False))
    )
    body = body.cut(slit)

    # Clamp bolt across X, above the channel through the flex jaw.
    bolt_z = ch_h + (body_h - ch_h) * 0.5
    bolt = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, bolt_z, 0))
        .circle(max(0.5, clamp_bolt_d / 2.0))
        .extrude(body_w / 2.0 + 1.0, both=True)
    )
    body = body.cut(bolt)

    # 1/4-20 hole up from the underside (mount the clamp to a head), vented.
    hr = max(0.5, slot_w / 2.0)
    depth = max(2.5, min(wall + 1.5, body_h - ch_h - 1.0, body_h - 1.0))
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .circle(hr)
        .extrude(depth + 0.01)
    )
    body = body.cut(hole)
    return body


def _vertical_leg_dovetail(top_w, height, flank_dx, leg_height):
    """A dovetail bar STANDING vertically: its length runs up +Z (0 .. leg_height)
    and its dovetail platform faces +X (platform at large X, wider toward small
    X — the undercut opens outward). Built from a YZ-plane cross-section so the
    orientation is unambiguous.

    Cross-section in the YZ plane (mapped: profile-x -> world Y, profile-y ->
    world Z is NOT what we want); instead we place the dovetail outline in the
    plane spanning world Y (platform width) and world X (dovetail depth), then
    extrude up world +Z."""
    htw = top_w / 2.0
    hbw = htw + flank_dx
    # Outline in (Y, X): platform spans Y in [-htw, htw] at outer X = depth d0;
    # undercut widens toward inner X = 0. Draw on the XY plane then extrude +Z.
    d0 = flank_dx + max(2.0, flank_dx)  # solid depth behind the platform
    pts = [
        (-hbw, 0.0),        # inner base, wide
        (hbw, 0.0),
        (htw, d0),          # platform edge at depth d0
        (-htw, d0),
    ]
    # Here profile x = world Y (width), profile y = world X (depth). Build on the
    # XY plane as (Y, X) then swap by rotating so depth points +X.
    prof = cq.Workplane("XY").polyline(pts).close()
    solid = prof.extrude(leg_height)          # extrude up +Z
    # Currently: platform-width along world-X, depth along world-Y, height +Z.
    # Rotate -90° about Z so width -> world-Y and depth -> world +X.
    solid = solid.rotate((0, 0, 0), (0, 0, 1), -90)
    return solid


def build_l_bracket():
    """An L-shaped Arca plate: a base plate (dovetail down, 1/4-20 slot) plus a
    vertical leg rising on the +X side whose OUTER face carries its own Arca
    dovetail — drop the base into a clamp for landscape, or drop the leg's
    dovetail in for instant portrait with no re-levelling."""
    # Base plate (dovetail down, flat top up) — like the QR plate but shorter.
    base_len = leg_len
    bar = _plate_bar(plate_w, plate_h, _flank_dx, base_len)
    bar = bar.rotate((0, 0, 0), (0, 1, 0), 180).translate((0, 0, plate_h))
    body = bar

    # 1/4-20 slot in the base top (vented).
    s_len = max(8.0, min(slot_len, base_len - 10.0))
    slot = _slot_cut(slot_w, s_len, plate_h, plate_h - 1.2)
    body = body.cut(slot)

    # Vertical leg standing at the +X edge, rising from the base up to leg_h,
    # dovetail facing +X. Overlap it into the base so the weld is solid.
    leg = _vertical_leg_dovetail(plate_w, plate_h, _flank_dx, leg_h)
    # Its dovetail depth extends toward +X from x=0; shift so its inner face sits
    # near the base's +X edge and it overlaps the base top region.
    x_shift = plate_w / 2.0 - plate_h * 0.6
    leg = leg.translate((x_shift, 0, 0))
    body = body.union(leg)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "arca_clamp":
    result = build_arca_clamp()
elif target_part == "l_bracket":
    result = build_l_bracket()
else:
    result = build_qr_plate()
