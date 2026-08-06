"""
Robot Wheel / Hub — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A drive wheel or hub with a shaft bore matched to a real motor shaft: a 3 mm or
4 mm D-shaft (round with one flat), a 6 mm round shaft (round bore + a set-screw),
or the double-flat TT gearmotor shaft (modelled as a hex bore adapter). Pick the
shaft; the bore geometry follows so the wheel keys to the shaft and drives it.

Modes (dispatched via `target_part`):
  * "wheel"        — a drive wheel: a rim built as stacked cylinders so a narrower
                     mid-band forms a tyre groove between two flanges, with the
                     keyed shaft bore up the centre.
  * "hub_adapter"  — a shaft-to-bolt-circle hub: the keyed bore on the shaft side,
                     a flat flange with a ring of bolt holes on the other, to bolt
                     a wheel, disc or arm to the motor.
  * "pulley_wheel" — a flanged pulley: a deep central V-groove (cord / round belt)
                     between two rim flanges, with the same keyed bore.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shaft`).
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


# ── Shaft table ──────────────────────────────────────────────────────────────
# kind: bore style; dia: nominal shaft dia (mm); flat: D-flat depth from the round
# (mm), i.e. how far the flat cuts in; af: hex across-flats for the TT adapter.
SHAFT_TABLE = {
    "3mm-D":       {"kind": "d",     "dia": 3.0, "flat": 0.5},
    "4mm-D":       {"kind": "d",     "dia": 4.0, "flat": 0.5},
    "6mm-round":   {"kind": "round", "dia": 6.0, "flat": 0.0},
    "hex-TT-motor":{"kind": "hex",   "dia": 5.4, "flat": 0.0, "af": 5.4},
}


def shaft_spec(key):
    """Case-insensitive lookup against the shaft table (keys carry mixed case)."""
    k = str(key).strip().lower().replace(" ", "")
    for name, spec in SHAFT_TABLE.items():
        if name.lower() == k:
            return spec
    return SHAFT_TABLE["3mm-D"]


# ── Parameters ───────────────────────────────────────────────────────────────
shaft       = str(  PARAM(lambda: shaft,      "3mm-D"))  # 3mm-D|4mm-D|6mm-round|hex-TT-motor
wheel_d     = float(PARAM(lambda: wheel_d,      60.0))   # wheel outer diameter
wheel_w     = float(PARAM(lambda: wheel_w,      12.0))   # wheel width (Z)
groove_d    = float(PARAM(lambda: groove_d,      3.0))   # tyre-groove depth (radial)
hub_d       = float(PARAM(lambda: hub_d,        16.0))   # central hub / boss diameter
bore_clear  = float(PARAM(lambda: bore_clear,    0.2))   # bore clearance over the shaft (fit)
bolt_circle = float(PARAM(lambda: bolt_circle,  24.0))   # adapter bolt-circle diameter
bolt_d      = float(PARAM(lambda: bolt_d,        3.4))   # adapter bolt-hole dia (M3)
bolt_n      = int(  PARAM(lambda: bolt_n,          4))   # adapter bolt count
set_d       = float(PARAM(lambda: set_d,         3.0))   # set-screw dia (round shaft)

target_part = str(  PARAM(lambda: target_part, "wheel"))
# "wheel" | "hub_adapter" | "pulley_wheel"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = shaft_spec(shaft)
shaft_kind = spec["kind"]
shaft_dia = spec["dia"]
bore_clear = max(0.0, min(bore_clear, 0.6))
bore_r = shaft_dia / 2.0 + bore_clear
wheel_d = max(hub_d + 8.0, wheel_d)
wheel_r = wheel_d / 2.0
wheel_w = max(6.0, wheel_w)
hub_r = max(bore_r + 2.0, hub_d / 2.0)
groove_d = max(0.5, min(groove_d, wheel_r - hub_r - 2.0))
bolt_r = max(1.2, bolt_d / 2.0)
bolt_n = max(2, min(int(bolt_n), 12))
set_r = max(0.8, set_d / 2.0)


# ── Keyed shaft bore ─────────────────────────────────────────────────────────
def _shaft_bore(height):
    """The negative of the shaft, from z=−1 up through `height`+1. D-shaft = a
    round bore with a chord flat; round = plain round bore; hex = a hexagonal bore
    (TT gearmotor adapter). Centred on the origin."""
    h = height + 2.0
    if shaft_kind == "hex":
        af = spec.get("af", shaft_dia) + 2.0 * bore_clear    # across flats
        rr = af / math.sqrt(3.0)                              # circumradius
        pts = []
        for i in range(6):
            a = math.radians(60.0 * i + 30.0)
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        cutter = cq.Workplane("XY").polyline(pts).close().extrude(h)
        return cutter.translate((0, 0, -1.0))
    # round base bore
    cutter = cq.Workplane("XY").circle(bore_r).extrude(h)
    if shaft_kind == "d":
        # Chop a flat off one side: subtract a box covering the +X chord.
        flat = spec.get("flat", 0.5) + bore_clear
        chord_x = bore_r - flat
        box = (
            cq.Workplane("XY")
            .box(bore_r * 2.0, bore_r * 2.0, h, centered=(True, True, False))
            .translate((chord_x + bore_r, 0, 0))   # sits beyond the chord line
        )
        cutter = cutter.cut(box)
    return cutter.translate((0, 0, -1.0))


def _apply_bore(body, height):
    body = body.cut(_shaft_bore(height))
    # Round shafts get a radial set-screw into the hub to lock onto the shaft.
    if shaft_kind == "round":
        setscrew = (
            cq.Workplane("YZ")
            .workplane(offset=0.0)
            .circle(set_r)
            .extrude(hub_r + 1.0)
            .translate((0, 0, height * 0.5))
        )
        body = body.cut(setscrew)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_wheel():
    """A drive wheel: two rim flanges with a narrower tyre-groove band between
    them (stacked cylinders → watertight by construction), a central hub, and the
    keyed bore. A ring of lightening holes reduces mass."""
    flange_w = max(2.0, wheel_w * 0.22)
    band_w = wheel_w - 2.0 * flange_w
    band_r = wheel_r - groove_d

    # Bottom flange, mid band, top flange as coaxial stacked cylinders.
    body = cq.Workplane("XY").circle(wheel_r).extrude(flange_w)
    body = body.union(
        cq.Workplane("XY").circle(band_r).extrude(band_w).translate((0, 0, flange_w))
    )
    body = body.union(
        cq.Workplane("XY").circle(wheel_r).extrude(flange_w)
        .translate((0, 0, flange_w + band_w))
    )
    # Central hub boss (rises through the wheel; overlaps every layer).
    body = body.union(cq.Workplane("XY").circle(hub_r).extrude(wheel_w))

    # Lightening holes on a mid radius (grouped pushPoints).
    lr = (hub_r + band_r) / 2.0
    if lr > hub_r + 3.0:
        hole_r = min(3.0, (band_r - hub_r) / 4.0)
        if hole_r > 0.8:
            n = 6
            pts = [(lr * math.cos(math.radians(60.0 * i)),
                    lr * math.sin(math.radians(60.0 * i))) for i in range(n)]
            cutter = (
                cq.Workplane("XY").pushPoints(pts).circle(hole_r)
                .extrude(wheel_w + 2.0).translate((0, 0, -1.0))
            )
            body = body.cut(cutter)

    body = _apply_bore(body, wheel_w)
    return body


def build_hub_adapter():
    """A shaft-to-bolt-circle hub: a keyed boss on the shaft side and a flat flange
    with a ring of bolt holes to carry a wheel/disc/arm."""
    boss_h = max(8.0, wheel_w * 0.6)
    flange_t = max(3.0, wheel_w * 0.35)
    flange_r = max(bolt_circle / 2.0 + bolt_r + 3.0, hub_r + 4.0)
    total_h = flange_t + boss_h

    # Flange disc (clean blank), then boss, then bolt ring, then keyed bore.
    body = cq.Workplane("XY").circle(flange_r).extrude(flange_t)
    body = body.union(
        cq.Workplane("XY").circle(hub_r).extrude(total_h)   # boss overlaps flange
    )
    # Bolt circle.
    bc_r = bolt_circle / 2.0
    pts = [(bc_r * math.cos(2.0 * math.pi * i / bolt_n),
            bc_r * math.sin(2.0 * math.pi * i / bolt_n)) for i in range(bolt_n)]
    cutter = (
        cq.Workplane("XY").pushPoints(pts).circle(bolt_r)
        .extrude(flange_t + 2.0).translate((0, 0, -1.0))
    )
    body = body.cut(cutter)
    body = _apply_bore(body, total_h)
    return body


def build_pulley_wheel():
    """A flanged pulley: two rim flanges with a deep V-groove between them for a
    cord or round belt, plus the keyed bore. The V-profile is built directly from
    two tapered frusta (no boolean groove-cut), so it is watertight by
    construction — the outer surface tapers in to the groove root and back out."""
    flange_w = max(2.0, wheel_w * 0.25)
    band_w = wheel_w - 2.0 * flange_w
    half = band_w / 2.0
    v_depth = min(groove_d + 1.5, wheel_r - hub_r - 2.0)
    root_r = max(hub_r + 1.5, wheel_r - v_depth)

    z0 = 0.0
    # Bottom flange (full rim radius).
    body = cq.Workplane("XY").circle(wheel_r).extrude(flange_w)
    z0 += flange_w
    # Lower frustum: rim radius → groove root (tapers inward going up).
    lower = (
        cq.Workplane("XY")
        .circle(wheel_r)
        .workplane(offset=half)
        .circle(root_r)
        .loft(combine=True)
        .translate((0, 0, z0))
    )
    body = body.union(lower)
    z0 += half
    # Upper frustum: groove root → rim radius (tapers back out going up).
    upper = (
        cq.Workplane("XY")
        .circle(root_r)
        .workplane(offset=half)
        .circle(wheel_r)
        .loft(combine=True)
        .translate((0, 0, z0))
    )
    body = body.union(upper)
    z0 += half
    # Top flange.
    body = body.union(
        cq.Workplane("XY").circle(wheel_r).extrude(flange_w).translate((0, 0, z0))
    )
    # Central hub boss spanning the full width (overlaps every layer).
    body = body.union(cq.Workplane("XY").circle(hub_r).extrude(wheel_w))

    body = _apply_bore(body, wheel_w)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hub_adapter":
    result = build_hub_adapter()
elif target_part == "pulley_wheel":
    result = build_pulley_wheel()
else:  # "wheel"
    result = build_wheel()
