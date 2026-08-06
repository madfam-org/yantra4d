"""
Speaker Wall Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A wall bracket for bookshelf / satellite speakers and small soundbars. Every
mode mounts to the wall through the same keyhole-slot interface (drops onto two
screw heads, then settles down to lock) and cradles the speaker on the other
side.

Three modes (rendered per-part via `target_part`):

  * "shelf_bracket" — an L shelf the speaker sits on: a wall plate with keyhole
                      slots and a horizontal shelf with a front retaining lip.
  * "strap_mount"   — a wall plate plus an open band / strap that wraps up around
                      a satellite speaker body and screws closed.
  * "keyhole_plate" — a flat plate carrying wall keyhole slots on one side and a
                      speaker-screw bolt pattern on the other (for a speaker with
                      its own threaded insert / bracket boss).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "shelf_bracket"))  # shelf_bracket|strap_mount|keyhole_plate

wall_w = float(PARAM(lambda: wall_w, 70.0))        # wall-plate width (mm)
wall_h = float(PARAM(lambda: wall_h, 70.0))        # wall-plate height (mm)
thickness = float(PARAM(lambda: thickness, 5.0))   # plate / shelf thickness (mm)

speaker_w = float(PARAM(lambda: speaker_w, 90.0))  # speaker footprint / body width (mm)
speaker_d = float(PARAM(lambda: speaker_d, 90.0))  # speaker depth on the shelf (mm)
shelf_depth = float(PARAM(lambda: shelf_depth, 80.0))  # how far the shelf sticks out (mm)
lip_h = float(PARAM(lambda: lip_h, 10.0))          # front retaining lip height (mm)

tilt = float(PARAM(lambda: tilt, 0.0))             # downward shelf tilt (deg)

keyhole_dia = float(PARAM(lambda: keyhole_dia, 9.0))   # keyhole big-hole (screw head) dia (mm)
keyhole_slot = float(PARAM(lambda: keyhole_slot, 4.5)) # keyhole slot (shank) width (mm)
keyhole_drop = float(PARAM(lambda: keyhole_drop, 12.0))  # slot travel below the big hole (mm)

speaker_screw = float(PARAM(lambda: speaker_screw, 4.5))  # speaker mounting screw dia (mm)
speaker_bolt_span = float(PARAM(lambda: speaker_bolt_span, 50.0))  # speaker bolt spacing (mm)


# ── Active part ──────────────────────────────────────────────────────────────
_parts = ("shelf_bracket", "strap_mount", "keyhole_plate")
active = target_part if target_part in _parts else "shelf_bracket"

# ── Safe clamps ──────────────────────────────────────────────────────────────
thickness = max(2.5, thickness)
wall_w = max(30.0, wall_w)
wall_h = max(30.0, wall_h)
speaker_w = max(20.0, speaker_w)
speaker_d = max(20.0, speaker_d)
shelf_depth = max(20.0, shelf_depth)
lip_h = max(0.0, lip_h)
tilt = max(0.0, min(tilt, 20.0))
keyhole_dia = max(5.0, min(keyhole_dia, wall_w * 0.35))
keyhole_slot = max(2.5, min(keyhole_slot, keyhole_dia - 1.0))
keyhole_drop = max(4.0, keyhole_drop)
speaker_screw = max(1.5, speaker_screw)
speaker_bolt_span = max(10.0, speaker_bolt_span)


# ── Shared plate + keyhole helpers (reused across the batch) ──────────────────
def plate_xz(w, h, t):
    """A wall plate standing in the XZ plane (facing -Y): width w in X, height h
    in Z rising from z=0, thickness t in Y with its back face at y=0 (screwed to
    a wall at y=0, material extends to y=+t away from the wall)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, t / 2.0, h / 2.0))
        .box(w, t, h)
    )


def keyhole_points(w, h):
    """Two keyhole big-hole centres near the top of a w×h wall plate."""
    x = min(w * 0.30, w / 2.0 - keyhole_dia)
    x = max(x, keyhole_dia * 0.6)
    z = h - max(keyhole_dia, h * 0.18)
    return [(-x, z), (x, z)]


def cut_keyholes(body, w, h, t):
    """Cut two wall keyhole slots through a plate standing in XZ (thickness in
    Y). Each keyhole is a big round hole (screw head passes) with a narrow slot
    dropping below it (the shank slides down to lock)."""
    r_big = keyhole_dia / 2.0
    thru = t + 2.0
    for (x, z) in keyhole_points(w, h):
        # Big head hole.
        head = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, z, 0))
            .cylinder(thru, r_big)
        )
        body = body.cut(head)
        # Slot below: a rounded channel from the hole down by keyhole_drop.
        slot = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(x, z - keyhole_drop / 2.0, 0))
            .slot2D(keyhole_drop, keyhole_slot, 90)
            .extrude(thru)
            .translate((0, -thru / 2.0, 0))
        )
        body = body.cut(slot)
    return body


def speaker_bolt_points():
    """Four speaker-screw points on a square of side speaker_bolt_span."""
    h = speaker_bolt_span / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


