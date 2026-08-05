"""
Volumetric Measuring Scoop — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

You enter a target volume in millilitres and the geometry SOLVES the bowl so its
interior holds that volume. Three bowl shapes, each solved from the target:

  * hemispherical — interior V = (2/3)·π·r³  ⇒  r = (3V / 2π)^(1/3)
  * cylindrical   — interior V = π·r²·h, with h = r  ⇒  r = (V / π)^(1/3), h = r
  * conical       — interior V = (1/3)·π·r²·h, with h = 1.5·r
                                            ⇒  r = (2V / π)^(1/3), h = 1.5·r

The interior cavity is built directly from those closed-form dimensions, so the
carved volume equals the target by construction (verified in render to within a
few tenths of a percent). A handle is added, and a flat-bottom variant adds a pad
so the scoop stands on a surface without changing the interior volume.

Modes (dispatched via `target_part`):
  * "scoop"             — the bowl + handle.
  * "scoop_flat_bottom" — adds a flat base pad under the bowl so it sits flat.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_ml`).
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
target_ml     = float(PARAM(lambda: target_ml,     15.0))  # target interior volume (mL)
shape         = str(  PARAM(lambda: shape, "hemispherical"))  # bowl shape
wall          = float(PARAM(lambda: wall,           2.0))  # bowl / handle wall thickness (mm)
handle_length = float(PARAM(lambda: handle_length, 60.0))  # handle length past the rim (mm)
handle_width  = float(PARAM(lambda: handle_width,  14.0))  # handle width (mm)
handle_thick  = float(PARAM(lambda: handle_thick,   5.0))  # handle thickness (mm)
hang_hole     = bool( PARAM(lambda: hang_hole,     True))  # hanging hole at the handle end

target_part   = str(  PARAM(lambda: target_part, "scoop"))  # "scoop" | "scoop_flat_bottom"


# ── Clamp inputs ─────────────────────────────────────────────────────────────
target_ml = max(1.0, min(target_ml, 1000.0))
wall = max(1.0, min(wall, 4.0))
handle_length = max(0.0, handle_length)
handle_width = max(6.0, handle_width)
handle_thick = max(2.0, handle_thick)

V = target_ml * 1000.0  # mL -> mm^3


# ── Solve interior dimensions from the target volume ─────────────────────────
def solve_dims():
    """Return (r_in, h_in) of the interior cavity so its volume == V (mm^3)."""
    if shape == "cylindrical":
        # V = pi r^2 h, choose h = r  ->  r = (V/pi)^(1/3)
        r = (V / math.pi) ** (1.0 / 3.0)
        return r, r
    if shape == "conical":
        # V = (1/3) pi r^2 h, choose h = 1.5 r  ->  r = (2V/pi)^(1/3)
        r = (2.0 * V / math.pi) ** (1.0 / 3.0)
        return r, 1.5 * r
    # hemispherical (default): V = (2/3) pi r^3  ->  r = (3V / 2pi)^(1/3)
    r = (3.0 * V / (2.0 * math.pi)) ** (1.0 / 3.0)
    return r, r


r_in, h_in = solve_dims()
r_out = r_in + wall
CAVITY_EPS = 0.0  # cavity is exact; no clearance (this is a measuring volume)


# ── Cavity + shell builders (bowl sits with its rim at z=0, opening up) ───────
# Convention: the rim (open top) is the plane z = 0. The bowl body is BELOW z=0
# (negative Z). This keeps the handle at z≈0 and makes a flat pad easy to add.

def _half_dome(radius):
    """A lower half-sphere of the given radius, flat face at z=0, revolved from a
    half-disk profile in XZ. The arc stops a hair before the axis and a tiny flat
    closes the pole: revolving an edge that lands exactly ON the axis leaves a
    degenerate (cracked) triangle at the pole, so the mesh reports non-watertight.
    The flat is ~0.4 mm across, changing the volume by < 0.002 mL — negligible for
    a measuring scoop and far below the required accuracy."""
    eps = min(0.4, radius * 0.06)
    hp = math.sqrt(max(0.0, radius * radius - eps * eps))  # pole depth at x=eps
    return (
        cq.Workplane("XZ")
        .moveTo(0.0, 0.0)
        .lineTo(radius, 0.0)                      # rim at z=0
        .threePointArc((radius * math.cos(math.pi / 4.0),
                        -radius * math.sin(math.pi / 4.0)),
                       (eps, -hp))                # arc to just off the axis
        .lineTo(0.0, -hp)                          # tiny flat across the pole
        .close()                                   # back up the axis to (0,0)
        .revolve(360)
    )


def _open_top(cavity, radius):
    """Add a short straight collar on top of a cavity so it pokes above the rim
    (z>0). Cutting with a cavity whose top is ABOVE the outer rim opens the bowl
    cleanly instead of leaving a coincident face at z=0 (which breaks manifold)."""
    collar = cq.Workplane("XY").circle(radius).extrude(1.0)  # z: 0 -> +1
    return cavity.union(collar)


def hemispherical():
    """Interior = lower half-sphere (radius r_in) with the flat opening at z=0."""
    outer = _half_dome(r_out)
    cavity = _open_top(_half_dome(r_in), r_in)
    return outer, cavity, -r_out  # bottom_z


def cylindrical():
    """Interior = cylinder radius r_in, depth h_in, opening up at z=0."""
    outer = (
        cq.Workplane("XY")
        .circle(r_out)
        .extrude(-(h_in + wall))  # floor thickness = wall below the cavity
    )
    cavity = cq.Workplane("XY").circle(r_in).extrude(-h_in)
    return outer, cavity, -(h_in + wall)


def conical():
    """Interior = inverted cone (tip at bottom, mouth radius r_in at z=0)."""
    # Outer: a frustum-ish solid — a cone of mouth radius r_out with a flat base.
    depth = h_in + wall
    # Build the outer as a revolved trapezoid so the tip has real wall + a small
    # flat so the point is printable and watertight.
    tip_flat = max(0.6, wall * 0.5)
    outer = (
        cq.Workplane("XZ")
        .polyline([
            (0.0, 0.0),
            (r_out, 0.0),
            (tip_flat, -depth),
            (0.0, -depth),
        ]).close()
        .revolve(360)
    )
    # Cavity cone: give the tip a tiny flat (off the axis) so the revolve doesn't
    # crack at the pole. Kept small (and scaled with r_in) so even at tiny target
    # volumes the interior stays within a couple of percent of target.
    c_eps = min(0.25, r_in * 0.03)
    cavity = (
        cq.Workplane("XZ")
        .polyline([
            (0.0, 0.0),
            (r_in, 0.0),
            (c_eps, -h_in),
            (0.0, -h_in),
        ]).close()
        .revolve(360)
    )
    cavity = _open_top(cavity, r_in)
    return outer, cavity, -depth


def build_bowl():
    if shape == "cylindrical":
        outer, cavity, bottom_z = cylindrical()
    elif shape == "conical":
        outer, cavity, bottom_z = conical()
    else:
        outer, cavity, bottom_z = hemispherical()
    bowl = outer.cut(cavity)
    return bowl, bottom_z


# ── Handle ───────────────────────────────────────────────────────────────────
def build_handle():
    """A flat handle extending in +X from the rim, at the top (z≈0)."""
    if handle_length < 1.0:
        return None
    # Start slightly inside the rim so it fuses with the bowl wall.
    x0 = r_out - wall * 0.5
    length = handle_length + wall
    handle = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x0, 0.0, -handle_thick))
        .box(length, handle_width, handle_thick, centered=(False, True, False))
    )
    # Round the far end corners and soften.
    try:
        handle = handle.edges("|Z and >X").fillet(min(handle_width * 0.4, 6.0))
    except Exception:
        pass
    # Hanging hole near the far end.
    if hang_hole:
        hx = x0 + length - max(handle_width * 0.5, 7.0)
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, 0.0, -handle_thick - 1.0))
            .circle(min(handle_width * 0.28, 4.0))
            .extrude(handle_thick + 2.0)
        )
        handle = handle.cut(hole)
    return handle


# ── Flat-bottom pad ──────────────────────────────────────────────────────────
def build_pad(bottom_z):
    """A flat disk pad under the lowest point of the bowl so it stands upright.
    Does NOT touch the interior cavity, so the measured volume is unchanged."""
    pad_h = max(1.5, wall)
    pad_r = max(r_out * 0.55, 8.0)
    # Place the pad so its top overlaps the bowl bottom and its base is flat.
    pad = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, bottom_z))
        .circle(pad_r)
        .extrude(pad_h)  # extends up into the bowl bottom (overlap = watertight)
        .translate((0, 0, -pad_h + 0.4))
    )
    try:
        pad = pad.edges("|Z").fillet(min(pad_r * 0.2, 3.0))
    except Exception:
        pass
    return pad


# ── Assemble ─────────────────────────────────────────────────────────────────
def build():
    bowl, bottom_z = build_bowl()
    body = bowl
    handle = build_handle()
    if handle is not None:
        body = body.union(handle)
    if target_part == "scoop_flat_bottom":
        body = body.union(build_pad(bottom_z))
    return body


result = build()
