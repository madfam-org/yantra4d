"""
Aquarium Fitting — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Rim-mounted hardware for a glass aquarium: a clip that hooks over the tank rim
and cradles a filter hose or lily pipe, a floating/rim feeding ring that keeps
flake food in one spot, and a small clip for a thin glass lily pipe.

  * "hose_holder"    — a J-hook over the tank rim with a C-cradle that grips a
                       hose or return pipe (target_part == "hose_holder").
  * "feeding_ring"   — a ring wall on a flat brim that corrals floating food,
                       with a rim tab to hang it (target_part == "feeding_ring").
  * "lily_pipe_clip" — a slim rim hook with a small C-clip for a glass lily pipe
                       (target_part == "lily_pipe_clip").

Watertight strategy: the rim hook is a solid J-profile extruded to a width; the
hose cradle is a solid C-ring (full ring minus a mouth slot) fused to the hook;
the feeding ring is a solid brim disc plus a ring wall with a central opening
that never perforates sideways. Every result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "hose_holder"))  # hose_holder | feeding_ring | lily_pipe_clip

tube_dia   = float(PARAM(lambda: tube_dia,   16.0))   # hose / pipe outer diameter (mm)
rim_th     = float(PARAM(lambda: rim_th,      8.0))   # tank rim / glass thickness (mm)
hook_depth = float(PARAM(lambda: hook_depth, 22.0))   # how far the hook reaches down the inside
wall       = float(PARAM(lambda: wall,        3.0))   # hook / clip / ring wall
clearance  = float(PARAM(lambda: clearance,   0.4))   # tube + rim slip clearance (per side)
width      = float(PARAM(lambda: width,      14.0))   # hook width (along the rim)
ring_dia   = float(PARAM(lambda: ring_dia,   65.0))   # feeding-ring inner diameter (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_dia   = max(5.0,  min(tube_dia, 40.0))
rim_th     = max(3.0,  min(rim_th, 25.0))
hook_depth = max(10.0, min(hook_depth, 60.0))
wall       = max(2.0,  min(wall, 8.0))
clearance  = max(0.0,  min(clearance, 1.5))
width      = max(8.0,  min(width, 40.0))
ring_dia   = max(30.0, min(ring_dia, 150.0))

RIM_GAP = rim_th + 2.0 * clearance     # slot the rim slides into
BORE_R = tube_dia / 2.0 + clearance    # hose cradle inner radius


# ── Helpers ──────────────────────────────────────────────────────────────────
def rim_hook(inner_drop, w):
    """A J-hook straddling the tank rim: a top bridge, an outer leg (short) and
    an inner leg dropping `inner_drop` down the inside face. Built from an
    extruded closed profile in the YZ plane, extruded along X by width `w`."""
    t = wall
    g = RIM_GAP
    outer_leg = 8.0
    # Profile (Y = across the rim, Z = up). Origin at the top of the outer leg.
    prof = (
        cq.Workplane("YZ")
        .polyline([
            (0.0, 0.0),                       # outer-bottom
            (0.0, outer_leg + t),             # outer-top
            (g + 2.0 * t, outer_leg + t),     # bridge top to inner-outer
            (g + 2.0 * t, outer_leg + t - inner_drop),   # inner leg down (outer face)
            (g + t, outer_leg + t - inner_drop),         # inner leg tip (inner face)
            (g + t, outer_leg),               # back up inside the slot
            (t, outer_leg),                   # slot inner-bottom (over the rim)
            (t, 0.0),                         # outer leg inner face down
        ])
        .close()
        .extrude(w)
    )
    # Center along X.
    return prof.translate((-w / 2.0, 0, 0))


def hose_cradle(w):
    """A C-ring that grips the hose: a full ring minus a mouth slot (< diameter
    so it snaps and retains). Ring axis along X (so the hose runs along the rim
    tangent). Returns the solid centred at origin."""
    outer_r = BORE_R + wall
    ring = cq.Workplane("YZ").circle(outer_r).circle(BORE_R).extrude(w).translate((-w / 2.0, 0, 0))
    mouth = max(2.0, tube_dia * 0.82)
    slot = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, -outer_r, 0))
        .rect(mouth, outer_r * 2.2)
        .extrude(w + 2.0)
        .translate((-w / 2.0 - 1.0, 0, 0))
    )
    return ring.cut(slot)


# ── Part builders ────────────────────────────────────────────────────────────
def build_hose_holder():
    """Rim J-hook with a hose C-cradle hanging on the inside."""
    hook = rim_hook(hook_depth, width)
    # Position a hose cradle on the inner leg, facing into the tank.
    outer_leg = 8.0
    inner_face_y = RIM_GAP + 2.0 * wall
    cradle_z = outer_leg + wall - hook_depth + BORE_R + wall
    cradle = hose_cradle(width).translate(
        (0, inner_face_y + BORE_R + wall, cradle_z)
    )
    # Neck connecting cradle back to the inner leg.
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, inner_face_y, cradle_z))
        .box(width, BORE_R + wall + 2.0, wall * 2.0, centered=(True, False, True))
    )
    body = hook.union(neck).union(cradle)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_lily_pipe_clip():
    """A slimmer rim hook with a small hose cradle for a thin glass lily pipe."""
    w = max(8.0, width * 0.6)
    hook = rim_hook(hook_depth * 0.8, w)
    outer_leg = 8.0
    inner_face_y = RIM_GAP + 2.0 * wall
    cradle_z = outer_leg + wall - hook_depth * 0.8 + BORE_R + wall
    cradle = hose_cradle(w).translate((0, inner_face_y + BORE_R + wall, cradle_z))
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, inner_face_y, cradle_z))
        .box(w, BORE_R + wall + 2.0, wall * 2.0, centered=(True, False, True))
    )
    body = hook.union(neck).union(cradle)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_feeding_ring():
    """A floating/rim food corral: a flat brim disc with a raised ring wall, plus
    a rim hook tab so it can hang on the tank edge instead of floating."""
    ring_r = ring_dia / 2.0
    brim_w = wall + 3.0
    ring_h = 14.0
    # Brim (a flat annular lip that traps flake food from below).
    brim = (
        cq.Workplane("XY")
        .circle(ring_r + brim_w)
        .circle(ring_r)
        .extrude(wall)
    )
    # Ring wall rising from the brim outer edge.
    wall_ring = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall - 0.5))
        .circle(ring_r + brim_w)
        .circle(ring_r + brim_w - wall)
        .extrude(ring_h)
    )
    body = brim.union(wall_ring)
    # A hang lug on the ring wall (a solid ear with a tether hole) so the ring
    # can be tied to the rim instead of drifting. Built as a radial box that
    # starts INSIDE the ring wall (overlap) and reaches outward — a volumetric
    # union, not a tangent kiss.
    wall_out = ring_r + brim_w
    lug = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, wall_out - wall, wall + ring_h * 0.2))
        .box(width, wall * 4.0, ring_h * 0.6, centered=(True, False, False))
    )
    body = body.union(lug)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, wall_out + wall * 2.0, wall + ring_h * 0.45))
        .transformed(rotate=cq.Vector(90, 0, 0))
        .circle(2.2)
        .extrude(wall * 6.0)
    )
    body = body.cut(hole)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "feeding_ring":
    result = build_feeding_ring()
elif target_part == "lily_pipe_clip":
    result = build_lily_pipe_clip()
else:  # "hose_holder"
    result = build_hose_holder()
