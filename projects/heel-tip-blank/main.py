"""Heel Tip Blank — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The replacement heel top-lift: the small wearing piece at the very bottom of a shoe heel,
the part that actually meets the pavement and the only part of a heel that is meant to be
consumed. On a woman's dress heel it is a plastic tip with a steel pin pressed into a bore;
on a leather-stacked man's heel it is a rubber top-lift nailed on. Cobblers replace them
constantly and the sizes are a manufacturer's private grid, so the exact tip for a
particular shoe is routinely unobtainable.

This cartridge is the blank. It carries a plain center pin bore, a chamfered wearing face,
and a slight taper from the seat face down to the ground face — the same draft a moulded
tip has, so it does not read as a cylinder stuck on a heel.

Modes (dispatched via `target_part`):
  * "round"  — the round tip (dress heel, stiletto, block heel).
  * "square" — the square tip with radiused corners (louis heel, cuban heel, boot heel).
  * "set"    — one of each on a plate, for a cobbler sizing a pair by eye.

Geometry: each tip is a single lofted solid through closed flat wires — a flat seat face and
a smaller flat ground face, never lofted to a point. The wearing chamfer is a THIRD loft
section inset below the ground face rather than a `.chamfer()` call: chamfering a tapered
loft's bottom edge loop is unreliable and can split the solid, so no post-cut fillet or
chamfer is used anywhere here. The pin bore is a cylinder overshooting both faces, so it is
a through hole that drains and cannot seal a void. Nothing is extruded off a loft face via
toPending; the loft is the whole body.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tip_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
tip_w    = float(PARAM(lambda: tip_w,    11.0))  # tip width at the seat face (mm)
tip_l    = float(PARAM(lambda: tip_l,    11.0))  # tip length at the seat face (mm)
tip_h    = float(PARAM(lambda: tip_h,    6.0))   # tip height, seat to ground (mm)
taper    = float(PARAM(lambda: taper,    0.9))   # ground face size / seat face size
pin_dia  = float(PARAM(lambda: pin_dia,  3.2))   # steel pin bore diameter (mm)
pin_depth = float(PARAM(lambda: pin_depth, 0.0))  # 0 = through bore, else blind depth (mm)
corner_r = float(PARAM(lambda: corner_r, 2.0))   # square-tip corner radius (mm)
edge_ch  = float(PARAM(lambda: edge_ch,  0.6))   # ground-face wearing chamfer (mm)

target_part = str(PARAM(lambda: target_part, "round"))  # round|square|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
tip_w = max(5.0, min(tip_w, 40.0))
tip_l = max(5.0, min(tip_l, 40.0))
tip_h = max(2.0, min(tip_h, 20.0))
taper = max(0.6, min(taper, 1.0))
# The bore must leave a real wall: never more than 55 % of the smaller ground dimension.
_ground_min = min(tip_w, tip_l) * taper
pin_dia = max(1.2, min(pin_dia, max(1.2, _ground_min * 0.55)))
pin_depth = max(0.0, min(pin_depth, tip_h - 0.8))
corner_r = max(0.3, min(corner_r, min(tip_w, tip_l) / 2.5))
edge_ch = max(0.0, min(edge_ch, min(tip_h * 0.25, _ground_min * 0.15)))

# Ground-face dimensions after draft.
g_w = tip_w * taper
g_l = tip_l * taper
g_r = max(0.2, corner_r * taper)

# The wearing chamfer is built INTO the loft as an extra inset section at Z = 0, with the
# full ground face lifted to Z = edge_ch. `.chamfer()` on a tapered loft's bottom edge loop
# is unreliable (it can split the solid), so no post-cut chamfer is used anywhere here.
ch = edge_ch if edge_ch > 0.01 else 0.0
c_w = max(0.4, g_w - 2.0 * ch)
c_l = max(0.4, g_l - 2.0 * ch)
c_r = max(0.15, g_r - ch)


def _round_body():
    """Round tip: a loft through flat circles — truncated cone, chamfer section, no point."""
    wp = cq.Workplane("XY")
    if ch > 0.0:
        wp = wp.circle(c_w / 2.0).workplane(offset=ch)
    return (
        wp.circle(g_w / 2.0)
        .workplane(offset=tip_h - ch)
        .circle(tip_w / 2.0)
        .loft(ruled=True)
    )


def _rounded_wire(length, width, rad, z):
    """A closed rounded-rectangle wire at height z — the loft section for a square tip."""
    r = max(0.2, min(rad, min(length, width) / 2.0 - 0.05))
    hx = length / 2.0 - r
    hy = width / 2.0 - r
    edges = [
        cq.Edge.makeLine(cq.Vector(-hx, -width / 2.0, z), cq.Vector(hx, -width / 2.0, z)),
        cq.Edge.makeThreePointArc(
            cq.Vector(hx, -width / 2.0, z),
            cq.Vector(hx + r * 0.70710678, -hy - r * 0.70710678, z),
            cq.Vector(length / 2.0, -hy, z),
        ),
        cq.Edge.makeLine(cq.Vector(length / 2.0, -hy, z), cq.Vector(length / 2.0, hy, z)),
        cq.Edge.makeThreePointArc(
            cq.Vector(length / 2.0, hy, z),
            cq.Vector(hx + r * 0.70710678, hy + r * 0.70710678, z),
            cq.Vector(hx, width / 2.0, z),
        ),
        cq.Edge.makeLine(cq.Vector(hx, width / 2.0, z), cq.Vector(-hx, width / 2.0, z)),
        cq.Edge.makeThreePointArc(
            cq.Vector(-hx, width / 2.0, z),
            cq.Vector(-hx - r * 0.70710678, hy + r * 0.70710678, z),
            cq.Vector(-length / 2.0, hy, z),
        ),
        cq.Edge.makeLine(cq.Vector(-length / 2.0, hy, z), cq.Vector(-length / 2.0, -hy, z)),
        cq.Edge.makeThreePointArc(
            cq.Vector(-length / 2.0, -hy, z),
            cq.Vector(-hx - r * 0.70710678, -hy - r * 0.70710678, z),
            cq.Vector(-hx, -width / 2.0, z),
        ),
    ]
    return cq.Wire.assembleEdges(edges)


def _square_body():
    """Square tip: a loft through closed rounded-rect wires, chamfer section included."""
    wires = []
    if ch > 0.0:
        wires.append(_rounded_wire(c_l, c_w, c_r, 0.0))
    wires.append(_rounded_wire(g_l, g_w, g_r, ch))
    wires.append(_rounded_wire(tip_l, tip_w, corner_r, tip_h))
    return cq.Workplane(obj=cq.Solid.makeLoft(wires, True))


def _bore(body):
    """Pin bore: overshoots both faces (through) or drills up from the seat (blind)."""
    if pin_depth <= 0.01:
        cutter = (
            cq.Workplane("XY")
            .circle(pin_dia / 2.0)
            .extrude(tip_h + 4.0)
            .translate((0, 0, -2.0))
        )
    else:
        # Blind from the SEAT face (the top, against the heel) so the bore opens upward
        # and drains; the ground face stays solid where it wears.
        cutter = (
            cq.Workplane("XY")
            .circle(pin_dia / 2.0)
            .extrude(pin_depth + 2.0)
            .translate((0, 0, tip_h - pin_depth))
        )
    return body.cut(cutter)


def build_round():
    """The round replacement tip."""
    return _bore(_round_body())


def build_square():
    """The square replacement tip with radiused corners."""
    return _bore(_square_body())


def _compound(solids):
    """Separate bodies on one plate — a Compound, never a union of non-touching solids."""
    shapes = []
    for s in solids:
        shapes.extend(s.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "round":
    result = build_round()
elif target_part == "square":
    result = build_square()
else:
    _off = max(tip_w, tip_l) + max(4.0, tip_w * 0.3)
    result = _compound([
        build_round().translate((-_off / 2.0, 0.0, 0.0)),
        build_square().translate((_off / 2.0, 0.0, 0.0)),
    ])
