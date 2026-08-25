"""
Compliant Flexure Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A monolithic flexure stage: a single printed part that moves precisely by ELASTIC
BENDING of thin blades instead of sliding joints — no play, no lubrication, no
wear. Flexures give sub-micron-repeatable motion for optics, metrology, and
precision positioning. Every mode here is ONE watertight solid (a compliant
mechanism is inherently monolithic); the thin blade sections are the compliant
elements, sized so they print and flex without severing the body.

It mates the ISO M3 fastener family: mounting holes are M3 clearance (3.4 mm) so
the stage bolts to any M3 pattern.

Modes:
  - flexure_stage : a parallel four-bar (parallelogram) LINEAR flexure — a moving
                    platform suspended on two thin blades from a fixed frame, with
                    M3 holes on both the frame and the platform.
  - notch_flexure : a NOTCH-hinge angular flexure — two arms joined by a thin
                    circular-notch living hinge, an M3 pivot mount, and travel
                    stops.
  - xy_flexure    : a serial XY flexure — two nested parallelogram stages at 90°
                    giving decoupled X and Y motion from one monolithic part.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
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
target_part = str(PARAM(lambda: target_part, "flexure_stage"))
# "flexure_stage" | "notch_flexure" | "xy_flexure"

body_w = float(PARAM(lambda: body_w, 60.0))       # overall footprint width (X)
body_d = float(PARAM(lambda: body_d, 50.0))       # overall footprint depth (Y)
thickness = float(PARAM(lambda: thickness, 10.0)) # part thickness (Z)
blade_t = float(PARAM(lambda: blade_t, 1.2))      # flexure blade thickness (compliance)
frame_w = float(PARAM(lambda: frame_w, 8.0))      # fixed frame / arm width
travel = float(PARAM(lambda: travel, 6.0))        # nominal motion gap
m3_d = float(PARAM(lambda: m3_d, 3.4))            # M3 clearance hole diameter

# ── Clamp to sane ranges ─────────────────────────────────────────────────────
body_w = max(30.0, min(body_w, 120.0))
body_d = max(24.0, min(body_d, 100.0))
thickness = max(5.0, min(thickness, 24.0))
blade_t = max(0.8, min(blade_t, 3.0))
frame_w = max(4.0, min(frame_w, 16.0))
travel = max(2.0, min(travel, 14.0))
m3_d = max(2.5, min(m3_d, 6.0))


def _m3(body, x, y, depth_from=-1.0, depth=None):
    """Cut an M3 clearance hole through Z at (x, y), vented both faces."""
    d = (thickness + 2.0) if depth is None else depth
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, depth_from))
        .circle(m3_d / 2.0)
        .extrude(d)
    )
    return body.cut(hole)


def build_flexure_stage():
    """A parallelogram LINEAR flexure: a fixed frame (bottom bar) and a moving
    platform (top bar) joined by TWO thin vertical blades, so the platform
    translates along X on a parallel four-bar. Cut from a solid blank by removing
    two slots that leave the blades; the whole thing stays one solid body."""
    blank = (
        cq.Workplane("XY")
        .box(body_w, body_d, thickness, centered=(True, True, False))
    )
    body = blank

    # Two slots define the parallelogram: an upper slot (under the platform) and a
    # lower slot (above the frame), leaving two vertical blades at the left/right.
    # Slot dimensions.
    bar_h = frame_w                      # height (Y) of the fixed bar & platform
    blade_span = body_d - 2.0 * bar_h    # vertical distance the blades span
    inner_w = body_w - 2.0 * frame_w     # width between the side columns

    # Left and right vertical blades sit at x = ±(inner_w/2 - blade_t/2), running
    # in Y between the two bars. Remove everything between them EXCEPT the blades:
    # two rectangular pockets (through Z) on either side of centre.
    pocket_w = (inner_w - 2.0 * blade_t) / 2.0 - travel / 2.0
    if pocket_w < 2.0:
        pocket_w = 2.0
    for sx in (-1, 1):
        # outer pockets between each blade and the side column
        cx = sx * (inner_w / 2.0 - blade_t - pocket_w / 2.0)
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0, -1.0))
            .box(pocket_w, blade_span, thickness + 2.0, centered=(True, True, False))
        )
        body = body.cut(pocket)
    # central pocket between the two blades
    central = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(inner_w - 2.0 * blade_t - 2.0 * pocket_w, blade_span,
             thickness + 2.0, centered=(True, True, False))
    )
    body = body.cut(central)

    # M3 holes: two on the fixed frame (bottom bar), two on the moving platform
    # (top bar).
    hy = body_d / 2.0 - bar_h / 2.0
    hx = body_w / 2.0 - frame_w / 2.0
    for sx in (-1, 1):
        body = _m3(body, sx * hx, -hy)   # frame
        body = _m3(body, sx * hx, hy)    # platform
    return body


def build_notch_flexure():
    """A NOTCH-hinge angular flexure: a solid bar split near the middle by two
    facing circular notches that leave a thin neck — the neck bends elastically
    like a hinge. M3 mounts at each end; a slot forms a travel stop. One solid."""
    blank = (
        cq.Workplane("XY")
        .box(body_w, body_d, thickness, centered=(True, True, False))
    )
    try:
        blank = blank.edges("|Z").fillet(3.0)
    except Exception:
        pass
    body = blank

    # Two facing circular notches at centre (cut from +Y and -Y), leaving a neck
    # of width `blade_t` at x=0. Notch radius sized from the gap.
    notch_r = (body_d - blade_t) / 2.0 * 0.7
    for sy in (-1, 1):
        cy = sy * (body_d / 2.0)
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, cy, -1.0))
            .circle(notch_r)
            .extrude(thickness + 2.0)
        )
        body = body.cut(notch)

    # A relief slot beside the neck sets the travel stop (open to +X edge).
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(body_w / 2.0, 0, -1.0))
        .box(travel * 2.0, blade_t + travel, thickness + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    # M3 mounts at both ends.
    hx = body_w / 2.0 - frame_w / 2.0
    for sx in (-1, 1):
        body = _m3(body, sx * hx, 0.0)
    return body


def _slot_ring(body, half_w, half_d, gap, blade, bridge_axis):
    """Cut a rectangular SLOT RING (annular gap) into `body` centred on the origin,
    leaving two opposite blade bridges so the inside stays connected to the
    outside. `half_w`/`half_d` are the ring's centreline half-extents, `gap` the
    slot width, `blade` the bridge width. `bridge_axis` = 'x' keeps bridges on the
    left/right (compliance in Y), 'y' keeps them top/bottom (compliance in X).

    Built as ONE closed sketch region (outer rectangle minus inner rectangle),
    extruded through Z and subtracted — a single boolean, so no coincident-face
    seams. The two bridges are then re-added as solid bars (unioned) with generous
    overlap so the fusion is clean."""
    z0 = -1.0
    h = thickness + 2.0
    ow, od = half_w + gap / 2.0, half_d + gap / 2.0   # outer of the slot
    iw, idd = half_w - gap / 2.0, half_d - gap / 2.0  # inner of the slot
    # slot ring = big rect minus inner rect (a closed frame region)
    ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .rect(2.0 * ow, 2.0 * od)
        .rect(2.0 * iw, 2.0 * idd)
        .extrude(h)   # even-odd → material only between the two rects
    )
    body = body.cut(ring)
    # add the two bridges back (blades) with overlap into inner+outer material
    span = gap + 2.0
    if bridge_axis == "x":
        for sx in (-1, 1):
            bx = sx * ((iw + ow) / 2.0)
            bar = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(bx, 0, z0))
                .box(span, blade, h, centered=(True, True, False))
            )
            body = body.union(bar)
    else:
        for sy in (-1, 1):
            by = sy * ((idd + od) / 2.0)
            bar = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, by, z0))
                .box(blade, span, h, centered=(True, True, False))
            )
            body = body.union(bar)
    return body


def build_xy_flexure():
    """A serial XY flexure: two nested rectangular slot-rings cut from one blank.
    The OUTER ring (bridges top/bottom) lets the middle frame move in X; the INNER
    ring (bridges left/right) lets the platform move in Y — decoupled XY from one
    monolithic solid. Each ring is a single boolean plus clean bridge unions, so
    the body stays watertight and manifold."""
    blank = (
        cq.Workplane("XY")
        .box(body_w, body_d, thickness, centered=(True, True, False))
    )
    try:
        blank = blank.edges("|Z").fillet(3.0)
    except Exception:
        pass
    body = blank
    g = max(1.5, travel * 0.55)

    # Outer ring centreline near the frame; bridges top/bottom → X compliance.
    outer_hw = body_w / 2.0 - frame_w - g
    outer_hd = body_d / 2.0 - frame_w - g
    body = _slot_ring(body, outer_hw, outer_hd, g, blade_t, bridge_axis="y")

    # Inner ring centreline smaller; bridges left/right → Y compliance.
    inner_hw = outer_hw - frame_w - g
    inner_hd = outer_hd - frame_w - g
    if inner_hw > frame_w and inner_hd > frame_w:
        body = _slot_ring(body, inner_hw, inner_hd, g, blade_t, bridge_axis="x")

    # M3: central platform + one frame corner.
    body = _m3(body, 0.0, 0.0)
    body = _m3(body, body_w / 2.0 - frame_w / 2.0, body_d / 2.0 - frame_w / 2.0)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "notch_flexure":
    result = build_notch_flexure()
elif target_part == "xy_flexure":
    result = build_xy_flexure()
else:
    result = build_flexure_stage()
