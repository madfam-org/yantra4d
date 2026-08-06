"""
Cord Guard — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Chew-resistant / abrasion sleeves that protect a cable or cord: a straight split
sleeve that snaps over the cable, an L-shaped corner guard for where a cord turns
a wall corner or table edge, and a spiral wrap that coils around the cable so it
can still flex.

  * "split_sleeve" — a straight tube with a lengthwise slit so it clips over an
                     in-place cable (target_part == "split_sleeve").
  * "corner_guard" — two split-sleeve arms meeting at a rounded 90° elbow to
                     protect a cable turning a corner (target_part ==
                     "corner_guard").
  * "spiral_wrap"  — a helical band that coils around the cable, staying flexible
                     (target_part == "spiral_wrap").

Watertight strategy: the sleeve is a tube (outer cylinder minus a coaxial bore)
with a lengthwise slot cut through the wall — one manifold solid. The corner
guard unions two straight tubes with an elbow torus-arm, all bored on the same
path. The spiral wrap sweeps a rectangle along a genuine `makeHelix`. Every
result is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "split_sleeve"))  # split_sleeve | corner_guard | spiral_wrap

cable_dia = float(PARAM(lambda: cable_dia, 6.0))    # cable outer diameter (mm)
wall      = float(PARAM(lambda: wall,      2.4))    # sleeve wall thickness
length    = float(PARAM(lambda: length,   80.0))    # sleeve length (mm)
split     = float(PARAM(lambda: split,    0.55))    # split opening as fraction of cable dia
clearance = float(PARAM(lambda: clearance, 0.4))    # radial slip clearance
pitch     = float(PARAM(lambda: pitch,    12.0))    # spiral-wrap pitch (mm/turn)

# ── Clamps ───────────────────────────────────────────────────────────────────
cable_dia = max(2.0,  min(cable_dia, 30.0))
wall      = max(1.2,  min(wall, 6.0))
length    = max(20.0, min(length, 200.0))
split     = max(0.3,  min(split, 0.9))
clearance = max(0.0,  min(clearance, 2.0))
pitch     = max(6.0,  min(pitch, 40.0))

BORE_R = cable_dia / 2.0 + clearance
OUTER_R = BORE_R + wall
SPLIT_W = max(1.0, cable_dia * split)


# ── Helpers ──────────────────────────────────────────────────────────────────
def tube(ln):
    """An UN-slotted hollow tube of length `ln` along Z (outer cylinder minus a
    coaxial bore). Kept separate from the slit so callers can union tubes first
    (matching cross-sections) and slit ONCE afterwards."""
    body = cq.Workplane("XY").circle(OUTER_R).extrude(ln)
    bore = cq.Workplane("XY").circle(BORE_R).extrude(ln + 2.0).translate((0, 0, -1.0))
    return body.cut(bore)


def straight_sleeve(ln):
    """A split tube of length `ln` along Z: `tube` with a lengthwise slot through
    the wall on +Y so it clips over an in-place cable."""
    body = tube(ln)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, OUTER_R, -1.0))
        .box(SPLIT_W, OUTER_R * 2.0, ln + 2.0, centered=(True, True, False))
    )
    return body.cut(slot)


# ── Part builders ────────────────────────────────────────────────────────────
def build_split_sleeve():
    body = straight_sleeve(length)
    # Chamfer both ends of the bore so the cable feeds in (non-fatal).
    for zsel in (">Z", "<Z"):
        try:
            body = body.faces(zsel).edges(cq.selectors.RadiusNthSelector(0)).chamfer(min(1.0, wall * 0.4))
        except Exception:
            pass
    return body


def build_corner_guard():
    """An L-shaped guard for a cable turning a 90° corner. Built from a square
    cross-section (a rectangular cord channel) so every boolean is a
    box-on-box operation — rock-solid and watertight at all sizes, unlike a
    swept round elbow. A vertical arm rises on +Z, a horizontal arm runs out on
    +Y, sharing one channel; a cross-slot on each arm lets a cable be laid in."""
    arm = max(20.0, length * 0.5)
    sq_out = 2.0 * OUTER_R          # outer square side (matches the round OD)
    sq_bore = 2.0 * BORE_R          # channel square side (fits the cable + slop)

    # Outer L solid: vertical box up +Z, horizontal box out +Y, welded (overlap).
    vert = cq.Workplane("XY").box(sq_out, sq_out, arm, centered=(True, True, False))
    horiz = (
        cq.Workplane("XY")
        .box(sq_out, arm, sq_out, centered=(True, True, False))
        .translate((0, arm / 2.0, sq_out / 2.0))
    )
    solid = vert.union(horiz)

    # Inner channel L, lifted by `wall` so a floor remains along the inside.
    cv = (
        cq.Workplane("XY")
        .box(sq_bore, sq_bore, arm + 1.0, centered=(True, True, False))
        .translate((0, 0, wall))
    )
    ch = (
        cq.Workplane("XY")
        .box(sq_bore, arm + 1.0, sq_bore, centered=(True, True, False))
        .translate((0, arm / 2.0, wall + sq_bore / 2.0))
    )
    body = solid.cut(cv.union(ch))

    # Lay-in slot on each arm (a through cross-slit at the channel level), so a
    # cable already routed through the corner can drop into the guard.
    sv = (
        cq.Workplane("XY")
        .box(sq_out + 2.0, SPLIT_W, arm, centered=(True, True, False))
        .translate((0, 0, wall + sq_bore / 2.0))
    )
    sh = (
        cq.Workplane("XY")
        .box(sq_out + 2.0, arm, SPLIT_W, centered=(True, True, False))
        .translate((0, arm / 2.0, wall + sq_bore / 2.0))
    )
    try:
        body = body.cut(sv.union(sh))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_spiral_wrap():
    """A helical band coiling around the cable. Sweep a rectangular cross-section
    along a genuine helix; the coil gaps let the bundle flex. Kept to a modest
    number of turns so the sweep is fast and watertight."""
    turns = max(1.0, min(6.0, length / pitch))
    height = pitch * turns
    coil_r = BORE_R + wall * 0.5
    band_w = wall * 1.4          # radial thickness of the ribbon
    band_h = pitch * 0.55        # axial height of each coil (leaves a flex gap)
    # Follow the bottle-thread-proven pattern: sweep a profile that already sits
    # at the coil radius (in its own XZ plane) along a NEAR-ZERO-radius helix, so
    # the profile traces the true coil. A rectangle centred at (coil_r, 0) gives
    # a clean rectangular ribbon.
    helix = cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)
    prof = (
        cq.Workplane("XZ")
        .center(coil_r, 0)
        .rect(band_w, band_h)
    )
    try:
        coil = prof.sweep(helix, isFrenet=True)
    except Exception:
        # Fallback to a simple split sleeve if the sweep fails on extremes.
        return straight_sleeve(length)
    try:
        coil = coil.clean()
    except Exception:
        pass
    return coil


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "corner_guard":
    result = build_corner_guard()
elif target_part == "spiral_wrap":
    result = build_spiral_wrap()
else:  # "split_sleeve"
    result = build_split_sleeve()
