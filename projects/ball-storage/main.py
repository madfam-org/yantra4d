"""
Sports Ball Wall Storage — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall holder that cradles a sports ball (basketball, soccer, volleyball) off the
floor. Sized by the ball diameter so the claw/ring hugs the ball at its equator.
The ball-cradling surface is the shared interface across the variants.

Three parts (dispatched by `target_part`):
  * "claw_holder"   — a back plate with three curved prongs that cup the ball
                      from below (drop the ball into the claw).
  * "ring_holder"   — a simple sloped ring the ball rests in, on a back plate.
  * "double_holder" — a taller plate with two ring cradles stacked for two balls.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `ball_dia`).
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
target_part = str(PARAM(lambda: target_part, "claw_holder"))  # claw|ring|double

ball_dia   = float(PARAM(lambda: ball_dia,  240.0))  # ball diameter (mm) — basketball ≈240
prongs     = int(  PARAM(lambda: prongs,       3))   # number of claw prongs
prong_w    = float(PARAM(lambda: prong_w,    16.0))  # prong width (mm)
prong_t    = float(PARAM(lambda: prong_t,     8.0))  # prong thickness (mm)
wall       = float(PARAM(lambda: wall,        6.0))  # back plate thickness (mm)
plate_w    = float(PARAM(lambda: plate_w,    90.0))  # back plate width (mm)
screw_dia  = float(PARAM(lambda: screw_dia,   5.0))  # wall screw clearance (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
ball_dia  = max(90.0, min(ball_dia, 300.0))
prongs    = max(2, min(prongs, 5))
prong_w   = max(8.0, min(prong_w, 40.0))
prong_t   = max(4.0, min(prong_t, 16.0))
wall      = max(4.0, min(wall, 12.0))
plate_w   = max(50.0, min(plate_w, 160.0))
screw_dia = max(3.5, min(screw_dia, 10.0))

R = ball_dia / 2.0
# The cradle sits a bit below the ball equator so the ball is captured.
cradle_r = R * 0.62      # radius from the wall-face axis to prong tips at contact


# ── Helpers ──────────────────────────────────────────────────────────────────
def back_plate(w, h, t):
    """Vertical wall plate in the XZ face; thickness along +Y into wall (y:0→−t),
    centred in X, base at z=0. Rounded outer vertical corners."""
    plate = (
        cq.Workplane("XY")
        .box(w, t, h, centered=(True, True, False))
        .translate((0, -t / 2.0, 0))
    )
    r = min(6.0, w * 0.15, h * 0.12)
    if r > 0.3:
        try:
            plate = plate.edges("|Z").fillet(r)
        except Exception:
            pass
    return plate


def screw_holes(body, h, t, cx=0.0):
    """Two vertical screw holes through the plate at column cx (bored +Y)."""
    r = screw_dia / 2.0
    inset = max(14.0, screw_dia + 8.0)
    for z in [inset, h - inset]:
        cutter = (
            cq.Workplane("XZ")
            .circle(r)
            .extrude(t + 6.0)
            .translate((cx, 3.0, z))
        )
        body = body.cut(cutter)
    return body


def curved_prong(reach, angle_deg, at_z):
    """One prong that reaches out +Y with an up-turned tip lip to cup the ball.
    The prong root starts a little INSIDE the plate (y=-3) so the union with the
    plate is volumetric (a root at y=0 would coincide with the plate face and
    leave a non-manifold seam). Several fanned prongs form the claw basket."""
    seg = (
        cq.Workplane("XY")
        .box(prong_w, reach + 3.0, prong_t, centered=(True, False, False))
        .translate((0, -3.0, 0))
    )
    # Up-turned tip lip so the ball is captured.
    tip = (
        cq.Workplane("XY")
        .box(prong_w, prong_t, reach * 0.5, centered=(True, False, False))
        .translate((0, reach - prong_t, 0))
    )
    prong = seg.union(tip)
    # Rotate the whole prong about Z so prongs fan out around the ball axis.
    prong = prong.rotate((0, 0, 0), (0, 0, 1), angle_deg)
    prong = prong.translate((0, 0, at_z))
    return prong


def ring_cradle(at_z):
    """A sloped ring the ball rests in, tangent to the plate. A partial cone ring
    (annulus) tilted so its opening faces up-and-out. Returns a solid Workplane."""
    ro = cradle_r + prong_t
    ring = (
        cq.Workplane("XY")
        .circle(ro).circle(cradle_r)
        .extrude(prong_w)
    )
    # Tilt the ring back ~20° so it scoops the ball, then push out from the wall.
    ring = ring.rotate((0, 0, 0), (1, 0, 0), 20.0)
    ring = ring.translate((0, cradle_r * 0.75, at_z))
    return ring


# ── Part builders ────────────────────────────────────────────────────────────
def build_claw_holder():
    """A back plate with `prongs` curved prongs fanning out to cradle the ball."""
    ph = ball_dia * 0.55
    body = back_plate(plate_w, ph, wall)
    reach = cradle_r
    at_z = ph * 0.35
    # Fan the prongs across the lower front. Prongs point generally +Y, splayed.
    if prongs <= 2:
        angles = [-30.0, 30.0]
    elif prongs == 3:
        angles = [-40.0, 0.0, 40.0]
    elif prongs == 4:
        angles = [-50.0, -18.0, 18.0, 50.0]
    else:
        angles = [-55.0, -27.0, 0.0, 27.0, 55.0]
    for ang in angles[:prongs]:
        body = body.union(curved_prong(reach, ang, at_z))
    body = screw_holes(body, ph, wall)
    return body


def build_ring_holder():
    """A back plate with a single sloped ring cradle."""
    ph = ball_dia * 0.5
    body = back_plate(plate_w, ph, wall)
    body = body.union(ring_cradle(ph * 0.3))
    body = screw_holes(body, ph, wall)
    return body


def build_double_holder():
    """A taller plate with two ring cradles stacked for two balls."""
    ph = ball_dia * 1.05
    body = back_plate(plate_w, ph, wall)
    body = body.union(ring_cradle(ph * 0.22))
    body = body.union(ring_cradle(ph * 0.66))
    # Screw holes near top and bottom.
    body = screw_holes(body, ph, wall)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ring_holder":
    result = build_ring_holder()
elif target_part == "double_holder":
    result = build_double_holder()
else:
    result = build_claw_holder()
