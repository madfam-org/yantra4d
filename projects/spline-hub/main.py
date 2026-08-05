"""
Keyed / Spline Hub Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hub with an internal torque-transmitting bore that couples a printed part to a
motor shaft, gearbox output, or actuator. Three bore types:

  * "keyway"          — a round bore plus a rectangular key slot (a parallel key
                        transmits the torque; the standard machine-element coupling).
  * "involute_spline" — a splined bore with N teeth around the circumference; the
                        many flanks share the load (an APPROXIMATE toothed bore,
                        dimensionally keyed to the shaft diameter and tooth count —
                        not a precision DIN 5480 flank form).
  * "hex"             — a hexagonal bore for hex shafts / hex drivers.

Optional outer mounting flange with a bolt-hole circle so the hub also bolts to a
plate (e.g. a pulley or arm face).

Three parts (dispatched via `target_part`): "keyed_hub", "spline_hub", "hex_hub"
(each forces the matching `bore_type`).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shaft_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "keyed_hub"))  # keyed_hub|spline_hub|hex_hub
if target_part not in ("keyed_hub", "spline_hub", "hex_hub"):
    target_part = "keyed_hub"

bore_type = str(PARAM(lambda: bore_type, "keyway"))  # keyway|involute_spline|hex
# target_part forces the matching bore type so the three parts are distinct.
if target_part == "keyed_hub":
    bore_type = "keyway"
elif target_part == "spline_hub":
    bore_type = "involute_spline"
elif target_part == "hex_hub":
    bore_type = "hex"
if bore_type not in ("keyway", "involute_spline", "hex"):
    bore_type = "keyway"

shaft_dia = float(PARAM(lambda: shaft_dia, 8.0))       # nominal shaft diameter / bore
clearance = float(PARAM(lambda: clearance, 0.2))       # printed fit gap on the bore
spline_teeth = int(PARAM(lambda: spline_teeth, 6))     # involute_spline tooth count
key_width = float(PARAM(lambda: key_width, 3.0))       # keyway: key slot width
key_depth = float(PARAM(lambda: key_depth, 1.8))       # keyway: slot depth into the hub wall
hub_od = float(PARAM(lambda: hub_od, 0.0))             # 0 → auto (2.2× shaft)
length = float(PARAM(lambda: length, 16.0))            # hub length (axial)
flange = bool(PARAM(lambda: flange, False))            # add an outer mounting flange
flange_bolts = int(PARAM(lambda: flange_bolts, 4))     # bolt holes in the flange
flange_bolt_dia = float(PARAM(lambda: flange_bolt_dia, 4.5))  # bolt-hole diameter

# Clamp to safe, watertight ranges.
shaft_dia = max(3.0, shaft_dia)
clearance = max(0.0, min(clearance, 1.0))
spline_teeth = max(4, min(spline_teeth, 24))
length = max(5.0, length)
flange_bolts = max(2, min(flange_bolts, 12))
key_width = max(1.0, min(key_width, shaft_dia * 0.6))
key_depth = max(0.5, min(key_depth, shaft_dia * 0.4))

bore_r = (shaft_dia + clearance) / 2.0

# Auto hub OD: enough wall to carry torque without splitting.
if hub_od <= 0.1:
    hub_od = shaft_dia * 2.2 + 4.0
hub_od = max(shaft_dia + 5.0, hub_od)
hub_r = hub_od / 2.0


# ── Bore cutters (each a solid extruded the full hub length + overshoot) ──────
def keyway_cutter():
    """Round bore + a rectangular key slot projecting outward from the bore wall."""
    cut_len = length + 2.0
    bore = cq.Workplane("XY").circle(bore_r).extrude(cut_len)
    # Key slot: a rectangle whose inner edge starts inside the bore and extends
    # out by key_depth past the bore radius. Centred on +X.
    slot_w = key_width + clearance
    slot_len = bore_r + key_depth + 1.0   # from bore centre outward past the wall
    slot = (
        cq.Workplane("XY")
        .box(slot_len, slot_w, cut_len, centered=(False, True, False))
    )
    # box with centered X=False grows +X from x=0; shift so it overlaps the bore.
    slot = slot.translate((0.0, 0.0, 0.0))
    return bore.union(slot).translate((0, 0, -1.0))


def hex_cutter():
    """A hexagonal bore sized across-flats to the shaft."""
    cut_len = length + 2.0
    af = shaft_dia + clearance            # across-flats = nominal hex size
    circum_r = af / math.sqrt(3.0)        # circumradius for a hexagon of this AF
    hexagon = (
        cq.Workplane("XY")
        .polygon(6, 2.0 * circum_r)       # polygon() takes the circumscribed diameter
        .extrude(cut_len)
    )
    return hexagon.translate((0, 0, -1.0))


def spline_cutter():
    """An APPROXIMATE internal involute spline: a round pitch bore with `spline_teeth`
    rectangular/rounded grooves cut around it. The many flanks share torque. This is
    a printable engagement form keyed to shaft_dia + tooth count, NOT a precision
    DIN 5480 flank profile."""
    cut_len = length + 2.0
    # Pitch bore sits at the shaft radius; grooves cut slightly out+in of it.
    pitch_r = bore_r
    tooth_w = max(0.8, (2.0 * math.pi * pitch_r / spline_teeth) * 0.5)  # ~half the pitch
    groove_depth = max(0.6, shaft_dia * 0.08)
    base = cq.Workplane("XY").circle(pitch_r).extrude(cut_len)
    # Add grooves: small radial slots around the bore so the mating shaft's teeth
    # engage. Model each groove as a thin box straddling the pitch circle.
    grooves = None
    for i in range(spline_teeth):
        ang = i * 360.0 / spline_teeth
        g = (
            cq.Workplane("XY")
            .box(groove_depth * 2.0 + pitch_r, tooth_w, cut_len,
                 centered=(False, True, False))
            .translate((pitch_r - groove_depth, 0.0, 0.0))
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        grooves = g if grooves is None else grooves.union(g)
    if grooves is not None:
        base = base.union(grooves)
    return base.translate((0, 0, -1.0))


def bore_cutter():
    if bore_type == "hex":
        return hex_cutter()
    if bore_type == "involute_spline":
        return spline_cutter()
    return keyway_cutter()


# ── Builder ──────────────────────────────────────────────────────────────────
def build_hub():
    hub = cq.Workplane("XY").circle(hub_r).extrude(length)
    hub = hub.cut(bore_cutter())

    if flange:
        # An outer flange disc at the base with a bolt-hole circle.
        fl_t = max(2.5, length * 0.25)
        fl_r = hub_r + max(6.0, flange_bolt_dia * 2.2)
        disc = cq.Workplane("XY").circle(fl_r).extrude(fl_t)
        # Bolt-hole circle midway between the hub wall and the flange rim.
        bhc_r = (hub_r + fl_r) / 2.0
        pts = []
        for i in range(flange_bolts):
            a = math.radians(i * 360.0 / flange_bolts)
            pts.append((bhc_r * math.cos(a), bhc_r * math.sin(a)))
        holes = (
            cq.Workplane("XY")
            .pushPoints(pts)
            .circle(flange_bolt_dia / 2.0)
            .extrude(fl_t + 2.0)
            .translate((0, 0, -1.0))
        )
        disc = disc.cut(holes)
        # Union the flange to the hub base (they share the z=0..fl_t band → solid).
        hub = hub.union(disc)
        # Re-cut the bore through the flange so it stays open through the whole part.
        hub = hub.cut(bore_cutter())

    return hub


result = build_hub()
