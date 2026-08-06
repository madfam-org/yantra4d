"""
Shelf Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A right-angle L-bracket that supports a shelf, load-aware: the wall thickness is
bounded so the part stays structurally sane, and an optional diagonal gusset
braces the corner against the shelf load. Screw holes are placed on both arms so
the bracket bolts to the wall and up into the shelf.

Parts (via target_part):
  - "bracket"      : a single L-bracket.
  - "bracket_pair" : a mirrored left + right pair, laid side by side.

The bracket lies with the vertical arm in the +Z direction against the -Y "wall"
plane, and the horizontal arm reaching out in +Y under the shelf.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `thickness`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
arm_h     = float(PARAM(lambda: arm_h,      80.0))   # horizontal arm length (under shelf, +Y)
arm_v     = float(PARAM(lambda: arm_v,      80.0))   # vertical arm length (up wall, +Z)
width     = float(PARAM(lambda: width,      30.0))   # bracket width (X)
thickness = float(PARAM(lambda: thickness,   5.0))   # plate thickness
brace     = bool( PARAM(lambda: brace,      True))   # diagonal gusset brace
screw_d   = float(PARAM(lambda: screw_d,     4.5))   # screw clearance hole dia
holes_per_arm = int(PARAM(lambda: holes_per_arm, 2)) # screw holes per arm
gap       = float(PARAM(lambda: gap,        10.0))   # spacing between the pair (mm)

target_part = str(PARAM(lambda: target_part, "bracket"))  # bracket | bracket_pair

# ── Clamp for structural sanity ──────────────────────────────────────────────
# Thickness bounded: at least 2 mm, at most ~1/4 of the shorter arm and < half width.
arm_h = max(20.0, arm_h)
arm_v = max(20.0, arm_v)
width = max(12.0, width)
_t_max = max(3.0, min(arm_h, arm_v) / 4.0)
thickness = max(2.0, min(thickness, _t_max, width / 2.0 - 0.5))
screw_d = max(2.0, min(screw_d, width - 4.0))
holes_per_arm = max(0, min(holes_per_arm, 4))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _hole_positions(arm_len):
    """Center offsets (along the arm, from the inside corner) for the screw holes,
    kept clear of the corner and the free end."""
    if holes_per_arm <= 0:
        return []
    margin = max(thickness + screw_d, 12.0)
    usable = arm_len - 2.0 * margin
    if usable <= 0 or holes_per_arm == 1:
        return [thickness + max((arm_len - thickness) / 2.0, screw_d)]
    step = usable / (holes_per_arm - 1)
    return [margin + step * i for i in range(holes_per_arm)]


def _l_body():
    """The L: a horizontal plate (in the XY plane, arm reaching +Y) joined to a
    vertical plate (in the XZ plane, arm reaching +Z), sharing the corner."""
    # Horizontal arm: occupies X:[-w/2,w/2], Y:[0,arm_h], Z:[0,thickness]
    horiz = (
        cq.Workplane("XY")
        .box(width, arm_h, thickness, centered=(True, False, False))
        .translate((0, 0, 0))
    )
    # Vertical arm: occupies X:[-w/2,w/2], Y:[0,thickness], Z:[0,arm_v]
    vert = (
        cq.Workplane("XY")
        .box(width, thickness, arm_v, centered=(True, False, False))
    )
    body = horiz.union(vert)
    return body


def _brace():
    """A triangular gusset spanning the inside of the corner, full bracket width.
    Right triangle from (Y=thickness,Z=thickness) out to the arms."""
    reach_y = min(arm_h - thickness, arm_v)  # keep it inside the arms
    reach_z = min(arm_v - thickness, arm_h)
    reach = max(8.0, min(reach_y, reach_z) * 0.7)
    pts = [
        (thickness, thickness),
        (thickness + reach, thickness),
        (thickness, thickness + reach),
    ]
    tri = (
        cq.Workplane("YZ")
        .polyline(pts).close()
        .extrude(width / 2.0, both=True)
    )
    # Give the gusset a bit less width than the arms so it prints cleanly.
    return tri


def _drill(body):
    """Bore screw holes through both arms."""
    r = screw_d / 2.0
    # Horizontal arm holes: axis along Z, at Y offsets.
    for y in _hole_positions(arm_h):
        tool = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, -1.0))
            .circle(r).extrude(thickness + 2.0)
        )
        body = body.cut(tool)
    # Vertical arm holes: axis along Y, at Z offsets.
    for z in _hole_positions(arm_v):
        tool = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, z, 1.0))
            .circle(r).extrude(thickness + 2.0)
        )
        body = body.cut(tool)
    return body


def build_bracket():
    body = _l_body()
    if brace:
        body = body.union(_brace())
    body = _drill(body)
    # Chamfer the two outer free edges lightly for print/handling; non-fatal.
    try:
        body = body.edges("|X").edges(">Y or >Z").chamfer(min(thickness * 0.3, 1.0))
    except Exception:
        pass
    return body


def build_pair():
    left = build_bracket()
    right = build_bracket().mirror("YZ")
    # Space them apart along X.
    shift = width / 2.0 + gap / 2.0
    return left.translate((-shift, 0, 0)).union(right.translate((shift, 0, 0)))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bracket_pair":
    result = build_pair()
else:
    result = build_bracket()
