"""
Ratchet & Pawl — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A one-way motion mechanism: a sawtooth ratchet WHEEL plus a pivoting PAWL arm that
drops into the teeth so the wheel turns freely one way and locks the other. Used in
winches, tensioners, indexing tables, and hand tools. The tooth flank asymmetry
(`rake_angle`) sets how firmly it locks versus how easily it ratchets over.

Interface (Ratchet Sawtooth, `spline`, internal):
  The engaging profile is defined by `teeth` (count around the rim) and
  `rake_angle` (the ramped-face lean of the asymmetric sawtooth). The pawl tip is
  sized from the same tooth pitch so any pawl built for a given `teeth`/diameter
  seats in the matching wheel.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `teeth`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
outer_dia   = float(PARAM(lambda: outer_dia,  50.0))   # ratchet outer diameter (tooth tips, mm)
teeth       = int(  PARAM(lambda: teeth,         16))   # number of sawtooth teeth
rake_angle  = float(PARAM(lambda: rake_angle, 20.0))   # ramped-face lean of the sawtooth (deg)
thickness   = float(PARAM(lambda: thickness,   6.0))   # part thickness (Z, mm)
bore        = float(PARAM(lambda: bore,        8.0))   # center bore diameter (mm)
tooth_depth = float(PARAM(lambda: tooth_depth, 4.0))   # radial tooth height (mm)
pawl_length = float(PARAM(lambda: pawl_length, 40.0))  # pawl arm length (mm)

target_part = str(PARAM(lambda: target_part, "ratchet"))  # ratchet | pawl | assembly

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
outer_dia = max(16.0, min(outer_dia, 200.0))
teeth = max(6, min(teeth, 72))
rake_angle = max(0.0, min(rake_angle, 45.0))
thickness = max(2.0, min(thickness, 30.0))
tooth_depth = max(1.0, min(tooth_depth, outer_dia * 0.2))
bore = max(2.0, min(bore, outer_dia - 2.0 * tooth_depth - 4.0))
pawl_length = max(outer_dia * 0.5, min(pawl_length, 250.0))

R_tip = outer_dia / 2.0            # tooth tip radius
R_root = R_tip - tooth_depth       # tooth root radius
tooth_pitch = 2.0 * math.pi / teeth  # angular pitch (radians)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _polar(r, a):
    """(x, y) at radius r, angle a (radians)."""
    return (r * math.cos(a), r * math.sin(a))


def build_ratchet():
    """Sawtooth wheel: a closed polyline traces asymmetric teeth around the rim,
    extruded to `thickness`, then the center bore is drilled.

    Each tooth spans one angular pitch: a long ramped rise from root to tip, then a
    (near-)radial steep drop back to root. `rake_angle` leans the steep face so the
    pawl locks against it; a bigger rake makes a more aggressive, harder-locking
    catch. The polyline is CCW and closed, so the extrude is a clean watertight
    solid."""
    # Fraction of the pitch used by the steep locking face (the rest is the ramp).
    # rake_angle leans the steep face away from radial, widening its footprint.
    steep_frac = min(0.45, 0.15 + math.tan(math.radians(rake_angle)) * 0.35)
    # Emit root_0, tip_0, root_1, tip_1, ... tip_{n-1} with NO trailing root
    # (root_n == root_0); `.close()` connects tip_{n-1} back to root_0 as the last
    # steep face. Sharing/duplicating the boundary root vertex would create a
    # zero-length segment that breaks the wire, so each vertex appears once.
    pts = [_polar(R_root, 0.0)]
    for i in range(teeth):
        a0 = i * tooth_pitch
        a_tip = a0 + tooth_pitch * (1.0 - steep_frac)  # ramp reaches tip here
        a1 = a0 + tooth_pitch                          # next root
        pts.append(_polar(R_tip, a_tip))               # ramp: root -> tip
        if i < teeth - 1:
            pts.append(_polar(R_root, a1))             # steep drop tip -> next root

    wheel = cq.Workplane("XY").polyline(pts).close().extrude(thickness)

    # Center bore.
    hole = cq.Workplane("XY").circle(bore / 2.0).extrude(thickness + 2.0).translate((0, 0, -1.0))
    wheel = wheel.cut(hole)

    # A shallow hub face-chamfer on the bore top for a cleaner print/entry.
    try:
        wheel = wheel.faces(">Z").edges(cq.NearestToPointSelector((0, 0, thickness))).chamfer(0.6)
    except Exception:
        pass
    try:
        wheel = wheel.clean()
    except Exception:
        pass
    return wheel


def build_pawl(origin=(0.0, 0.0), z0=0.0):
    """Pivoting arm: a rounded bar with a pivot hole at the tail, a tooth-engaging
    tip (a small angled nose) at the head, and a small spring tab off the side that
    a torsion element or elastic band can push on to keep the nose engaged."""
    ox, oy = origin
    arm_w = max(6.0, tooth_depth * 2.0)
    pivot_r = max(2.0, bore * 0.35)

    # Main arm as a rounded rectangle from tail (pivot) to head (nose).
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(ox + pawl_length / 2.0, oy, z0))
        .box(pawl_length, arm_w, thickness, centered=(True, True, False))
    )
    try:
        arm = arm.edges("|Z").fillet(min(arm_w * 0.45, pawl_length * 0.1))
    except Exception:
        pass

    # Engaging nose at the head (+X end): a wedge matching the steep tooth face.
    nose_len = max(3.0, tooth_depth * 1.2)
    nose = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(ox + pawl_length, oy, z0))
        .polyline([
            (0, arm_w * 0.5),
            (nose_len, arm_w * 0.15),
            (nose_len, -arm_w * 0.15),
            (0, -arm_w * 0.5),
        ])
        .close()
        .extrude(thickness)
    )
    arm = arm.union(nose)

    # Spring tab off the −Y side, midway along the arm.
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(ox + pawl_length * 0.55, oy - arm_w * 0.5 - 3.0, z0))
        .box(6.0, 8.0, thickness, centered=(True, True, False))
    )
    arm = arm.union(tab)

    # Pivot hole at the tail (near origin).
    pivot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(ox + arm_w * 0.6, oy, z0 - 1.0))
        .circle(pivot_r)
        .extrude(thickness + 2.0)
    )
    arm = arm.cut(pivot)
    try:
        arm = arm.clean()
    except Exception:
        pass
    return arm


def build_assembly():
    """Ratchet + pawl positioned as they would sit in service: the pawl pivot is
    placed just outside the wheel so its nose rests on the tooth tips. Returned as a
    single fused solid (not a live joint) for preview/print-in-place staging."""
    wheel = build_ratchet()

    # Pivot location: out past the tip radius on the +X side, nose reaching in.
    pivot_x = R_tip + 6.0
    pivot_y = -R_tip * 0.55
    # Build the pawl along −X so its nose (built at +X end) points back at the wheel.
    pawl = build_pawl(origin=(pivot_x, pivot_y), z0=0.0)
    # Rotate the pawl about its pivot so the nose swings toward the rim.
    pawl = pawl.rotate((pivot_x, pivot_y, 0), (pivot_x, pivot_y, 1), 155.0)

    asm = wheel.union(pawl)
    try:
        asm = asm.clean()
    except Exception:
        pass
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pawl":
    result = build_pawl()
elif target_part == "assembly":
    result = build_assembly()
else:
    result = build_ratchet()
