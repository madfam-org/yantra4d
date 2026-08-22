"""Lacing Hook (speed hook) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The upturned speed hook a lace is zig-zagged over on a corset, a boot, or a bodice —
the rigid hard good the Fashion Cabinet `lacing-hook` notion places and bridges to here
for its geometry. Each hook is a riveted base plate carrying a J-shaped horn whose mouth
opens toward the top, so the cord drops in from above and the curl holds it. Fitted in a
row it is the classic heritage / footwear-adjacent closure; it pairs with `garment-eyelet`
on the opposing edge for corsetry and boot-style lacing.

Modes (dispatched via `target_part`):
  * "set"  — a row of `hook_count` hooks on a shared centreline, spaced by `pitch`.
  * "hook" — a single hook.

Geometry: a rounded base plate (box with vertical fillets) pierced by one rivet hole,
plus an upturned horn built from a straight cylinder stub fused to half of a
`cq.Solid.makeTorus` (trimmed with an oversized box cut) and closed at the free tip by a
short flat-capped cylinder. No swept arcs, no spheres, no lofts to a point. Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cord_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
hook_count     = int(  PARAM(lambda: hook_count,     4))     # hooks in a "set" row
cord_dia       = float(PARAM(lambda: cord_dia,       4.0))   # lace / cord diameter (mm)
plate_w        = float(PARAM(lambda: plate_w,        9.0))   # base plate width (mm)
plate_t        = float(PARAM(lambda: plate_t,        1.6))   # base plate thickness (mm)
pitch          = float(PARAM(lambda: pitch,          12.0))  # hook-to-hook spacing (mm)
rivet_hole_dia = float(PARAM(lambda: rivet_hole_dia, 2.5))   # rivet / setting hole (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|hook

# ── Safe clamps ──────────────────────────────────────────────────────────────
hook_count     = max(2, min(hook_count, 8))
cord_dia       = max(2.0, min(cord_dia, 6.0))
plate_w        = max(6.0, min(plate_w, 14.0))
plate_t        = max(1.2, min(plate_t, 3.0))
rivet_hole_dia = max(1.5, min(rivet_hole_dia, 4.0))
# The rivet hole must leave real material on every side of the plate.
rivet_hole_dia = min(rivet_hole_dia, plate_w * 0.45)
pitch          = max(8.0, min(pitch, 25.0))
# A row must not overlap plate-to-plate, so pitch never falls under the plate width.
pitch          = max(pitch, plate_w + 1.0)

# ── Derived geometry (cross-clamped so no combination is invalid) ────────────
_mouth  = cord_dia + 0.5                                    # clear cord opening (mm)
_wire_r = max(0.7, min(plate_t * 0.55, plate_w * 0.10))     # horn stock radius (mm)
_r_curl = _mouth / 2.0 + _wire_r                            # curl centreline radius (mm)

# Plate depth in Y must carry the whole horn footprint plus the rivet hole.
_horn_span = 2.0 * _r_curl + 2.0 * _wire_r
_plate_d = max(plate_w * 0.9, _horn_span + rivet_hole_dia + 3.0)

# Horn stub sits toward the front (−Y) edge, rivet hole toward the rear (+Y) edge.
_stub_y  = -_plate_d / 2.0 + _wire_r + 1.0
_rivet_y = _plate_d / 2.0 - rivet_hole_dia / 2.0 - 1.2
# Curl axis is behind the stub by one curl radius; the free tip lands one more behind.
_curl_y = _stub_y + _r_curl
_tip_y  = _stub_y + 2.0 * _r_curl

# The stub rises from the plate to the curl axis height.
_stub_top = plate_t + max(1.2, cord_dia * 0.55) + _r_curl


def build_hook():
    """One speed hook: rounded rivet plate + upturned J horn whose mouth faces +Z."""
    plate = cq.Workplane("XY").box(
        plate_w, _plate_d, plate_t, centered=(True, True, False)
    )
    try:
        plate = plate.edges("|Z").fillet(min(plate_w, _plate_d) * 0.18)
    except Exception:
        pass
    # Rivet hole — an oversized tool translated clear of both faces.
    rivet = (
        cq.Workplane("XY")
        .center(0, _rivet_y)
        .circle(rivet_hole_dia / 2.0)
        .extrude(plate_t + 4.0)
        .translate((0, 0, -2.0))
    )
    plate = plate.cut(rivet)

    # Front stub: a plain cylinder from the plate base to the curl axis height. It
    # starts at z=0 so it is volumetrically inside the plate (no coincident face).
    stub = (
        cq.Workplane("XY")
        .center(0, _stub_y)
        .circle(_wire_r)
        .extrude(_stub_top + _wire_r * 0.8)
    )
    try:
        stub = stub.edges(">Z").fillet(_wire_r * 0.45)
    except Exception:
        pass

    # Curl: a torus with its axis along X (ring lies in the YZ plane), centred behind
    # the stub at the stub's top. Keeping the lower half leaves a U that runs down the
    # stub, under the cord channel, and back up to a free tip — a J opening toward +Z.
    torus = cq.Solid.makeTorus(
        _r_curl,
        _wire_r,
        pnt=cq.Vector(0, _curl_y, _stub_top),
        dir=cq.Vector(1, 0, 0),
    )
    curl = cq.Workplane(obj=torus)
    box_s = (_r_curl + _wire_r) * 4.0
    upper_cut = (
        cq.Workplane("XY")
        .box(box_s, box_s, box_s, centered=(True, True, False))
        .translate((0, _curl_y, _stub_top))
    )
    curl = curl.cut(upper_cut)

    # Free tip: a short flat-capped cylinder rising from the curl's rear end, so the
    # arc never terminates on a knife edge and the cord is retained.
    # A slightly slimmer radius keeps the tip strictly inside the torus tube where the
    # two meet, so the fuse is volumetric rather than a fragile surface tangency.
    tip_r = _wire_r * 0.82
    tip_h = max(_wire_r * 1.8, cord_dia * 0.5)
    tip = (
        cq.Workplane("XY")
        .center(0, _tip_y)
        .circle(tip_r)
        .extrude(tip_h)
        .translate((0, 0, _stub_top - _wire_r * 0.9))
    )
    try:
        tip = tip.edges(">Z").fillet(tip_r * 0.45)
    except Exception:
        pass

    return plate.union(stub).union(curl).union(tip)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "hook":
    result = build_hook()
else:
    _n = hook_count
    _x0 = -(_n - 1) * pitch / 2.0
    result = build_hook().translate((_x0, 0, 0))
    for _i in range(1, _n):
        result = result.union(build_hook().translate((_x0 + _i * pitch, 0, 0)))

_ = math  # `math` is part of the sandbox contract; kept imported for parity.
