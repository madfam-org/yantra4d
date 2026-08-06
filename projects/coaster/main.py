"""
Coaster / Trivet — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A patterned disc that protects a surface from a cup or a hot pot. Choose a
round, square, or hex outline; an optional raised edge lip catches condensation
runoff; and a top pattern (solid / grid cutout / concentric rings / honeycomb)
adds style while saving material. Two parts share one geometry:

  * "coaster" — the small drink coaster (target_part == "coaster").
  * "trivet"  — a larger, thicker version for hot pots and pans.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `thickness`).
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
target_part = str(PARAM(lambda: target_part, "coaster"))  # "coaster" | "trivet"

diameter    = float(PARAM(lambda: diameter,    95.0))   # round Ø / square & hex width across flats
thickness   = float(PARAM(lambda: thickness,    5.0))   # base disc thickness
shape       = str(  PARAM(lambda: shape,     "round"))  # "round" | "square" | "hex"
lip_height  = float(PARAM(lambda: lip_height,   2.5))   # raised edge to catch condensation (0 = flat)
lip_wall    = float(PARAM(lambda: lip_wall,     3.0))   # thickness of the raised lip ring
pattern     = str(  PARAM(lambda: pattern,    "grid-cutout"))  # top decoration / material saver
pattern_depth = float(PARAM(lambda: pattern_depth, 2.0))  # how deep the pattern is cut into the top

# Trivet is a scaled, sturdier variant of the same object.
if target_part == "trivet":
    diameter  = max(diameter, 150.0)
    thickness = max(thickness, 6.0)

# ── Clamps (keep geometry valid & watertight) ────────────────────────────────
diameter    = max(30.0, diameter)
thickness   = max(2.0, thickness)
lip_height  = max(0.0, min(lip_height, 12.0))
lip_wall    = max(1.5, min(lip_wall, diameter / 4.0))
# The pattern must never cut through the floor: keep a solid base under it.
pattern_depth = max(0.0, min(pattern_depth, thickness - 1.5))

R = diameter / 2.0          # outer "radius" (across-flats/2 for square & hex)
inner_R = R - lip_wall      # radius of the recessed pattern field inside the lip


# ── Outline ──────────────────────────────────────────────────────────────────
def outline_wire(radius):
    """A closed 2D wire on XY for the chosen outline at the given radius
    (round: true radius; square: half-width; hex: across-flats/2)."""
    wp = cq.Workplane("XY")
    if shape == "square":
        return wp.rect(radius * 2.0, radius * 2.0)
    if shape == "hex":
        # Regular hexagon, flat-to-flat = 2*radius → circumradius = radius / cos(30°).
        circum = radius / math.cos(math.radians(30.0))
        return wp.polygon(6, circum * 2.0)
    return wp.circle(radius)


def base_solid(radius, height):
    """Extruded outline as a solid block."""
    return outline_wire(radius).extrude(height)


# ── Pattern cutters (cut into the top face, never through the floor) ──────────
def _grid_cutter(depth):
    """Square lattice of slots leaving a grid of ribs."""
    if depth <= 0.05:
        return None
    field = inner_R * 2.0
    slot = 6.0          # open channel width
    rib = 3.0           # solid rib width
    step = slot + rib
    n = int(field / step) + 2
    cutters = []
    z0 = thickness - depth
    start = -(n // 2) * step
    for i in range(n + 1):
        c = start + i * step
        # vertical channel
        cutters.append(
            cq.Workplane("XY").transformed(offset=cq.Vector(c, 0, z0))
            .box(slot, field + step, depth + 1.0, centered=(True, True, False))
        )
        # horizontal channel
        cutters.append(
            cq.Workplane("XY").transformed(offset=cq.Vector(0, c, z0))
            .box(field + step, slot, depth + 1.0, centered=(True, True, False))
        )
    cutter = cutters[0]
    for c in cutters[1:]:
        cutter = cutter.union(c)
    return cutter


def _rings_cutter(depth):
    """Concentric annular grooves."""
    if depth <= 0.05:
        return None
    groove = 4.0
    wall = 3.0
    z0 = thickness - depth
    cutters = []
    r_out = inner_R - 2.0
    while r_out - groove > 3.0:
        r_in = r_out - groove
        ring = (
            cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
            .circle(r_out).circle(r_in).extrude(depth + 1.0)
        )
        cutters.append(ring)
        r_out = r_in - wall
    if not cutters:
        return None
    cutter = cutters[0]
    for c in cutters[1:]:
        cutter = cutter.union(c)
    return cutter


def _honeycomb_cutter(depth):
    """Hex-hole honeycomb array."""
    if depth <= 0.05:
        return None
    hole_across = 9.0        # hex hole flat-to-flat
    wall = 3.0
    pitch = hole_across + wall
    circum = (hole_across / 2.0) / math.cos(math.radians(30.0))
    row_h = pitch * math.sqrt(3.0) / 2.0
    z0 = thickness - depth
    n = int(inner_R / pitch) + 2
    pts = []
    for row in range(-n, n + 1):
        y = row * row_h
        x_off = (pitch / 2.0) if (row % 2) else 0.0
        for col in range(-n, n + 1):
            x = col * pitch + x_off
            # keep the hole centre inside the pattern field (with margin)
            if math.hypot(x, y) <= inner_R - hole_across / 2.0 - 1.0:
                pts.append((x, y))
    if not pts:
        return None
    cutter = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0))
        .pushPoints(pts).polygon(6, circum * 2.0).extrude(depth + 1.0)
    )
    return cutter


def apply_pattern(body):
    """Cut the chosen decorative pattern into the top face."""
    if pattern == "solid" or pattern_depth <= 0.05:
        return body
    if pattern == "concentric-rings":
        cutter = _rings_cutter(pattern_depth)
    elif pattern == "honeycomb":
        cutter = _honeycomb_cutter(pattern_depth)
    else:  # grid-cutout (default)
        cutter = _grid_cutter(pattern_depth)
    if cutter is None:
        return body
    # Intersect the cutter with the pattern field so channels never breach the
    # lip / outline wall — guarantees the result stays watertight.
    field = base_solid(inner_R, thickness + 2.0)
    cutter = cutter.intersect(field)
    return body.cut(cutter)


# ── Lip (raised edge that catches condensation) ──────────────────────────────
def add_lip(body):
    """Add a raised ring around the rim so drips are contained."""
    if lip_height <= 0.05:
        return body
    ring = base_solid(R, thickness + lip_height).cut(base_solid(inner_R, thickness + lip_height + 1.0))
    return body.union(ring)


# ── Build ────────────────────────────────────────────────────────────────────
def build():
    body = base_solid(R, thickness)
    body = apply_pattern(body)
    body = add_lip(body)
    # Soften the outer top edge for comfort; non-fatal if the radius is degenerate.
    try:
        body = body.edges(">Z").edges("|Z").fillet(0.6)
    except Exception:
        pass
    return body


result = build()
