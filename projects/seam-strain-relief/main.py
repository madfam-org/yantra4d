"""Seam Strain Relief — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An e-textile garment finding: two flat plates that sandwich a cable where it exits a
garment seam, so tugging the cable loads the seam allowance and the stitch line instead
of the solder joint or the conductive-thread transition inside the garment. Each plate
carries a half-round cable groove and a ring of perimeter sew holes; sewn face to face
through the seam allowance they clamp the jacket without crushing the conductors.

Distinct from the building/appliance-scale `strain-relief` cartridge (panel-mounted bend
limiters for plugs and enclosures) and from `cord-guard` (abrasion sleeves): this one is
stitched into cloth and is sized by seam-allowance width, not by a panel bore.

Modes (dispatched via `target_part`):
  * "plate_pair" — top and bottom plate laid out side by side, ready to sew.
  * "plate"      — a single plate (both plates are identical mirror-symmetric halves).
  * "set"        — the pair plus a strain-relief tail sleeve for the cable run beyond
                   the seam, all on one plate layout.

Geometry: each plate is a rounded-rect slab (rounded via `.edges("|Z").fillet()` on the
CLEAN blank, before any cut). The cable groove is a cylinder laid along X and cut, with
the cylinder overshooting both plate ends so no coincident faces survive. Sew holes are
one `pushPoints(...).circle(...).cutThruAll()`. The tail sleeve is a tube with a
lengthwise relief slot; it is a separate body in the `set` layout, never a tangent union.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cable_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
cable_dia   = float(PARAM(lambda: cable_dia,   4.0))   # cable jacket outside diameter (mm)
plate_len   = float(PARAM(lambda: plate_len,   26.0))  # plate length along the cable (mm)
plate_w     = float(PARAM(lambda: plate_w,     14.0))  # plate width across the seam (mm)
plate_t     = float(PARAM(lambda: plate_t,     2.2))   # plate thickness (mm)
grip        = float(PARAM(lambda: grip,        0.35))  # groove squeeze on the jacket (mm)
sew_holes   = int(  PARAM(lambda: sew_holes,   6))     # perimeter stitch holes per plate
hole_dia    = float(PARAM(lambda: hole_dia,    1.6))   # stitch hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "plate_pair"))  # plate_pair|plate|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
cable_dia = max(1.5, min(cable_dia, 10.0))
plate_t   = max(1.4, min(plate_t, 5.0))
plate_len = max(12.0, min(plate_len, 60.0))
# The plate must be wide enough for the groove plus a stitch lane on each side.
plate_w   = max(cable_dia + 8.0, min(plate_w, 40.0))
grip      = max(0.0, min(grip, 0.8))
sew_holes = max(4, min(sew_holes, 12))
hole_dia  = max(1.0, min(hole_dia, 2.5))

# Groove: a half-round trough on the mating face, slightly under the jacket OD so the
# two plates pinch it. Never deeper than half the plate, or the plate would part.
groove_r = max(0.5, (cable_dia - grip) / 2.0)
groove_depth = min(groove_r, plate_t - 0.8)
corner_r = min(plate_w / 4.0, plate_len / 4.0, 3.0)

# Stitch lane: holes ride a rectangular ring inset from the plate edge, outboard of the
# groove so a needle never breaks into the cable channel.
inset = max(hole_dia * 0.9 + 0.8, 2.0)
lane_y = plate_w / 2.0 - inset
lane_x = plate_len / 2.0 - inset
# Keep the lane clear of the groove wall.
lane_y = max(lane_y, groove_r + hole_dia / 2.0 + 1.0)
lane_y = min(lane_y, plate_w / 2.0 - hole_dia / 2.0 - 0.8)

# Tail sleeve: a short tube the cable runs into past the seam, slotted so it flexes.
sleeve_id = cable_dia + 0.4
sleeve_wall = max(0.9, min(plate_t * 0.6, 1.8))
sleeve_len = max(10.0, plate_len * 0.75)


def _plate_blank():
    """Clean rounded-rect slab on Z=0 — chamfer/fillet happens HERE, before any cut."""
    return (
        cq.Workplane("XY")
        .rect(plate_len, plate_w)
        .extrude(plate_t)
        .edges("|Z")
        .fillet(corner_r)
    )


def _sew_points():
    """Stitch-hole centres on a rectangular lane: split evenly between the two sides."""
    per_side = max(2, sew_holes // 2)
    span = 2.0 * lane_x
    pts = []
    for i in range(per_side):
        t = (i + 0.5) / per_side
        x = -lane_x + span * t
        pts.append((x, lane_y))
        pts.append((x, -lane_y))
    return pts


def build_plate():
    """One clamp plate: rounded slab, half-round cable groove, perimeter sew holes."""
    body = _plate_blank()

    # Cable groove: a cylinder along X, centred on the plate's top (mating) face, cut so
    # the trough is exactly groove_depth deep. Overshoot both ends of the plate.
    cyl_z = plate_t - groove_depth + groove_r
    groove = (
        cq.Workplane("YZ")
        .circle(groove_r)
        .extrude(plate_len + 8.0)
        .translate((-(plate_len + 8.0) / 2.0, 0.0, cyl_z))
    )
    body = body.cut(groove)

    # Sew holes: a single cutThruAll from the bottom face so the groove cut above does
    # not steer the workplane. Cut clean through both faces.
    body = (
        body.faces("<Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(x, -y) for (x, y) in _sew_points()])
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )
    return body


def build_sleeve():
    """A slotted tail tube: the cable's flexible run past the seam clamp."""
    outer = (
        cq.Workplane("XY")
        .circle(sleeve_id / 2.0 + sleeve_wall)
        .extrude(sleeve_len)
    )
    bore = (
        cq.Workplane("XY")
        .circle(sleeve_id / 2.0)
        .extrude(sleeve_len + 4.0)
        .translate((0, 0, -2.0))
    )
    tube = outer.cut(bore)
    # Lengthwise relief slot: opens the tube so it snaps over an installed cable and
    # so nothing seals a void. Oversized in every direction; overshoots both ends.
    slot_w = max(0.8, sleeve_id * 0.35)
    slot = (
        cq.Workplane("XY")
        .box(sleeve_id + 2.0 * sleeve_wall + 4.0, slot_w, sleeve_len + 6.0)
        .translate(((sleeve_id + 2.0 * sleeve_wall + 4.0) / 2.0, 0.0, sleeve_len / 2.0))
    )
    return tube.cut(slot)


def _lay(a, b, gap):
    """Two solids side by side along Y as one compound — never a tangent union."""
    return cq.Workplane(obj=cq.Compound.makeCompound([
        a.val().moved(cq.Location(cq.Vector(0, -gap / 2.0, 0))),
        b.val().moved(cq.Location(cq.Vector(0, gap / 2.0, 0))),
    ]))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "plate":
    result = build_plate()
elif target_part == "set":
    _gap = plate_w + max(4.0, plate_w * 0.25)
    _pair = _lay(build_plate(), build_plate(), _gap)
    # Sleeve laid on its side, clear of both plates in +X.
    _sleeve = (
        build_sleeve()
        .rotate((0, 0, 0), (0, 1, 0), 90)
        .translate((plate_len / 2.0 + 6.0 + sleeve_len / 2.0, 0.0, sleeve_id / 2.0 + sleeve_wall))
    )
    result = cq.Workplane(obj=cq.Compound.makeCompound(
        list(_pair.vals()) + list(_sleeve.vals())
    ))
else:
    _gap = plate_w + max(4.0, plate_w * 0.25)
    result = _lay(build_plate(), build_plate(), _gap)
