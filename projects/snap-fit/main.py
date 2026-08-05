"""
Snap-Fit Cantilever Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Reusable snap-fit connectors: a cantilever beam whose hooked end deflects to snap
over a mating ledge, plus the catch that receives it. The kit ships BOTH halves so
they actually mate — print one of each and clip them together.

Three parts (dispatched via `target_part`):
  * "cantilever_pair" — a classic cantilever hook on a base, AND the catch block
                        with a window/ledge the hook grabs, side by side.
  * "annular_snap"    — a ring snap: a shaft with a raised annular bead near the
                        tip, AND a bore piece with a matching internal groove.
  * "test_clip"       — a small single-hook demonstrator to tune deflection/fit.

The undercut hook is built as a 2D profile extruded across the beam width, which
keeps the snapping face a clean planar undercut (watertight, printable).

Snap deflection force depends on material — the geometry here fixes the stiffness
(beam length/thickness) and the engagement (hook depth); the force does not.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `beam_len`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cantilever_pair"))
if target_part not in ("cantilever_pair", "annular_snap", "test_clip"):
    target_part = "cantilever_pair"

snap_type = str(PARAM(lambda: snap_type, "cantilever"))  # cantilever|annular|ball_detent
if snap_type not in ("cantilever", "annular", "ball_detent"):
    snap_type = "cantilever"

beam_len = float(PARAM(lambda: beam_len, 20.0))          # free length of the cantilever
beam_thick = float(PARAM(lambda: beam_thick, 3.0))       # beam thickness at the root
beam_width = float(PARAM(lambda: beam_width, 8.0))       # beam width (across)
hook_depth = float(PARAM(lambda: hook_depth, 1.8))       # undercut / engagement depth
insert_angle = float(PARAM(lambda: insert_angle, 35.0))  # lead-in ramp angle (insertion)
clearance = float(PARAM(lambda: clearance, 0.3))         # printed fit gap hook↔ledge
bore_dia = float(PARAM(lambda: bore_dia, 16.0))          # annular: shaft/bore nominal diameter
wall = float(PARAM(lambda: wall, 3.0))                   # base / catch / bore wall thickness

# Clamp to safe, watertight ranges.
beam_len = max(6.0, beam_len)
beam_thick = max(1.2, beam_thick)
beam_width = max(3.0, beam_width)
hook_depth = max(0.4, min(hook_depth, beam_thick * 1.5))
insert_angle = max(10.0, min(insert_angle, 60.0))
clearance = max(0.05, min(clearance, 1.0))
wall = max(1.5, wall)
bore_dia = max(6.0, bore_dia)


# ── Cantilever hook profile ──────────────────────────────────────────────────
def hook_profile_points():
    """2D profile of a cantilever beam + hook, in the X(length)–Z(height) plane,
    beam root at the origin growing along +X. The hook sits at the free end (+X),
    projecting in +Z with an undercut catch face and an angled lead-in ramp.

    Returned as a closed CCW polygon (list of (x, z))."""
    lx = beam_len
    tz = beam_thick
    hd = hook_depth
    # Lead-in ramp horizontal run from the insertion angle.
    ramp = hd / max(0.2, math.tan(math.radians(insert_angle)))
    ramp = min(ramp, lx * 0.6)
    tip = lx + ramp
    # Walk the outline counter-clockwise:
    #  bottom edge  → ramp up to hook tip → hook top → undercut back down → top edge back
    pts = [
        (0.0, 0.0),          # root, bottom
        (tip, 0.0),          # far bottom (under the ramp)
        (tip, hd),           # hook outer tip height (ramp apex projected)
        (lx, hd + tz),       # top of the hook (its full height above the beam)
        (lx, tz),            # undercut catch face steps back to beam top
        (0.0, tz),           # back along the beam top to the root
    ]
    return pts


def cantilever_beam():
    """Solid cantilever beam + engagement feature, root at origin, extruded across
    width in Y (centred). Points along +X.

    For a `cantilever` (or `annular` routed elsewhere) snap the tip is a hooked
    undercut; for a `ball_detent` the tip carries a rounded bump that snaps into a
    matching dimple (a gentler, repeatable detent)."""
    if snap_type == "ball_detent":
        # Straight beam bar, then a spherical detent bump on top near the tip.
        bar = (
            cq.Workplane("XZ")
            .polyline([(0.0, 0.0), (beam_len, 0.0), (beam_len, beam_thick), (0.0, beam_thick)])
            .close()
            .extrude(beam_width)
            .translate((0, beam_width / 2.0, 0))
        )
        # A short cylindrical detent stub, chamfered to a dome, that OVERLAPS down
        # into the bar (no tangent-sphere sliver → stays watertight).
        bump_r = min(hook_depth + beam_thick * 0.4, beam_width * 0.45)
        bump_h = hook_depth + 1.0
        overlap = min(1.0, beam_thick * 0.5)
        bump = (
            cq.Workplane("XY")
            .workplane(offset=beam_thick - overlap)
            .center(beam_len - bump_r - 1.0, 0)
            .circle(bump_r)
            .extrude(bump_h + overlap)
        )
        try:
            bump = bump.edges(">Z").chamfer(min(bump_r * 0.6, bump_h * 0.9))
        except Exception:
            pass  # chamfer is cosmetic; never fatal
        return bar.union(bump)

    prof = hook_profile_points()
    beam = (
        cq.Workplane("XZ")
        .polyline(prof)
        .close()
        .extrude(beam_width)
    )
    # extrude on XZ pushes into -Y; recentre the width on Y=0.
    beam = beam.translate((0, beam_width / 2.0, 0))
    return beam


def catch_block():
    """The mating catch: a wall with a rectangular window/ledge the hook grabs.
    Positioned so the hook (built pointing +X) would engage its far face.

    Built as its own solid centred so its engagement face is at x≈beam_len."""
    tz = beam_thick
    hd = hook_depth
    # A catch wall standing in the Y-Z plane at the hook's engagement location.
    cw_thick = max(wall, hd + 1.5)                 # wall thick enough to host the ledge
    cw_h = tz + hd + tz + 4.0                       # tall enough to cover hook travel
    cw_w = beam_width + 2.0 * clearance + 2.0 * wall
    # Solid wall block.
    block = (
        cq.Workplane("XY")
        .box(cw_thick, cw_w, cw_h, centered=(True, True, False))
    )
    # Cut the window the hook passes through and latches behind. The window is as
    # wide as the beam + clearance, and tall enough for the beam thickness; the
    # ledge is the material ABOVE the window that the hook's undercut catches.
    win_w = beam_width + 2.0 * clearance
    win_h = tz + clearance
    window = (
        cq.Workplane("XY")
        .box(cw_thick + 2.0, win_w, win_h, centered=(True, True, False))
        .translate((0, 0, win_h / 2.0 + wall * 0.0))
    )
    # Position window vertically so its floor is at the beam bottom (z=0) region.
    window = window.translate((0, 0, 0.0))
    block = block.cut(window)
    return block


def build_cantilever_pair():
    """Hook on a base + the catch block, laid out side by side to show the fit."""
    tz = beam_thick
    # Base pad the beam roots on (so the printed part stands and has a root fillet).
    base_h = max(wall, tz)
    base_len = max(6.0, beam_len * 0.35)
    base = (
        cq.Workplane("XY")
        .box(base_len, beam_width + 2.0 * wall, base_h, centered=(True, True, False))
        .translate((-base_len / 2.0, 0, 0))
    )
    # Overlap the beam root INTO the base (share volume, not just a face) so the
    # union is a single watertight solid.
    beam = cantilever_beam().translate((0, 0, base_h - min(0.8, base_h * 0.5)))
    hook_side = base.union(beam)

    catch = catch_block()
    # Place the catch to the +X of the hook, at the engagement height.
    catch = catch.translate((beam_len + hook_depth + clearance + 2.0, 0, base_h))

    # Separate the two halves in Y so they print as distinct bodies but read as a
    # matched pair in the viewer.
    hook_side = hook_side.translate((0, -(beam_width + wall + 6.0), 0))
    catch = catch.translate((0, (beam_width + wall + 6.0), 0))
    return hook_side.union(catch)


def build_test_clip():
    """A compact single-hook demonstrator: a base pad + one cantilever hook."""
    tz = beam_thick
    base_h = max(wall, tz)
    base_len = max(5.0, beam_len * 0.3)
    base = (
        cq.Workplane("XY")
        .box(base_len, beam_width + 2.0 * wall, base_h, centered=(True, True, False))
        .translate((-base_len / 2.0, 0, 0))
    )
    # Overlap the beam root into the base for a watertight single-body union.
    beam = cantilever_beam().translate((0, 0, base_h - min(0.8, base_h * 0.5)))
    return base.union(beam)


# ── Annular snap ─────────────────────────────────────────────────────────────
def build_annular_snap():
    """A ring snap: a solid shaft with a raised annular bead near its tip, AND a
    bore piece (a tube) with a matching internal groove the bead seats into. Both
    laid out side by side."""
    shaft_len = beam_len
    shaft_r = bore_dia / 2.0 - clearance          # slip fit into the bore
    shaft_r = max(2.0, shaft_r)
    bead_h = hook_depth                            # radial bead projection
    bead_w = max(1.5, beam_thick)                  # axial bead length
    bead_z = shaft_len - bead_w - 2.0              # bead sits near the tip

    # Shaft with a lead-in chamfer at the tip and the annular bead.
    shaft = cq.Workplane("XY").circle(shaft_r).extrude(shaft_len)
    bead = (
        cq.Workplane("XY")
        .workplane(offset=bead_z)
        .circle(shaft_r + bead_h)
        .extrude(bead_w)
    )
    shaft = shaft.union(bead)
    # Tip lead-in chamfer so it starts into the bore.
    try:
        shaft = shaft.edges(">Z").chamfer(min(bead_h, shaft_r * 0.4))
    except Exception:
        pass
    # A relief slot down the shaft lets a solid print flex (optional, keeps it a
    # real snap not a press fit). A single slot keeps it watertight and simple.
    slot_w = max(1.2, shaft_r * 0.5)
    slot = (
        cq.Workplane("XY")
        .box(slot_w, shaft_r * 2.4, shaft_len * 0.7, centered=(True, True, False))
        .translate((0, 0, shaft_len * 0.3 + 0.001))
    )
    shaft = shaft.cut(slot)

    # Bore piece: an outer tube with an internal groove matching the bead.
    bore_r = bore_dia / 2.0
    outer_r = bore_r + wall
    tube_len = shaft_len
    tube = cq.Workplane("XY").circle(outer_r).extrude(tube_len)
    hole = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(tube_len + 2.0)
        .translate((0, 0, -1.0))
    )
    tube = tube.cut(hole)
    # Internal groove (a wider annular relief) at the depth the bead lands.
    groove = (
        cq.Workplane("XY")
        .workplane(offset=bead_z - clearance)
        .circle(bore_r + bead_h + clearance)
        .circle(bore_r)
        .extrude(bead_w + 2.0 * clearance)
    )
    tube = tube.cut(groove)
    # Lead-in chamfer at the bore mouth.
    try:
        tube = tube.edges(">Z").chamfer(min(bead_h, wall * 0.6))
    except Exception:
        pass

    gap = outer_r + shaft_r + 8.0
    shaft = shaft.translate((-gap, 0, 0))
    tube = tube.translate((gap, 0, 0))
    return shaft.union(tube)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "annular_snap" or snap_type == "annular":
    result = build_annular_snap()
elif target_part == "test_clip":
    result = build_test_clip()
else:
    result = build_cantilever_pair()