# ── Builders ─────────────────────────────────────────────────────────────────
def build_keyhole_plate():
    """Flat plate: wall keyhole slots (top) + a speaker-screw bolt square that
    goes through the plate so the speaker's own bracket boss bolts on. Both the
    keyholes and the bolt square are cut through a single standing plate."""
    body = plate_xz(wall_w, wall_h, thickness)
    body = cut_keyholes(body, wall_w, wall_h, thickness)

    # Speaker screw square in the lower portion of the plate.
    cz = min(wall_h * 0.35, wall_h / 2.0)
    for (px, pz) in speaker_bolt_points():
        z = cz + pz
        if z < speaker_screw or z > wall_h - speaker_screw:
            continue
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(px, z, 0))
            .cylinder(thickness + 2.0, speaker_screw / 2.0)
        )
        body = body.cut(hole)
    return body


def build_shelf_bracket():
    """L shelf: a wall plate (with keyholes) plus a horizontal shelf sticking
    out in +Y, with a front retaining lip, optionally tilted down toward the
    wall so the speaker leans back into the plate. Two triangular gussets brace
    the shelf under load."""
    wall = plate_xz(wall_w, wall_h, thickness)
    wall = cut_keyholes(wall, wall_w, wall_h, thickness)

    shelf_w = min(speaker_w + 2.0 * thickness, wall_w)

    # Horizontal shelf: sits at the plate front (y from thickness outward),
    # its top face flush with z=thickness so the speaker rests on top.
    shelf = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, thickness + shelf_depth / 2.0, thickness / 2.0)
        )
        .box(shelf_w, shelf_depth, thickness)
    )

    # Front retaining lip rising at the shelf's outer edge.
    if lip_h > 0.05:
        lip = (
            cq.Workplane("XY")
            .transformed(
                offset=cq.Vector(
                    0,
                    thickness + shelf_depth - thickness / 2.0,
                    thickness + lip_h / 2.0,
                )
            )
            .box(shelf_w, thickness, lip_h)
        )
        shelf = shelf.union(lip)

    # Side gussets: right-triangle braces under the shelf, in the YZ plane.
    reach = min(shelf_depth * 0.7, wall_h * 0.7)
    reach = max(reach, thickness * 2.0)
    gx = shelf_w / 2.0 - thickness / 2.0
    for sx in (-gx, gx):
        tri = (
            cq.Workplane("YZ")
            .polyline([
                (thickness, 0.0),
                (thickness + reach, 0.0),
                (thickness, -reach),
            ])
            .close()
            .extrude(thickness)
            .translate((sx - thickness / 2.0, 0, 0))
        )
        shelf = shelf.union(tri)

    body = wall.union(shelf)

    if tilt > 0.05:
        # Tilt the whole assembly's shelf back by rotating about the X axis at
        # the wall front root; a small tilt keeps the speaker leaning inward.
        body = body.rotate((0, thickness, 0), (1, thickness, 0), -tilt)
    return body.clean()


def build_strap_mount():
    """Wall plate plus an open band that cradles a satellite speaker body. The
    solid mass (plate + a neck block + the band's outer disc) is fused FIRST,
    then the speaker bore and the top mouth are subtracted last — ending the
    boolean tree on cuts keeps the C-cradle a clean watertight solid."""
    band_r_out = speaker_w / 2.0 + thickness
    band_r_in = speaker_w / 2.0
    band_w = min(speaker_d, wall_h * 0.6)   # band height in Z
    band_cz = wall_h * 0.5
    z0 = band_cz - band_w / 2.0
    cy = thickness + band_r_out            # disc centre out in +Y

    # ── Solid mass first ─────────────────────────────────────────────────────
    wall = plate_xz(wall_w, wall_h, thickness)

    # Outer disc of the band (solid for now).
    disc = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy, z0))
        .circle(band_r_out)
        .extrude(band_w)
    )
    # Neck block bridging plate front to the disc, overlapping both generously.
    neck_len = band_r_out + thickness
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, thickness + neck_len / 2.0, z0 + band_w / 2.0))
        .box(min(speaker_w, wall_w * 0.7), neck_len, band_w)
    )
    solid = wall.union(disc).union(neck)

    # ── Subtract the speaker bore and the mouth last ─────────────────────────
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy, z0 - 0.5))
        .circle(band_r_in)
        .extrude(band_w + 1.0)
    )
    solid = solid.cut(bore)

    # Mouth: open the top (+Y) so the speaker slides in. Cut a slab spanning the
    # +Y outer half, narrower than the bore so two arms remain.
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cy + band_r_out, z0 + band_w / 2.0))
        .box(band_r_in * 1.1, band_r_out * 2.0, band_w + 2.0)
    )
    solid = solid.cut(mouth)

    # Now cut the keyholes (through the plate) after the big booleans.
    solid = cut_keyholes(solid, wall_w, wall_h, thickness)
    return solid.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "strap_mount":
    result = build_strap_mount()
elif active == "keyhole_plate":
    result = build_keyhole_plate()
else:
    result = build_shelf_bracket()
