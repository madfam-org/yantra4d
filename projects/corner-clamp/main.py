"""
Corner Assembly Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A 90° clamp that holds two workpieces square while glue or fasteners set. An
L-shaped body registers both faces at a true right angle; a clamp-screw bore
lets a bolt or clamp pull the joint tight. Sized by the material thickness and
width it must hold.

Three modes, dispatched by `target_part`:
  - corner_clamp  : a rigid right-angle jaw with two registration walls and a
                    clamp-screw bore through each leg.
  - band_corner   : an adjustable corner block with a band/strap slot so a strap
                    clamp can wrap four corners of a frame at once.
  - picture_frame : a 45° miter corner cradle that holds two mitered ends against
                    a 90° inside reference for picture frames.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `mat_thick`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
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
mat_thick   = float(PARAM(lambda: mat_thick,   18.0))   # material thickness held
mat_width   = float(PARAM(lambda: mat_width,   60.0))   # material width (leg length)
wall        = float(PARAM(lambda: wall,         6.0))   # clamp body wall thickness
height      = float(PARAM(lambda: height,      40.0))   # clamp height along the joint
screw_bore  = float(PARAM(lambda: screw_bore,   6.5))   # clamp-screw / bolt bore Ø
band_w      = float(PARAM(lambda: band_w,      25.0))   # strap width (band mode)
band_t      = float(PARAM(lambda: band_t,       2.0))   # strap thickness slot (band mode)

target_part = str(PARAM(lambda: target_part, "corner_clamp"))

# The registration pocket must fit the material; body wall wraps outside it.
pocket = mat_thick
leg = max(mat_width, pocket + 2.0 * wall)


# ── Helpers ──────────────────────────────────────────────────────────────────
def prism(w, d, h, cx=True, cy=True):
    """Axis-aligned block, base at z=0."""
    return cq.Workplane("XY").box(w, d, h, centered=(cx, cy, False))


def safe_fillet_z(solid, r):
    """Round vertical edges, clamped and non-fatal."""
    if r <= 0.3:
        return solid
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


def bore_z(dia, depth, at):
    """Vertical cylindrical cutter, tall enough to punch through, positioned at `at`."""
    return (
        cq.Workplane("XY")
        .circle(dia / 2.0)
        .extrude(depth + 2.0)
        .translate((at[0], at[1], -1.0))
    )


def bore_x(dia, length, at):
    """Horizontal (X-axis) cutter for a clamp screw through a leg."""
    return (
        cq.Workplane("YZ")
        .circle(dia / 2.0)
        .extrude(length + 2.0)
        .translate((-1.0, at[1], at[2]))
    )


# ── Corner clamp (rigid right-angle jaw) ─────────────────────────────────────
def build_corner_clamp():
    """Two perpendicular arms forming an L; each arm is a channel that captures
    a board face. A clamp-screw bore runs through the thick heel of each arm."""
    outer = pocket + 2.0 * wall

    # Arm along +X (captures a board lying along X).
    arm_x = prism(leg, outer, height, cx=False, cy=True)
    # Arm along +Y (captures a board lying along Y).
    arm_y = prism(outer, leg, height, cx=True, cy=False)
    body = arm_x.union(arm_y)
    body = safe_fillet_z(body, min(wall * 0.6, 3.0))

    # Capture channels: cut the material pocket from each arm, leaving a back wall
    # and floor so the boards register against an inside corner.
    # Pocket for X arm: open toward +Y face, floor of `wall`, back wall at inside.
    poc_x = prism(leg + 1.0, pocket, height + 2.0, cx=False, cy=True)
    poc_x = poc_x.translate((wall, wall / 2.0 + pocket / 2.0 + 0.0, -1.0))
    body = body.cut(poc_x)

    poc_y = prism(pocket, leg + 1.0, height + 2.0, cx=True, cy=False)
    poc_y = poc_y.translate((wall / 2.0 + pocket / 2.0, wall, -1.0))
    body = body.cut(poc_y)

    # Clamp-screw bores through the heel of each arm (pull the joint tight).
    body = body.cut(bore_x(screw_bore, outer, (0.0, leg * 0.6, height / 2.0)))
    bore_y = (
        cq.Workplane("XZ")
        .circle(screw_bore / 2.0)
        .extrude(outer + 2.0)
        .translate((leg * 0.6, 1.0, height / 2.0))
    )
    body = body.cut(bore_y)
    return body


# ── Band corner (strap-clamp corner block) ───────────────────────────────────
def build_band_corner():
    """A 90° outside corner block a strap clamp wraps around. The strap seats in
    a slot around the outer faces so it pulls four frame corners in evenly."""
    outer = pocket + 2.0 * wall
    arm_x = prism(leg, outer, height, cx=False, cy=True)
    arm_y = prism(outer, leg, height, cx=True, cy=False)
    body = arm_x.union(arm_y)
    body = safe_fillet_z(body, min(wall * 0.5, 2.5))

    # Inside corner pocket captures the frame stock (both boards meet here).
    poc_x = prism(leg + 1.0, pocket, height + 2.0, cx=False, cy=True)
    poc_x = poc_x.translate((wall, wall / 2.0 + pocket / 2.0, -1.0))
    body = body.cut(poc_x)
    poc_y = prism(pocket, leg + 1.0, height + 2.0, cx=True, cy=False)
    poc_y = poc_y.translate((wall / 2.0 + pocket / 2.0, wall, -1.0))
    body = body.cut(poc_y)

    # Strap slot around the two OUTER faces (the -X face of arm_y, -Y face of arm_x)
    # cut as shallow channels at mid-height so a strap wraps the outside corner.
    z0 = height / 2.0 - band_w / 2.0
    slot_x = prism(leg + 1.0, band_t, band_w, cx=False, cy=True).translate(
        (wall, -outer / 2.0 + band_t / 2.0, z0)
    )
    body = body.cut(slot_x)
    slot_y = prism(band_t, leg + 1.0, band_w, cx=True, cy=False).translate(
        (-outer / 2.0 + band_t / 2.0, wall, z0)
    )
    body = body.cut(slot_y)
    return body


# ── Picture-frame miter corner ───────────────────────────────────────────────
def build_picture_frame():
    """A cradle holding two 45° mitered ends against a true 90° inside reference.
    The two arms meet at a diagonal miter line; a clamp-screw bore crosses the
    diagonal to pull the mitered joint closed."""
    outer = pocket + 2.0 * wall
    arm_x = prism(leg, outer, height, cx=False, cy=True)
    arm_y = prism(outer, leg, height, cx=True, cy=False)
    body = arm_x.union(arm_y)

    # Register pockets (as corner clamp) so both frame legs seat square.
    poc_x = prism(leg + 1.0, pocket, height + 2.0, cx=False, cy=True)
    poc_x = poc_x.translate((wall, wall / 2.0 + pocket / 2.0, -1.0))
    body = body.cut(poc_x)
    poc_y = prism(pocket, leg + 1.0, height + 2.0, cx=True, cy=False)
    poc_y = poc_y.translate((wall / 2.0 + pocket / 2.0, wall, -1.0))
    body = body.cut(poc_y)

    # Diagonal relief slot along the 45° miter line so the mitered ends butt
    # cleanly and any glue squeeze-out has somewhere to go.
    diag = leg * 1.6
    slot = (
        cq.Workplane("XY")
        .box(diag, 1.6, height + 2.0, centered=(True, True, False))
        .rotate((0, 0, 0), (0, 0, 1), 45.0)
        .translate((leg * 0.5, leg * 0.5, -1.0))
    )
    body = body.cut(slot)

    # Clamp-screw bore crossing the diagonal (pulls the miter together).
    screw = (
        cq.Workplane("XY")
        .circle(screw_bore / 2.0)
        .extrude(diag)
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
        .rotate((0, 0, 0), (0, 0, 1), 45.0)
        .translate((leg * 0.5 - diag * 0.354, leg * 0.5 - diag * 0.354, height / 2.0))
    )
    body = body.cut(screw)
    return safe_fillet_z(body, min(wall * 0.4, 2.0))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "band_corner":
    result = build_band_corner()
elif target_part == "picture_frame":
    result = build_picture_frame()
else:
    result = build_corner_clamp()
