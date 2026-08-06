"""
Circuit / Breadboard Trainer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Oversized, tactile circuit-teaching hardware on the universal 2.54 mm (0.1 in)
breadboard pitch. Big enough for small hands and group demonstration, it teaches
component identification, lead spacing and how a solderless breadboard connects.
Three interoperating pieces:

  - breadboard      : a base board with a grid of lead holes on the 2.54 mm pitch
                      and a centre channel (the DIP gutter) — the socket board.
  - component_holder: an oversized component body with two lead legs spaced an
                      integer number of pitches apart, so it plugs into the board
                      (a giant resistor / LED / capacitor stand-in to label).
  - bus_strip       : a power / ground rail strip — a long bar with a single row
                      of holes on the pitch and a top rail groove (the +/- rails).

Interoperable figures (cited as the CDG `standard` = "breadboard 2.54mm"):
  - hole pitch = 2.54 mm  (0.1 inch — the universal breadboard / DIP lead pitch)
  - lead / hole diameter  = 1.0 mm typical (oversized boards scale this up)

Watertight strategy:
  The breadboard is a solid slab with THROUGH holes (open both faces → vented)
  and a centre channel milled from the top (open to the top face → vented). The
  component holder is a solid body with SOLID leg pegs unioned underneath
  (overlapping into the body). The bus strip is a solid bar with a row of through
  holes and a top groove (open to top). Blank blanks are filleted BEFORE cutting.
  No hollow sealed cavities, no revolve-of-cut, no oblique curved booleans.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>); render worker injects
    target_part = <mode.parts[0]>. Do NOT use globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "breadboard"))
# "breadboard" | "component_holder" | "bus_strip"

pitch = float(PARAM(lambda: pitch, 2.54))             # breadboard hole pitch (mm)
scale = float(PARAM(lambda: scale, 4.0))              # oversize multiplier for teaching
hole_dia = float(PARAM(lambda: hole_dia, 1.0))        # nominal lead hole diameter (mm)

bb_cols = int(PARAM(lambda: bb_cols, 10))             # breadboard hole columns (X)
bb_rows = int(PARAM(lambda: bb_rows, 6))              # breadboard hole rows (Y)
bb_thick = float(PARAM(lambda: bb_thick, 3.0))        # breadboard slab thickness (mm, pre-scale)
gutter = bool(PARAM(lambda: gutter, True))            # centre DIP channel

comp_pitches = int(PARAM(lambda: comp_pitches, 4))    # lead spacing in whole pitches
comp_len = float(PARAM(lambda: comp_len, 12.0))       # component body length (mm, pre-scale)
comp_dia = float(PARAM(lambda: comp_dia, 5.0))        # component body diameter (mm, pre-scale)
leg_len = float(PARAM(lambda: leg_len, 6.0))          # lead leg length below body (mm, pre-scale)

bus_holes = int(PARAM(lambda: bus_holes, 12))         # bus-strip hole count

# ── Clamp inputs ─────────────────────────────────────────────────────────────
pitch = max(1.5, min(pitch, 6.0))
scale = max(1.0, min(scale, 10.0))
hole_dia = max(0.5, min(hole_dia, pitch - 0.5))
bb_cols = max(2, min(bb_cols, 30))
bb_rows = max(2, min(bb_rows, 30))
bb_thick = max(2.0, min(bb_thick, 10.0))
comp_pitches = max(1, min(comp_pitches, 20))
comp_len = max(4.0, min(comp_len, 60.0))
comp_dia = max(2.0, min(comp_dia, 20.0))
leg_len = max(2.0, min(leg_len, 20.0))
bus_holes = max(2, min(bus_holes, 40))

# Everything is expressed at the real breadboard scale, then multiplied by
# `scale` so a classroom board is oversized but geometrically faithful.
P = pitch * scale                                     # working pitch
HOLE_R = (hole_dia * scale) / 2.0
LEG_R = max(0.6, (hole_dia * scale) / 2.0 - 0.15 * scale)   # legs slightly under hole


def _grid_centers(cols, rows):
    x0 = -(cols - 1) * P / 2.0
    y0 = -(rows - 1) * P / 2.0
    return [(x0 + c * P, y0 + r * P) for c in range(cols) for r in range(rows)]


def build_breadboard():
    """A base board: grid of through lead holes on the pitch + a centre gutter."""
    thick = bb_thick * scale
    margin = P
    w = (bb_cols - 1) * P + 2.0 * margin
    d = (bb_rows - 1) * P + 2.0 * margin
    slab = (
        cq.Workplane("XY")
        .box(w, d, thick, centered=(True, True, False))
    )
    # Fillet the blank BEFORE cutting holes.
    try:
        slab = slab.edges("|Z").fillet(min(margin * 0.5, 2.0 * scale))
    except Exception:
        pass

    # Centre DIP gutter: a shallow channel down the middle (open to top → vented).
    if gutter and bb_rows >= 4:
        gw = P
        gd_depth = min(thick * 0.5, 3.0 * scale)
        chan = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, thick - gd_depth))
            .box(w + 2.0, gw, gd_depth + 0.1, centered=(True, True, False))
        )
        slab = slab.cut(chan)

    # Through lead holes on the pitch grid (vented both faces).
    centers = _grid_centers(bb_cols, bb_rows)
    holes = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints(centers)
        .circle(HOLE_R)
        .extrude(thick + 2.0)
    )
    body = slab.cut(holes)
    return body


def build_component_holder():
    """An oversized component body with two lead legs `comp_pitches` apart."""
    body_len = comp_len * scale
    body_r = (comp_dia * scale) / 2.0
    span = comp_pitches * P                            # lead-to-lead spacing
    leg = leg_len * scale

    # Body: a horizontal cylinder (like a through-hole resistor) lying along X,
    # raised so its underside clears the board and legs reach down.
    body_z = leg + body_r
    comp = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, body_z, 0))    # workplane at x=0; YZ plane
        .circle(body_r)
        .extrude(body_len / 2.0, both=True)
    )
    # Round the two ends into caps so it reads as a component (union hemispheres
    # would need a sphere; instead union short coaxial discs = flat caps, still a
    # single solid). Flat caps are fine and watertight.

    # Lead rib: a solid bar along X at the body centre height spanning leg-to-leg,
    # representing the component's wire leads. It guarantees the two legs and the
    # body are always one connected solid, even when the leads reach beyond the
    # body ends (a real through-hole part has leads longer than its body).
    rib_r = LEG_R
    rib = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, body_z, 0))
        .circle(rib_r)
        .extrude(span / 2.0 + rib_r, both=True)
    )
    result_body = comp.union(rib)

    # Two lead legs: solid vertical pegs from the board up to the rib/body centre.
    for sx in (-span / 2.0, span / 2.0):
        peg = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, 0, -0.01))
            .circle(LEG_R)
            .extrude(body_z + 0.02)                      # up to the lead rib
        )
        result_body = result_body.union(peg)

    return result_body


def build_bus_strip():
    """A power/ground rail: a long bar, one row of holes on the pitch, top groove."""
    thick = bb_thick * scale
    n = bus_holes
    length = (n - 1) * P + 2.0 * P
    width = P * 1.8
    bar = (
        cq.Workplane("XY")
        .box(length, width, thick, centered=(True, True, False))
    )
    try:
        bar = bar.edges("|Z").fillet(min(width * 0.3, 2.0 * scale))
    except Exception:
        pass

    # Top rail groove running the length (open to top → vented) — the painted +/-
    # stripe channel.
    groove = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, thick - min(thick * 0.35, 2.0 * scale)))
        .box(length + 2.0, P * 0.5, min(thick * 0.35, 2.0 * scale) + 0.1, centered=(True, True, False))
    )
    bar = bar.cut(groove)

    # One row of through holes on the pitch.
    x0 = -(n - 1) * P / 2.0
    centers = [(x0 + i * P, 0.0) for i in range(n)]
    holes = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .pushPoints(centers)
        .circle(HOLE_R)
        .extrude(thick + 2.0)
    )
    body = bar.cut(holes)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "component_holder":
    result = build_component_holder()
elif target_part == "bus_strip":
    result = build_bus_strip()
else:
    result = build_breadboard()
