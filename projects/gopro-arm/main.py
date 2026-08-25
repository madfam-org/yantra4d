"""
GoPro Extension Arm — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Chains GoPro-style action-cam accessories: a finger clevis on each end of a
connecting bar lets you extend, offset or couple mounts in the ubiquitous GoPro
ecosystem. One end carries a 2-prong (female) bank, the other a 3-prong (male)
bank facing the opposite way, so the arm passes a mount through while adding
reach. Every finger set is the real GoPro clevis, so it mates any GoPro mount,
base or accessory.

GoPro finger spec, encoded dimensionally:
  - finger thickness ~3.0 mm, inter-finger gap ~3.2 mm (pitch ~6.2 mm so a 3.0 mm
    finger nests in the opposite prong's gap),
  - knuckle diameter ~15 mm, M5 axle bolt through-hole ~5.0 mm.

Three modes (each geometrically distinct):
  - straight_arm : 2-prong (up) at one end, 3-prong (down) at the other — a plain
                   pass-through extension.
  - coupler      : 2-prong up + 2-prong down on a SHORT bar — couples two male
                   (3-prong) mounts back-to-back.
  - long_arm     : a long straight_arm with two round lightening holes through
                   the bar (vented) — extra reach at lower mass.

Watertight strategy:
  Each finger is a knuckle-cylinder + shaft-box union; the shaft overlaps into
  the arm bar (real material). The far-end bank is rotated 180° about X so its
  knuckles point the other way, then unioned into the bar. Axle holes and
  lightening holes are through-cuts (vent to outside). No tangent unions.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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


# ── Parameters (GoPro finger standard) ───────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "straight_arm"))
# "straight_arm" | "coupler" | "long_arm"

finger_thick = float(PARAM(lambda: finger_thick, 3.0))  # finger thickness (X)
finger_gap = float(PARAM(lambda: finger_gap, 3.2))      # inter-finger gap
knuckle_d = float(PARAM(lambda: knuckle_d, 15.0))       # knuckle diameter
bolt_hole_d = float(PARAM(lambda: bolt_hole_d, 5.0))    # M5 axle through-hole
reach = float(PARAM(lambda: reach, 12.0))               # knuckle pivot height above bar face
arm_len = float(PARAM(lambda: arm_len, 60.0))           # connecting bar length (Y)
arm_th = float(PARAM(lambda: arm_th, 6.0))              # bar thickness (Z)

# Clamp to sane ranges so extreme UI values never crash the kernel.
finger_thick = max(2.0, min(finger_thick, 6.0))
finger_gap = max(2.2, min(finger_gap, 8.0))
knuckle_d = max(9.0, min(knuckle_d, 26.0))
bolt_hole_d = max(3.0, min(bolt_hole_d, 8.0))
reach = max(6.0, min(reach, 30.0))
arm_len = max(30.0, min(arm_len, 160.0))
arm_th = max(4.0, min(arm_th, 12.0))

_knuckle_r = max(1.0, knuckle_d / 2.0)
_bolt_r = min(max(0.5, bolt_hole_d / 2.0), _knuckle_r - 1.2)
_pitch = finger_thick + finger_gap
_shaft_w = knuckle_d * 0.92
_bar_w = knuckle_d * 1.0


# ── GoPro finger primitive (knuckle axis along X, shaft down) ────────────────
def _finger(x_center, base_top_z):
    knuckle = (
        cq.Workplane("YZ")
        .circle(_knuckle_r)
        .extrude(finger_thick / 2.0, both=True)
    )
    shaft_h = reach + 4.0
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -shaft_h / 2.0))
        .box(finger_thick, _shaft_w, shaft_h, centered=(True, True, True))
    )
    finger = knuckle.union(shaft)
    hole = cq.Workplane("YZ").circle(_bolt_r).extrude(finger_thick, both=True)
    finger = finger.cut(hole)
    return finger.translate((x_center, 0, base_top_z + reach))


def _bank(filled, base_top_z):
    span = 2.0 * _pitch
    x0 = -span / 2.0
    bank = None
    for i in filled:
        f = _finger(x0 + i * _pitch, base_top_z)
        bank = f if bank is None else bank.union(f)
    return bank


def _bar(length):
    """Flat connecting bar centred on origin, spanning `length` in Y, `arm_th`
    in Z, `_bar_w` in X."""
    bar = cq.Workplane("XY").box(_bar_w, length, arm_th, centered=(True, True, True))
    try:
        bar = bar.edges("|Z").fillet(min(3.0, _bar_w / 2.0 - 0.5))
    except Exception:
        pass
    return bar


def _add_bank(bar, length, filled_top, y_top, filled_bot, y_bot):
    """Weld a top-facing bank (knuckles up) at y_top and a bottom-facing bank
    (knuckles down) at y_bot to the bar. Either may be None."""
    body = bar
    top_z = arm_th / 2.0
    if filled_top is not None:
        b = _bank(filled_top, top_z).translate((0, y_top, 0))
        body = body.union(b)
    if filled_bot is not None:
        b = _bank(filled_bot, top_z)
        b = b.rotate((0, 0, 0), (1, 0, 0), 180)  # knuckles now point -Z
        b = b.translate((0, y_bot, 0))
        body = body.union(b)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_straight_arm():
    """2-prong (up) at +Y end, 3-prong (down) at -Y end — pass-through extension."""
    y_end = arm_len / 2.0 - knuckle_d * 0.6
    bar = _bar(arm_len)
    return _add_bank(bar, arm_len, [0, 2], y_end, [0, 1, 2], -y_end)


def build_coupler():
    """2-prong up + 2-prong down on a SHORT bar — couples two male mounts."""
    length = max(30.0, min(arm_len * 0.55, 40.0))
    y_end = length / 2.0 - knuckle_d * 0.45
    bar = _bar(length)
    return _add_bank(bar, length, [0, 2], y_end, [0, 2], -y_end)


def build_long_arm():
    """A long straight arm with two round lightening holes through the bar."""
    length = max(arm_len, 90.0)
    y_end = length / 2.0 - knuckle_d * 0.6
    bar = _bar(length)
    body = _add_bank(bar, length, [0, 2], y_end, [0, 1, 2], -y_end)
    # Two lightening holes through the flat of the bar (Z through, vented),
    # placed in the clear middle span away from the knuckle banks.
    hr = min(_bar_w * 0.3, 5.0)
    clear = length / 2.0 - knuckle_d * 1.2
    for y in (-clear * 0.4, clear * 0.4):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, -arm_th))
            .circle(hr)
            .extrude(arm_th * 2.0)
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "coupler":
    result = build_coupler()
elif target_part == "long_arm":
    result = build_long_arm()
else:  # "straight_arm"
    result = build_straight_arm()
