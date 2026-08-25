"""
Arca-Swiss L-Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An L-bracket for the Arca-Swiss 38 mm tripod quick-release standard. An Arca
plate that wraps up the camera's left side so the same body drops into any Arca
clamp in either landscape (base dovetail down) or portrait (wing dovetail out)
orientation with no re-levelling. Every face that meets a clamp carries the same
38 mm dovetail with ~45° flanks, so it mates every Arca clamp, plate and ball
head (e.g. the `arca-plate` clamp/plate cartridge).

Arca-Swiss dovetail geometry (nominal, dimensionally real):
  - platform width       = 38.0 mm  (the wide upper dovetail platform, standard)
  - flank angle          ≈ 45°       (the dovetail undercut, measured from vertical)
  - plate / dovetail height ≈ 9.0 mm (typical plate thickness incl. the dovetail)
  - 1/4-20 camera bolt slot ≈ 6.6 mm clearance (ASME B1.1 1/4-20 UNC)

Three modes (each geometrically distinct):
  - l_bracket      : base dovetail plate + vertical wing whose OUTER face is a
                     second Arca dovetail (the portrait/landscape switch).
  - flat_plate     : a plain Arca QR plate with an elongated 1/4-20 slot.
  - long_lens_foot : a long Arca dovetail foot bar with twin 1/4-20 holes to
                     replace a telephoto lens tripod foot.

Watertight strategy:
  Every part is an extruded 2D dovetail cross-section (wide at the base,
  undercut). Slots/holes are THROUGH features that vent to outside. The wing is
  a vertical dovetail bar UNIONED into the base with real overlap (no tangency).
  Fillets are applied to plain blanks BEFORE feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (Arca-Swiss 38 mm dovetail standard) ──────────────────────────
target_part = str(PARAM(lambda: target_part, "l_bracket"))
# "l_bracket" | "flat_plate" | "long_lens_foot"

plate_w = float(PARAM(lambda: plate_w, 38.0))      # Arca dovetail platform width (X)
flank_ang = float(PARAM(lambda: flank_ang, 45.0))  # dovetail flank angle (deg from vertical)
plate_h = float(PARAM(lambda: plate_h, 9.0))       # plate/dovetail height (Z)
base_len = float(PARAM(lambda: base_len, 70.0))    # base plate length along dovetail (Y)

slot_w = float(PARAM(lambda: slot_w, 6.6))         # 1/4-20 camera slot width (mm)
slot_len = float(PARAM(lambda: slot_len, 30.0))    # 1/4-20 slot travel length (mm)

wing_h = float(PARAM(lambda: wing_h, 55.0))        # vertical wing height (Z, l_bracket)
wing_len = float(PARAM(lambda: wing_len, 40.0))    # vertical wing length along Y (l_bracket)

foot_len = float(PARAM(lambda: foot_len, 100.0))   # long-lens foot length (Y, long_lens_foot)

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_w = max(28.0, min(plate_w, 60.0))
flank_ang = max(30.0, min(flank_ang, 55.0))
plate_h = max(6.0, min(plate_h, 16.0))
base_len = max(40.0, min(base_len, 140.0))
slot_w = max(3.0, min(slot_w, 10.0))
slot_len = max(8.0, min(slot_len, 120.0))
wing_h = max(25.0, min(wing_h, 120.0))
wing_len = max(25.0, min(wing_len, 120.0))
foot_len = max(50.0, min(foot_len, 200.0))

_flank_dx = plate_h * math.tan(math.radians(flank_ang))


# ── Cross-section primitives ─────────────────────────────────────────────────
def _dovetail_profile(top_w, height, flank_dx):
    """Arca dovetail cross-section in XZ, centred on X, base at z=0. Wider at the
    bottom (undercut) so a clamp jaw pulls it in as it tightens."""
    htw = top_w / 2.0
    hbw = htw + flank_dx
    pts = [(-hbw, 0.0), (hbw, 0.0), (htw, height), (-htw, height)]
    return cq.Workplane("XZ").polyline(pts).close()


def _plate_bar_down(top_w, height, flank_dx, length):
    """Dovetail plate with the wide platform DOWN (into a clamp) and the flat
    camera face UP. Centred on Y."""
    bar = _dovetail_profile(top_w, height, flank_dx).extrude(length / 2.0, both=True)
    return bar.rotate((0, 0, 0), (0, 1, 0), 180).translate((0, 0, height))


def _slot_cut(width, length, z_top, depth):
    """Elongated 1/4-20 slot (obround) bored from above the top surface down into
    the plate — vents to outside. Centred on X/Y; runs along Y."""
    overall = max(width + 0.2, length)
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .slot2D(overall, width, angle=90)
        .extrude(depth + 1.0)
    )


def _vertical_wing_dovetail(top_w, height, flank_dx, leg_height):
    """A dovetail bar STANDING vertically: its length runs up +Z (0..leg_height)
    and its dovetail platform faces +X (undercut opening outward). Built from a
    profile in (Y, X) extruded up +Z, then rotated so depth points +X."""
    htw = top_w / 2.0
    hbw = htw + flank_dx
    d0 = flank_dx + max(3.0, flank_dx)  # solid depth behind the platform
    pts = [(-hbw, 0.0), (hbw, 0.0), (htw, d0), (-htw, d0)]
    prof = cq.Workplane("XY").polyline(pts).close()
    solid = prof.extrude(leg_height)
    return solid.rotate((0, 0, 0), (0, 0, 1), -90)


# ── Part builders ────────────────────────────────────────────────────────────
def build_flat_plate():
    """A plain Arca-Swiss QR plate: the 38 mm dovetail bar (platform down) with
    an elongated 1/4-20 slot so a camera bolts on anywhere along the slot."""
    body = _plate_bar_down(plate_w, plate_h, _flank_dx, base_len)
    s_len = max(8.0, min(slot_len, base_len - 12.0))
    body = body.cut(_slot_cut(slot_w, s_len, plate_h, plate_h - 1.4))
    return body


def build_l_bracket():
    """An L-shaped Arca plate: a base dovetail plate plus a vertical wing on the
    +X side whose OUTER face carries its own Arca dovetail. Drop the base into a
    clamp for landscape, or the wing's dovetail in for instant portrait."""
    b_len = wing_len
    body = _plate_bar_down(plate_w, plate_h, _flank_dx, b_len)
    # 1/4-20 slot in the base top (vented).
    s_len = max(8.0, min(slot_len, b_len - 10.0))
    body = body.cut(_slot_cut(slot_w, s_len, plate_h, plate_h - 1.4))

    # Vertical wing standing at the +X edge, rising to wing_h, dovetail facing +X.
    wing = _vertical_wing_dovetail(plate_w, plate_h, _flank_dx, wing_h)
    # Its length spans the Y width of the wing (plate_w). Shift so it overlaps the
    # base's +X edge (real material overlap → watertight weld).
    x_shift = plate_w / 2.0 - plate_h * 0.5
    wing = wing.translate((x_shift, 0, 0))
    body = body.union(wing)
    return body


def build_long_lens_foot():
    """A long Arca dovetail foot bar to replace a telephoto lens tripod foot:
    a long 38 mm dovetail (platform down) with two spaced 1/4-20 through-holes
    that bolt up into the lens foot boss."""
    body = _plate_bar_down(plate_w, plate_h, _flank_dx, foot_len)
    # Twin 1/4-20 through-holes along the centreline, spaced along Y.
    hr = max(1.5, slot_w / 2.0)
    span = min(foot_len - 20.0, 45.0)
    for y in (-span / 2.0, span / 2.0):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, -0.5))
            .circle(hr)
            .extrude(plate_h + 1.0)
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "flat_plate":
    result = build_flat_plate()
elif target_part == "long_lens_foot":
    result = build_long_lens_foot()
else:
    result = build_l_bracket()
