"""Bottle Bracket — Shampoo / Pump-Bottle Wall Bracket (Yantra4D Hyperobject).

Shower-shelf brackets and pump-bottle holders sized to REAL bottle bodies:
shampoo / conditioner bottles (~55-90 mm across the body) and pump-dispenser
bottles (~50-75 mm). Three distinct socket/rail modes:

  * shelf_ring — a wall shelf with one or more ring cutouts a bottle drops into
    (upright, or inverted to drain the last of it). Screw mounts anchor the back.
  * neck_hook  — a wall plate with a keyhole that grips a pump bottle UNDER its
    neck collar, so the bottle hangs nozzle-down.
  * body_clip  — a C-clip that snaps around the bottle body and mounts to the
    wall; the open front lets the bottle press in.

Watertightness: fillet before cutting; ring/clip openings are bored through both
faces (no trapped voids); the shelf is a solid slab with through cutouts; screw
holes open through to the back face.

Sandbox contract (cq_runner.py): `cq`+`math` pre-injected; params are bare
globals read via PARAM(lambda: name, default); final solid assigned to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "shelf_ring"))
bottle_d    = float(PARAM(lambda: bottle_d,    70.0))   # bottle body diameter (mm)
neck_d      = float(PARAM(lambda: neck_d,      28.0))   # pump neck diameter (mm)
count       = int(PARAM(lambda: count,          1))     # bottles held (shelf)
wall        = float(PARAM(lambda: wall,         4.0))   # wall / rim thickness (mm)
depth       = float(PARAM(lambda: depth,       55.0))   # shelf depth / clip reach (mm)
plate_h     = float(PARAM(lambda: plate_h,     50.0))   # wall-plate height (mm)
screw_d     = float(PARAM(lambda: screw_d,      4.2))   # mount screw clearance (mm)

bottle_d = max(30.0, min(bottle_d, 110.0))
neck_d   = max(15.0, min(neck_d, 45.0))
count    = max(1, min(count, 4))
wall     = max(2.5, min(wall, 10.0))
depth    = max(30.0, min(depth, 90.0))
plate_h  = max(30.0, min(plate_h, 100.0))
screw_d  = max(2.5, min(screw_d, 8.0))


def _fillet_safe(wp, selector, radius):
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _back_screws(plate_th, span_x, at_z_list):
    """Return a cutter of plain front-to-back screw through-holes.

    Cut on the XZ plane with both=True so each cylinder spans the full Y
    thickness regardless of the plane-normal sign. Two columns are only used when
    they are clearly separated (>= 3*screw_d between centres); otherwise a single
    centred hole is used. Tangent/near-tangent twin holes pinch to zero wall and
    break watertightness, so they are avoided. No countersink: a countersink
    concentric with a both=True through-hole leaves a non-manifold face on thin
    plates."""
    cutter = None
    if span_x >= 3.0 * screw_d:
        xs = (-span_x / 2.0, span_x / 2.0)
    else:
        xs = (0.0,)
    for x in xs:
        for z in at_z_list:
            hole = (
                cq.Workplane("XZ").center(x, z).circle(screw_d / 2.0)
                .extrude(plate_th, both=True)
            )
            cutter = hole if cutter is None else cutter.union(hole)
    return cutter


# ── shelf_ring ───────────────────────────────────────────────────────────────
def build_shelf_ring():
    """A wall shelf slab with through ring cutouts a bottle drops into."""
    ring_pitch = bottle_d + wall
    shelf_w = count * ring_pitch + wall
    shelf_d = max(depth, bottle_d + 2 * wall)
    slab_th = max(wall * 2.0, 8.0)

    # Back plate against the wall.
    plate_th = max(4.0, wall)
    plate = (
        cq.Workplane("XY")
        .box(shelf_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall, shelf_w / 6.0))

    # Horizontal shelf slab projecting forward from the plate's bottom.
    slab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0, wall))
        .box(shelf_w, shelf_d, slab_th, centered=(True, True, False))
        .translate((0, shelf_d / 2.0, 0))
    )
    body = plate.union(slab)
    body = _fillet_safe(body, ">Y and |Z", min(wall, shelf_w / 6.0))

    # Ring cutouts through the slab (open top + bottom → drains, no trapped void).
    ring_y = plate_th / 2.0 + shelf_d / 2.0
    xs = [(-(count - 1) / 2.0 + i) * ring_pitch for i in range(count)]
    for x in xs:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, ring_y, wall - 1.0))
            .circle(bottle_d / 2.0)
            .extrude(slab_th + 2.0)
        )
        body = body.cut(hole)

    # Screw mounts near the top corners of the back plate.
    screws = _back_screws(plate_th, shelf_w - ring_pitch, [plate_h * 0.82])
    if screws is not None:
        body = body.cut(screws)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── neck_hook ────────────────────────────────────────────────────────────────
def build_neck_hook():
    """Wall plate with a keyhole gripping a pump bottle under its neck collar.

    A pump bottle hangs by its neck: the entry hole only needs to clear the
    collar (not the full body), then a narrow neck slot catches under the collar.
    The entry is sized to the neck (with margin) and kept well inside the plate
    width so the two sides stay solidly bridged (one body). The plate is wide
    enough to back the whole bottle body."""
    plate_w = bottle_d + 2 * wall
    plate_th = max(6.0, wall + 2.0)

    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall * 1.5, plate_w / 5.0))

    # Keyhole (a proper wall-mount keyhole, kept ENTIRELY inside the plate so the
    # two sides stay bridged top AND bottom — a cut that breaks the top or bottom
    # edge would sever the plate into two bodies). The bottle neck is inserted
    # through the round entry, then slid DOWN into the narrow slot that catches
    # under the collar. Entry clears the collar (~neck + margin); its diameter is
    # capped to leave >= 2*wall of plate on each side.
    entry_d = min(neck_d + 12.0, plate_w - 4.0 * wall)
    entry_d = max(entry_d, neck_d + 4.0)
    margin = max(wall, entry_d * 0.12)
    entry_z = plate_h - margin - entry_d / 2.0      # top of entry stays below the rim
    slot_bottom = margin + neck_d / 2.0             # bottom of slot stays above the base
    entry_z = max(entry_z, slot_bottom + neck_d)    # keep a real slot length
    entry = (
        cq.Workplane("XZ").center(0, entry_z).circle(entry_d / 2.0)
        .extrude(plate_th, both=True)
    )
    neck_slot = (
        cq.Workplane("XZ")
        .center(0, (entry_z + slot_bottom) / 2.0)
        .rect(neck_d, entry_z - slot_bottom)
        .extrude(plate_th, both=True)
    )
    neck_end = (
        cq.Workplane("XZ").center(0, slot_bottom).circle(neck_d / 2.0)
        .extrude(plate_th, both=True)
    )
    plate = plate.cut(entry).cut(neck_slot).cut(neck_end)

    # Screw mounts flanking the keyhole, high on the plate.
    screws = _back_screws(plate_th, plate_w - 2.0 * wall, [plate_h * 0.90])
    if screws is not None:
        plate = plate.cut(screws)

    try:
        plate = plate.clean()
    except Exception:
        pass
    return plate


# ── body_clip ────────────────────────────────────────────────────────────────
def build_body_clip():
    """A C-clip that snaps around the bottle body, mounted to a wall plate.

    Built entirely in global coords: the bottle stands upright (axis = Z), so the
    clip is a horizontal ring band at mid-height whose axis is Z. The ring center
    sits FORWARD of the plate by ring_cy so the collar's back overlaps into the
    plate material (volumetric union → one body, watertight). The C-mouth opens
    toward +Y (away from the wall)."""
    collar_or = bottle_d / 2.0 + wall
    plate_w = collar_or * 2.0
    plate_th = max(4.0, wall)

    plate = (
        cq.Workplane("XY")
        .box(plate_w, plate_th, plate_h, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", min(wall, plate_w / 6.0))

    # Ring band: outer solid disc of height collar_h, centered forward at ring_cy.
    collar_h = min(plate_h * 0.55, bottle_d * 0.7)
    collar_z0 = plate_h * 0.5 - collar_h / 2.0
    # Push the ring forward so only a thin back crescent overlaps the plate.
    reach = min(depth, bottle_d)
    ring_cy = plate_th / 2.0 + reach - collar_or  # front-of-plate + reach - radius
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, ring_cy, collar_z0))
        .circle(collar_or)
        .extrude(collar_h)
    )
    # A connector slab guarantees a solid bridge from ring to plate (belt + braces).
    bridge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_th / 2.0 - 1.0, collar_z0))
        .box(min(plate_w, bottle_d * 0.8), ring_cy + collar_or, collar_h, centered=(True, True, False))
        .translate((0, (ring_cy + collar_or) / 2.0, 0))
    )
    body = plate.union(bridge).union(outer)

    # Bore the bottle hole through the ring (vertical, opens top + bottom → no
    # trapped void; the bore also passes through the bridge/plate overlap).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, ring_cy, collar_z0 - 1.0))
        .circle(bottle_d / 2.0)
        .extrude(collar_h + 2.0)
    )
    body = body.cut(bore)

    # C-mouth: open the ring front (+Y) so the bottle presses in from the front.
    mouth_w = bottle_d * 0.5
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, ring_cy + collar_or / 2.0, collar_z0 - 1.0))
        .box(mouth_w, collar_or * 2.0, collar_h + 2.0, centered=(True, True, False))
    )
    body = body.cut(mouth)

    # Screw mounts top + bottom of the back plate.
    screws = _back_screws(plate_th, 0, [plate_h * 0.88, plate_h * 0.12])
    if screws is not None:
        body = body.cut(screws)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "neck_hook":
    result = build_neck_hook()
elif target_part == "body_clip":
    result = build_body_clip()
else:
    result = build_shelf_ring()
