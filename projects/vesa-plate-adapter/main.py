"""
VESA Adapter Plate (75 <-> 100) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The VESA FDMI / MIS-D flat-display mounting interface uses square bolt patterns:
MIS-D 75 is 75 x 75 mm and MIS-D 100 is 100 x 100 mm, both with M4 threads. Many
monitors expose one pattern while the arm/bracket expects the other. This adapter
plate carries two concentric square patterns so a 75 mm display bolts to a 100 mm
arm (or the reverse), growing the `vesa` family.

VESA MIS-D geometry (nominal, dimensionally real):
  - MIS-D 75  bolt square = 75.0 mm, M4  (4.5 mm clearance holes)
  - MIS-D 100 bolt square = 100.0 mm, M4 (4.5 mm clearance holes)
  - M4 screw head / counterbore ~ 8.0 mm; min thread engagement handled by arm.

Watertight strategy:
  The plate is a filleted rounded slab. The two VESA squares are through-holes
  (they vent to both faces, so no trapped voids). A central cable pass-through is
  a single through-bore. Counterbores are open pockets on the outward face (they
  vent to the face). The spacer step (100->75 mode) is a solid boss UNIONED onto
  the slab with overlap, never a hollow post. Fillets are applied to the clean
  blank BEFORE any hole is cut, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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


# ── Parameters (VESA MIS-D 75/100 standard) ──────────────────────────────────
target_part = str(PARAM(lambda: target_part, "adapter_75_to_100"))
# "adapter_75_to_100" | "adapter_100_to_75" | "combo_universal"

plate_t = float(PARAM(lambda: plate_t, 5.0))        # plate thickness (Z)
vesa_small = float(PARAM(lambda: vesa_small, 75.0))  # MIS-D 75 bolt square
vesa_large = float(PARAM(lambda: vesa_large, 100.0))  # MIS-D 100 bolt square
bolt_d = float(PARAM(lambda: bolt_d, 4.5))          # M4 clearance hole dia
cbore_d = float(PARAM(lambda: cbore_d, 8.5))        # M4 head counterbore dia
cbore_depth = float(PARAM(lambda: cbore_depth, 2.5))  # counterbore depth
cable_d = float(PARAM(lambda: cable_d, 30.0))       # central cable pass-through
spacer_h = float(PARAM(lambda: spacer_h, 8.0))      # 100->75 stand-off spacer height
corner_r = float(PARAM(lambda: corner_r, 6.0))      # plate corner radius

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_t = max(3.0, min(plate_t, 12.0))
vesa_small = max(50.0, min(vesa_small, 90.0))
vesa_large = max(95.0, min(vesa_large, 140.0))
bolt_d = max(3.5, min(bolt_d, 7.0))
cbore_d = max(bolt_d + 1.5, min(cbore_d, 14.0))
cbore_depth = max(1.0, min(cbore_depth, plate_t - 1.5))
cable_d = max(0.0, min(cable_d, min(vesa_small, vesa_large) - 12.0))
spacer_h = max(3.0, min(spacer_h, 25.0))
corner_r = max(2.0, min(corner_r, 12.0))


# ── Primitives ───────────────────────────────────────────────────────────────
def _rounded_slab(size, thick, rad):
    """A square slab centred on XY, base at z=0, with filleted vertical edges.
    Fillet the blank BEFORE any feature is cut (fillet on a feature-laden solid
    crashes OCCT clean())."""
    blank = (
        cq.Workplane("XY")
        .box(size, size, thick, centered=(True, True, False))
    )
    try:
        blank = blank.edges("|Z").fillet(min(rad, size / 2.0 - 1.0))
    except Exception:
        pass
    return blank


def _square_bolt_pts(square):
    """The 4 corner points of a VESA bolt square, centred on origin."""
    h = square / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


def _drill_square(body, square, thick, dia, cb_dia, cb_depth):
    """Cut a VESA square of through-holes with open counterbores on the TOP face
    (both vent to outside). `thick` is the local plate thickness at those holes."""
    pts = _square_bolt_pts(square)
    # Through clearance holes (vent to both faces).
    body = (
        body.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts)
        .hole(dia)
    )
    # Open counterbores sunk from the top face.
    if cb_dia > dia and cb_depth > 0:
        body = (
            body.faces(">Z").workplane(centerOption="ProjectedOrigin")
            .pushPoints(pts)
            .cboreHole(dia, cb_dia, cb_depth)
        )
    return body


def _plate_size():
    """Outer plate size — must clear the larger square plus material margin."""
    return max(vesa_small, vesa_large) + 20.0


# ── Part builders ────────────────────────────────────────────────────────────
def build_adapter_75_to_100():
    """Classic conversion plate: a flat slab drilled with BOTH the 75 mm and the
    100 mm VESA squares. Bolt the display's 75 mm pattern and the arm's 100 mm
    pattern on the same plate. Central cable pass-through vents through."""
    size = _plate_size()
    body = _rounded_slab(size, plate_t, corner_r)

    # Central cable pass-through (single through-bore, vented both faces).
    if cable_d > 1.0:
        body = (
            body.faces(">Z").workplane(centerOption="ProjectedOrigin")
            .circle(cable_d / 2.0)
            .cutThruAll()
        )

    # Both VESA squares as through-holes with open counterbores.
    body = _drill_square(body, vesa_small, plate_t, bolt_d, cbore_d, cbore_depth)
    body = _drill_square(body, vesa_large, plate_t, bolt_d, cbore_d, cbore_depth)
    return body


def build_adapter_100_to_75():
    """Reverse adapter with a raised stand-off boss. The slab carries the 100 mm
    square (bolts to the arm). A solid central boss lifts the display off the arm
    and carries the 75 mm square through the boss — clears a recessed monitor
    back. The boss is UNIONED with overlap (solid, no trapped void)."""
    size = _plate_size()
    body = _rounded_slab(size, plate_t, corner_r)

    # Solid stand-off boss on the top face, sized to enclose the 75 mm square.
    boss_size = vesa_small + 16.0
    boss = _rounded_slab(boss_size, spacer_h, corner_r)
    boss = boss.translate((0, 0, plate_t - 0.01))  # overlap into slab, no seam
    body = body.union(boss)

    total_h = plate_t + spacer_h - 0.01

    # 100 mm VESA square through the base slab region only (open counterbore on
    # the bottom face so a flush arm screw seats). Drill from the bottom.
    pts100 = _square_bolt_pts(vesa_large)
    body = (
        body.faces("<Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts100)
        .cboreHole(bolt_d, cbore_d, cbore_depth)
    )

    # 75 mm VESA square straight through the whole stack (boss + slab), vented.
    pts75 = _square_bolt_pts(vesa_small)
    body = (
        body.faces(">Z").workplane(centerOption="ProjectedOrigin")
        .pushPoints(pts75)
        .hole(bolt_d)
    )

    # Central cable pass-through through the whole stack.
    if cable_d > 1.0:
        body = (
            body.faces(">Z").workplane(centerOption="ProjectedOrigin")
            .circle(cable_d / 2.0)
            .cutThruAll()
        )

    _ = total_h  # documents the built height; geometry uses the faces above
    return body


def build_combo_universal():
    """A universal slab carrying the 75 and 100 mm squares as SHORT radial slots
    instead of round holes, so slightly off-spec displays still bolt up. Obround
    slots are more robust than fans-of-circles. Central cable pass-through."""
    size = _plate_size()
    body = _rounded_slab(size, plate_t, corner_r)

    if cable_d > 1.0:
        body = (
            body.faces(">Z").workplane(centerOption="ProjectedOrigin")
            .circle(cable_d / 2.0)
            .cutThruAll()
        )

    # Radial obround slots at each corner of each square (slot runs toward centre
    # so the plate tolerates ±(slot travel) misalignment).
    slot_travel = 6.0
    for square in (vesa_small, vesa_large):
        h = square / 2.0
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            cx, cy = sx * h, sy * h
            # obround oriented along the diagonal toward the centre
            ang = 45.0 if (sx * sy > 0) else 135.0
            slot = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(cx, cy, 0))
                .slot2D(bolt_d + slot_travel, bolt_d, angle=ang)
                .extrude(plate_t + 2.0)
                .translate((0, 0, -1.0))
            )
            body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "adapter_100_to_75":
    result = build_adapter_100_to_75()
elif target_part == "combo_universal":
    result = build_combo_universal()
else:
    result = build_adapter_75_to_100()
