"""
Angle Gauge / Setup Block — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Precision angle references for setting saw blades, bevels, miters and fences. A
setup block stacks several known-angle wedges into one stepped tool; a protractor
gauge fans reference edges from a common vertex; a saw gauge is a single-angle
reference block that seats against a blade to set the bevel.

Three modes, dispatched by `target_part`:
  - setup_block     : a staircase of wedges, one per angle in the chosen set,
                      each face a known reference angle.
  - protractor_gauge: a quarter-round body with a flat edge cut at each angle so
                      a blade/bevel can be checked against the marked edges.
  - saw_gauge       : a single wedge block of one angle (the first in the set)
                      with a flat register base to set a saw or table.

The `angles` select maps to a list of reference angles (degrees):
  common     -> 15, 22.5, 30, 45
  fine       -> 5, 10, 15, 20
  roofing    -> 18.4, 26.6, 33.7, 45   (4:12, 6:12, 8:12, 12:12 pitches)

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `angles`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
angles      = str(  PARAM(lambda: angles, "common"))   # angle set (select)
size        = float(PARAM(lambda: size,      50.0))    # reference edge length
width       = float(PARAM(lambda: width,     30.0))    # tool width (extrusion)
base_t      = float(PARAM(lambda: base_t,     8.0))    # base thickness under wedges
single_ang  = float(PARAM(lambda: single_ang, 45.0))   # saw-gauge single angle

target_part = str(PARAM(lambda: target_part, "setup_block"))

_SETS = {
    "common": [15.0, 22.5, 30.0, 45.0],
    "fine": [5.0, 10.0, 15.0, 20.0],
    "roofing": [18.4, 26.6, 33.7, 45.0],
}
angle_list = _SETS.get(angles, _SETS["common"])


# ── Helpers ──────────────────────────────────────────────────────────────────
def wedge(run, height, w):
    """A right-triangle prism (a wedge): vertical back of `height`, horizontal
    run of `run`, extruded `w` in Y and centred on Y=0. The hypotenuse is the
    reference angle face. Base at z=0, right angle at the origin.

    Note: an XZ workplane extrudes along its −Y normal, so the raw prism spans
    y∈[−w, 0]; translating by +w/2 centres it on Y=0."""
    pts = [(0.0, 0.0), (run, 0.0), (0.0, height)]
    return (
        cq.Workplane("XZ")
        .polyline(pts)
        .close()
        .extrude(w)
        .translate((0, w / 2.0, 0))
    )


def wedge_for_angle(a, ref):
    """Wedge whose hypotenuse makes angle `a` with the horizontal; the reference
    edge (hypotenuse) has length `ref`."""
    a = max(1.0, min(a, 80.0))
    run = ref * math.cos(math.radians(a))
    height = ref * math.sin(math.radians(a))
    return wedge(run, height, width), run, height


# ── Setup block (staircase of wedges) ────────────────────────────────────────
def build_setup_block():
    """One wedge per angle, stacked side by side on a common base so the whole
    set is a single stepped block. Each hypotenuse is a known reference angle."""
    base_w = 0.0
    runs = []
    for a in angle_list:
        _, run, _ = wedge_for_angle(a, size)
        runs.append(run)
        base_w += run + 6.0
    base = cq.Workplane("XY").box(base_w, width + 6.0, base_t, centered=(True, True, False))
    # Soften only the base's bottom edges (safe rectangular loop) BEFORE unioning
    # the wedges so the fillet never touches a wedge's acute apex.
    try:
        base = base.edges("|X and <Z").fillet(min(base_t * 0.25, 1.5))
    except Exception:
        pass
    body = base

    x = -base_w / 2.0 + 3.0
    for a, run in zip(angle_list, runs):
        w_solid, run, _ = wedge_for_angle(a, size)
        body = body.union(w_solid.translate((x, 0, base_t)))
        x += run + 6.0
    return body


# ── Protractor gauge (fan of reference edges) ────────────────────────────────
def build_protractor_gauge():
    """A quarter-round plate with an engraved reference ray for each angle,
    fanning from a common vertex at the origin. A blade laid along a groove reads
    its angle from the horizontal base."""
    r = size
    # Quarter disc in the +X/+Z quadrant (vertex at origin). An XZ workplane
    # extrudes along −Y, so the raw disc spans y∈[−width,0]; +width/2 centres it.
    quarter = (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(r, 0.0)
        .radiusArc((0.0, r), -r)
        .close()
        .extrude(width)
        .translate((0, width / 2.0, 0))
    )
    body = quarter
    # Engrave a shallow groove along each angle's ray from the vertex so the
    # reference edge is unmistakable. Each groove is a thin bar (full width) that
    # is rotated about the Y axis to the marked angle and cut into the top face.
    for a in angle_list:
        a = max(1.0, min(a, 88.0))
        groove = (
            cq.Workplane("XZ")
            .rect(r * 1.2, 1.4, centered=(False, True))
            .extrude(2.5)
            .rotate((0, 0, 0), (0, -1, 0), a)
            .translate((0, width / 2.0 + 1.0, 0))
        )
        body = body.cut(groove)
    try:
        body = body.edges("|Y").fillet(0.8)
    except Exception:
        pass
    return body


# ── Saw gauge (single-angle register block) ──────────────────────────────────
def build_saw_gauge():
    """A single wedge of `single_ang` on a flat base — set a saw table or blade
    bevel by seating the tool's hypotenuse against the blade with the base flat
    on the table."""
    a = max(1.0, min(single_ang, 80.0))
    run = size * math.cos(math.radians(a))
    height = size * math.sin(math.radians(a))
    base = cq.Workplane("XY").box(run + 12.0, width + 6.0, base_t, centered=(True, True, False))
    # Soften only the base's bottom edges (a safe rectangular loop) BEFORE the
    # union so the fillet never touches the wedge's acute apex — filleting that
    # apex at steep angles crashes the OCCT kernel.
    try:
        base = base.edges("|X and <Z").fillet(min(base_t * 0.25, 1.5))
    except Exception:
        pass
    w_solid = wedge(run, height, width).translate((-run / 2.0, 0, base_t))
    body = base.union(w_solid)
    # A finger notch through the base so it's easy to pick up.
    notch = (
        cq.Workplane("XY")
        .circle(min(width, run) * 0.22)
        .extrude(base_t + 2.0)
        .translate((run / 2.0 + 2.0, 0, -1.0))
    )
    body = body.cut(notch)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "protractor_gauge":
    result = build_protractor_gauge()
elif target_part == "saw_gauge":
    result = build_saw_gauge()
else:
    result = build_setup_block()
