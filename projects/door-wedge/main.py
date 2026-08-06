"""
Door / Window Wedge & Stop — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A classic ramp doorstop. Length, width, and height set the ramp angle; an optional
grip texture (shallow ridges) on the underside keeps it from sliding on hard
floors, and an optional finger hole lets it hang on a hook.

  * "wedge"     — the plain ramp (target_part == "wedge").
  * "hook_stop" — a wedge with a raised heel at the tall end so it stops a door
                  harder (the door can't ride up and over it).

Watertight strategy: the ramp is a solid triangular prism (extruded triangle).
Grip ridges are cut as full cross-floor channels (through-cuts stay manifold);
the heel is a solid block unioned on; the finger hole is a full through-bore.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `length`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

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
target_part = str(PARAM(lambda: target_part, "wedge"))  # "wedge" | "hook_stop"

length   = float(PARAM(lambda: length,  120.0))   # ramp run (X)
width    = float(PARAM(lambda: width,    45.0))   # wedge width (Y)
height   = float(PARAM(lambda: height,   35.0))   # tall-end height (Z)
grip     = bool( PARAM(lambda: grip,     True))   # ridged underside
finger_hole = bool(PARAM(lambda: finger_hole, False))  # hang hole near the heel
heel_height = float(PARAM(lambda: heel_height, 22.0))  # raised heel (hook_stop only)

# ── Clamps ───────────────────────────────────────────────────────────────────
length = max(50.0, min(length, 250.0))
width  = max(25.0, min(width, 120.0))
height = max(15.0, min(height, 90.0))
heel_height = max(8.0, min(heel_height, height * 1.5))

# The wedge sits with its ramp rising from the thin (toe) end at x=0 to the tall
# (heel) end at x=length. The triangular cross-section lives in the XZ plane and
# is extruded across the width in Y.


# ── Ramp solid ───────────────────────────────────────────────────────────────
def build_ramp():
    """Extrude the right-triangle profile (toe at x=0, heel at x=length)."""
    tri = (
        cq.Workplane("XZ")
        .moveTo(0.0, 0.0)
        .lineTo(length, 0.0)
        .lineTo(length, height)
        .close()
        .extrude(width)
    )
    # An XZ workplane extrudes along its −Y normal, so the prism lands in
    # Y ∈ [−width, 0]; shift by +width/2 to centre it on the Y axis.
    tri = tri.translate((0, width / 2.0, 0))
    return tri


# ── Grip ridges (shallow channels across the underside) ──────────────────────
def add_grip(body):
    """Cut shallow transverse grooves into the flat bottom face so the wedge
    grips a hard floor. Channels run the full width → clean through-cuts."""
    if not grip:
        return body
    groove_w = 2.0
    rib = 4.0
    depth = 1.2
    step = groove_w + rib
    n = int((length - 10.0) / step)
    if n < 1:
        return body
    cutters = []
    for i in range(1, n + 1):
        x = i * step
        if x > length - 6.0:
            break
        cutters.append(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, -0.5))
            .box(groove_w, width + 2.0, depth + 0.5, centered=(True, True, False))
        )
    if not cutters:
        return body
    cut = cutters[0]
    for c in cutters[1:]:
        cut = cut.union(c)
    return body.cut(cut)


# ── Heel (raised block at the tall end, hook_stop) ───────────────────────────
def add_heel(body):
    """A raised vertical heel at the tall end so a door can't ride over the stop."""
    total_top = height + heel_height
    heel_len = min(14.0, length * 0.15)
    heel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(length - heel_len / 2.0, 0, 0))
        .box(heel_len, width, total_top, centered=(True, True, False))
    )
    body = body.union(heel)
    # Round the top of the heel for looks / safety; non-fatal if degenerate.
    try:
        body = body.edges(">Z").fillet(min(3.0, heel_len / 2.0 - 0.5))
    except Exception:
        pass
    return body


# ── Finger hole (hang the wedge on a hook) ───────────────────────────────────
def add_finger_hole(body):
    """Bore a through-hole near the tall end, high enough to clear the ramp."""
    if not finger_hole:
        return body
    hole_d = min(16.0, width * 0.4, height * 0.5)
    if hole_d < 6.0:
        return body
    # Position near the heel, centred in the material there.
    cx = length - max(hole_d, 14.0)
    cz = height - hole_d / 2.0 - 3.0
    if cz - hole_d / 2.0 < 2.0:
        cz = hole_d / 2.0 + 2.0
    cutter = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(cx, cz, width / 2.0 + 1.0))
        .circle(hole_d / 2.0)
        .extrude(-(width + 2.0))
    )
    return body.cut(cutter)


# ── Build ────────────────────────────────────────────────────────────────────
def build():
    body = build_ramp()
    if target_part == "hook_stop":
        body = add_heel(body)
    body = add_grip(body)
    body = add_finger_hole(body)
    return body


result = build()
