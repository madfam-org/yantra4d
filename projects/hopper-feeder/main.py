"""
Hopper / Funnel Feeder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hopper that funnels bulk material (pellets, granules, powder, small parts) down
to an outlet. The taper wall angle is exposed so it can be set steeper than the
material's angle of repose, ensuring reliable flow. Built as a genuine hollow
tapered shell: a solid outer funnel with an inner cavity and an outlet bore cut
away, so the result is watertight and printable.

Three build targets are dispatched by `target_part`:
  - "round_hopper"  : a conical funnel (round top -> round outlet)
  - "square_hopper" : a pyramidal funnel (square top -> round outlet)
  - "trough_feeder" : a linear wedge trough narrowing to a slot outlet

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `outlet_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
top_w        = float(PARAM(lambda: top_w,        120.0))  # top opening width (X)
top_d        = float(PARAM(lambda: top_d,        120.0))  # top opening depth (Y)
outlet_dia   = float(PARAM(lambda: outlet_dia,    20.0))  # outlet diameter (round)
height       = float(PARAM(lambda: height,       100.0))  # funnel body height
wall_angle   = float(PARAM(lambda: wall_angle,    60.0))  # taper wall angle (deg from horizontal)
wall         = float(PARAM(lambda: wall,           2.4))  # shell wall thickness
outlet_len   = float(PARAM(lambda: outlet_len,    15.0))  # straight outlet spout length
rim          = bool( PARAM(lambda: rim,           True))  # add a top stiffening rim
slot_len     = float(PARAM(lambda: slot_len,      80.0))  # outlet slot length (trough)

shape        = str(  PARAM(lambda: shape,       "round"))  # round|square|wedge (informational)
target_part  = str(  PARAM(lambda: target_part, "round_hopper"))

# ── Derived / clamped ────────────────────────────────────────────────────────
wall        = max(1.2, min(wall, 8.0))
outlet_dia  = max(4.0, min(outlet_dia, min(top_w, top_d) - 4.0 * wall))
wall_angle  = max(20.0, min(wall_angle, 85.0))
outlet_len  = max(0.0, min(outlet_len, 60.0))

# The taper height implied by the wall angle and the top->outlet horizontal run.
# We honour the user's `height` but never let the cone invert: the horizontal
# run from top edge to outlet edge sets a minimum height for the chosen angle.
_tan = math.tan(math.radians(wall_angle))


def _taper_height(run):
    """Vertical drop for a horizontal `run` at the configured wall angle."""
    return run * _tan


# ── Helpers ──────────────────────────────────────────────────────────────────
def _round_shell(r_top, r_bot, h):
    """Hollow conical frustum (outer minus inner), watertight, base at z=0.
    Wall thickness is `wall` measured horizontally."""
    outer = (
        cq.Workplane("XY").circle(r_top)
        .workplane(offset=h).circle(max(r_bot, 0.5))
        .loft(combine=True)
    )
    inner = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(max(r_top - wall, 0.4))
        .workplane(offset=h + 1.0).circle(max(r_bot - wall, 0.3))
        .loft(combine=True)
    )
    return outer.cut(inner)


def _spout(r_out, h, z0):
    """A straight hollow cylindrical outlet spout of outer radius r_out."""
    outer = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0)).circle(r_out).extrude(h)
    inner = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0 - 0.5))
        .circle(max(r_out - wall, 0.3)).extrude(h + 1.0)
    )
    return outer.cut(inner)


def _top_rim(r_top, kind):
    """Optional stiffening rim around the top opening."""
    rim_t = wall * 1.8
    rim_h = max(4.0, wall * 3.0)
    if kind == "round":
        outer = cq.Workplane("XY").circle(r_top + rim_t).extrude(rim_h)
        inner = (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -0.5))
            .circle(r_top - wall).extrude(rim_h + 1.0)
        )
        return outer.cut(inner)
    # rectangular rim
    ow, od = r_top
    outer = cq.Workplane("XY").box(ow + 2 * rim_t, od + 2 * rim_t, rim_h, centered=(True, True, False))
    inner = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -0.5))
        .box(ow - 2 * wall, od - 2 * wall, rim_h + 1.0, centered=(True, True, False))
    )
    return outer.cut(inner)


# ── round_hopper ─────────────────────────────────────────────────────────────
def build_round_hopper():
    r_top = min(top_w, top_d) / 2.0
    r_out = outlet_dia / 2.0 + wall  # outer radius at the throat
    run = r_top - r_out
    body_h = max(height, _taper_height(run) if run > 0 else height, outlet_dia)

    body = _round_shell(r_top, r_out, body_h)
    if outlet_len > 0.1:
        body = body.union(_spout(r_out, outlet_len, -outlet_len))
    if rim:
        body = body.union(_top_rim(r_top, "round"))
    return body


# ── square_hopper (pyramidal -> round outlet) ────────────────────────────────
def build_square_hopper():
    r_out = outlet_dia / 2.0 + wall
    half_top_w = top_w / 2.0
    half_top_d = top_d / 2.0
    run = min(half_top_w, half_top_d) - r_out
    body_h = max(height, _taper_height(run) if run > 0 else height, outlet_dia)

    # Outer: square top lofted to a small square around the throat.
    thr = r_out  # square half-size at the throat that circumscribes the outlet
    outer = (
        cq.Workplane("XY").rect(top_w, top_d)
        .workplane(offset=body_h).rect(2 * thr, 2 * thr)
        .loft(combine=True)
    )
    # Inner cavity: offset inward by `wall`, opening to the outlet bore.
    inner = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -0.5))
        .rect(top_w - 2 * wall, top_d - 2 * wall)
        .workplane(offset=body_h + 1.0).rect(max(2 * (thr - wall), 0.6), max(2 * (thr - wall), 0.6))
        .loft(combine=True)
    )
    body = outer.cut(inner)

    # Clean round outlet bore straight through the throat region.
    bore = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -outlet_len - 1.0))
        .circle(outlet_dia / 2.0).extrude(body_h + outlet_len + 2.0)
    )
    body = body.cut(bore)

    if outlet_len > 0.1:
        body = body.union(_spout(r_out, outlet_len, -outlet_len))
    if rim:
        body = body.union(_top_rim((top_w, top_d), "rect"))
    return body


# ── trough_feeder (linear wedge -> slot) ─────────────────────────────────────
def build_trough_feeder():
    """A linear trough: a wide top opening narrowing (in one axis) down to a slot
    of width `outlet_dia`, running the full `slot_len` in the other axis."""
    length = max(slot_len, 20.0)
    half_top = top_w / 2.0
    slot_half = max(outlet_dia / 2.0 + wall, 2.0)
    run = half_top - slot_half
    body_h = max(height, _taper_height(run) if run > 0 else height, outlet_dia)

    # Outer wedge: trapezoid profile in XZ, extruded along Y for `length`.
    outer = (
        cq.Workplane("XZ")
        .moveTo(-half_top, body_h)
        .lineTo(half_top, body_h)
        .lineTo(slot_half, 0.0)
        .lineTo(-slot_half, 0.0)
        .close()
        .extrude(length, both=False)
        .translate((0, -length / 2.0, 0))
    )
    # Inner cavity: same trapezoid shrunk by `wall`, opening through the slot.
    inner = (
        cq.Workplane("XZ")
        .moveTo(-(half_top - wall), body_h + 1.0)
        .lineTo(half_top - wall, body_h + 1.0)
        .lineTo(max(slot_half - wall, 0.4), -1.0)
        .lineTo(-max(slot_half - wall, 0.4), -1.0)
        .close()
        .extrude(length - 2 * wall, both=False)
        .translate((0, -(length - 2 * wall) / 2.0, 0))
    )
    body = outer.cut(inner)

    # Slot outlet: cut a through slot of width outlet_dia along the bottom.
    slot = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -outlet_len - 1.0))
        .box(outlet_dia, length - 2 * wall, outlet_len + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "round_hopper":  build_round_hopper,
    "square_hopper": build_square_hopper,
    "trough_feeder": build_trough_feeder,
}

result = _dispatch.get(target_part, build_round_hopper)()
