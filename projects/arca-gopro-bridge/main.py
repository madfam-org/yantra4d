"""
Arca-to-GoPro Adapter Bridge — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A cross-family hub that bridges the tripod world (Arca-Swiss 38 mm dovetail) and
the action-cam world (GoPro finger clevis). One face is a 38 mm Arca dovetail
(platform down) that drops into any Arca clamp; the other face is a GoPro finger
bank (2-prong female or 3-prong male) that mates any GoPro accessory. So an Arca
tripod head can carry a GoPro chain, or a GoPro cage can bolt to an Arca plate.

Two real standards, encoded dimensionally:
  Arca-Swiss dovetail — platform width 38.0 mm, flank angle ~45° from vertical,
    height ~9.0 mm; bottom width = width + 2·height·tan(flank).
  GoPro finger clevis — finger thickness ~3.0 mm, gap ~3.2 mm (pitch ~6.2 mm so a
    3.0 mm finger nests in the opposite prong's gap), knuckle diameter ~15 mm,
    M5 axle bolt through-hole ~5.0 mm.

Three modes (each geometrically distinct):
  - arca_to_gopro   : Arca dovetail plate + GoPro 2-prong (female) fingers up.
  - gopro_to_arca   : Arca dovetail plate + GoPro 3-prong (male) fingers up.
  - arca_gopro_flat : a compact filleted puck with GoPro 3-prong fingers up and a
                      short Arca dovetail underneath (a low-profile bridge).

Watertight strategy:
  The Arca base is an extruded dovetail cross-section (platform down). GoPro
  fingers are knuckle-cylinder + shaft-box unions whose shafts overlap DOWN into
  the base top (real material overlap → single watertight body). The axle hole is
  a through-hole along X (vents to outside). Fillets are on plain blanks only.

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


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "arca_to_gopro"))
# "arca_to_gopro" | "gopro_to_arca" | "arca_gopro_flat"

# Arca-Swiss dovetail
plate_w = float(PARAM(lambda: plate_w, 38.0))      # dovetail platform width (X)
flank_ang = float(PARAM(lambda: flank_ang, 45.0))  # dovetail flank angle (deg from vertical)
plate_h = float(PARAM(lambda: plate_h, 9.0))       # dovetail height (Z)
plate_len = float(PARAM(lambda: plate_len, 46.0))  # Arca plate length along Y

# GoPro finger clevis
finger_thick = float(PARAM(lambda: finger_thick, 3.0))  # finger thickness (X)
finger_gap = float(PARAM(lambda: finger_gap, 3.2))      # inter-finger gap (mating clearance)
knuckle_d = float(PARAM(lambda: knuckle_d, 15.0))       # knuckle diameter
bolt_hole_d = float(PARAM(lambda: bolt_hole_d, 5.0))    # M5 axle through-hole
reach = float(PARAM(lambda: reach, 16.0))               # knuckle-centre height above base top

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_w = max(28.0, min(plate_w, 60.0))
flank_ang = max(30.0, min(flank_ang, 55.0))
plate_h = max(6.0, min(plate_h, 16.0))
plate_len = max(36.0, min(plate_len, 90.0))
finger_thick = max(2.0, min(finger_thick, 6.0))
finger_gap = max(2.2, min(finger_gap, 8.0))
knuckle_d = max(9.0, min(knuckle_d, 26.0))
bolt_hole_d = max(3.0, min(bolt_hole_d, 8.0))
reach = max(8.0, min(reach, 40.0))

_flank_dx = plate_h * math.tan(math.radians(flank_ang))
_knuckle_r = max(1.0, knuckle_d / 2.0)
_bolt_r = min(max(0.5, bolt_hole_d / 2.0), _knuckle_r - 1.2)
_pitch = finger_thick + finger_gap
_shaft_w = knuckle_d * 0.92


# ── Arca dovetail base (platform down, flat top up) ──────────────────────────
def _dovetail_bar_down(top_w, height, flank_dx, length):
    htw = top_w / 2.0
    hbw = htw + flank_dx
    prof = cq.Workplane("XZ").polyline(
        [(-hbw, 0.0), (hbw, 0.0), (htw, height), (-htw, height)]
    ).close()
    bar = prof.extrude(length / 2.0, both=True)
    return bar.rotate((0, 0, 0), (0, 1, 0), 180).translate((0, 0, height))


# ── GoPro finger primitive (knuckle axis along X, shaft down) ────────────────
def _finger(x_center, base_top_z):
    """One GoPro finger: rounded knuckle (X-axis cylinder) at Z = base_top_z +
    reach, joined by a shaft that overlaps DOWN into the base top. Axle hole
    along X (through, vented)."""
    knuckle = (
        cq.Workplane("YZ")
        .circle(_knuckle_r)
        .extrude(finger_thick / 2.0, both=True)
    )
    shaft_h = reach + 4.0  # from pivot down to 4 mm below the base top (overlap)
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -shaft_h / 2.0))
        .box(finger_thick, _shaft_w, shaft_h, centered=(True, True, True))
    )
    finger = knuckle.union(shaft)
    hole = cq.Workplane("YZ").circle(_bolt_r).extrude(finger_thick, both=True)
    finger = finger.cut(hole)
    return finger.translate((x_center, 0, base_top_z + reach))


def _finger_bank(filled, base_top_z):
    """Union fingers on a 3-slot pitch grid centred on X=0; `filled` = slot idx."""
    span = 2.0 * _pitch
    x0 = -span / 2.0
    bank = None
    for i in filled:
        f = _finger(x0 + i * _pitch, base_top_z)
        bank = f if bank is None else bank.union(f)
    return bank


# ── Part builders ────────────────────────────────────────────────────────────
def build_bridge(prongs):
    """Arca dovetail plate (platform down) with a GoPro finger bank rising from
    the flat top. prongs='dual' → 2-prong female; 'triple' → 3-prong male."""
    base = _dovetail_bar_down(plate_w, plate_h, _flank_dx, plate_len)
    filled = [0, 2] if prongs == "dual" else [0, 1, 2]
    bank = _finger_bank(filled, plate_h)
    return base.union(bank)


def build_flat():
    """A compact low-profile bridge: a filleted rectangular puck carrying GoPro
    3-prong fingers on top, with a short Arca dovetail on the underside so it
    still drops into a clamp but sits lower than the full plate."""
    # Short dovetail base (platform down).
    short_len = max(30.0, min(plate_len * 0.7, 40.0))
    base = _dovetail_bar_down(plate_w, plate_h, _flank_dx, short_len)
    # A thin stiffening puck fused over the flat top to spread the finger loads,
    # sized to the finger X-span; unioned with overlap into the top.
    x_half = _pitch + finger_thick / 2.0
    puck_x = 2.0 * (x_half + 3.0)
    puck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_h - 0.5))
        .box(puck_x, short_len * 0.8, 2.5, centered=(True, True, False))
    )
    try:
        puck = puck.edges("|Z").fillet(2.0)
    except Exception:
        pass
    base = base.union(puck)
    bank = _finger_bank([0, 1, 2], plate_h + 2.0)
    return base.union(bank)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "gopro_to_arca":
    result = build_bridge("triple")
elif target_part == "arca_gopro_flat":
    result = build_flat()
else:  # "arca_to_gopro"
    result = build_bridge("dual")
