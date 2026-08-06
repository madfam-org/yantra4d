"""
Junction Box Mounting Ears — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Retrofit mounting hardware for US electrical junction boxes. It bridges the
device-mounting screw pattern of a standard single-gang box — #6-32 screws on a
~83.3 mm (3.28 in) vertical centre-to-centre pitch — to a wall, a surface
standoff, or a raised mud ring. Sizes follow the US NEMA/NEC box conventions
(single-gang device box ~2 x 3 in face; #6-32 device screws).

Three distinct modes (dispatch on target_part):
  - ear_pair     : a pair of flat retrofit ears (printed as one plate joined by
                   a thin frangible web) that screw to the box tabs and give the
                   box a new mounting flange with wall screw holes.
  - box_standoff : a rectangular standoff frame that spaces a box off a rough
                   surface, carrying the device-screw pattern through to the box.
  - mud_ring     : a raised single-gang plaster ring that brings the box up flush
                   to a thick wall finish, with the device screw pattern on the
                   raised face and wall ears at the sides.

Watertight strategy (per the Yantra4D authoring canon):
  - Fillet the clean blank BEFORE cutting any feature.
  - All screw holes are simple through-bores (vent to outside), never trapped.
  - The mud ring's raised collar and the standoff walls union into the base with
    real material overlap (no tangent seams, no severed bodies).
  - The ear pair's connecting web is solid material, so the print is one body
    (snap it apart after printing).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - No cross-file imports; assign the final solid to top-level `result`.
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
target_part = str(PARAM(lambda: target_part, "ear_pair"))
# "ear_pair" | "box_standoff" | "mud_ring"

device_pitch = float(PARAM(lambda: device_pitch, 83.3))  # #6-32 device screw C-C
device_screw = float(PARAM(lambda: device_screw, 3.6))   # #6-32 clearance (~3.5mm)
wall_screw = float(PARAM(lambda: wall_screw, 4.5))       # #8 wall screw clearance
gang_w = float(PARAM(lambda: gang_w, 50.0))              # single-gang box width (~2in)
plate_t = float(PARAM(lambda: plate_t, 4.0))             # plate thickness
ring_h = float(PARAM(lambda: ring_h, 16.0))              # mud-ring / standoff depth
ear_w = float(PARAM(lambda: ear_w, 22.0))                # wall-ear width

# Clamp to sane ranges so extreme UI values never crash the kernel.
device_pitch = max(60.0, min(device_pitch, 120.0))
device_screw = max(2.5, min(device_screw, 6.0))
wall_screw = max(3.0, min(wall_screw, 7.0))
gang_w = max(40.0, min(gang_w, 70.0))
plate_t = max(3.0, min(plate_t, 8.0))
ring_h = max(8.0, min(ring_h, 30.0))
ear_w = max(16.0, min(ear_w, 34.0))

_opening_w = gang_w - 2.0 * 8.0        # the device opening width (box mouth)
_opening_h = device_pitch - 18.0        # opening height between the screw bosses


# ── Helpers ──────────────────────────────────────────────────────────────────
def _bore_z(wp, x, y, dia, z0, depth):
    """A simple through-bore along +Z from z0."""
    return wp.cut(
        cq.Workplane("XY").transformed(offset=cq.Vector(x, y, z0))
        .circle(dia / 2.0).extrude(depth)
    )


def _device_holes(wp, z0, depth):
    """The two #6-32 device screws at +/- device_pitch/2 on the Y centreline."""
    for sgn in (+1.0, -1.0):
        wp = _bore_z(wp, 0.0, sgn * device_pitch / 2.0, device_screw, z0, depth)
    return wp


# ── Part builders ────────────────────────────────────────────────────────────
def build_ear_pair():
    """A flat plate the size of the box face carrying BOTH the device-screw
    pattern (to bolt onto the box) and outboard wall-screw ears — the simplest
    retrofit flange. Printed flat; thickness +Z."""
    plate_w = gang_w + 2.0 * ear_w
    plate_h = device_pitch + 22.0
    plate = (cq.Workplane("XY").box(plate_w, plate_h, plate_t,
                                    centered=(True, True, False)))
    try:
        plate = plate.edges("|Z").fillet(min(6.0, ear_w - 2.0))
    except Exception:
        pass

    # Device opening (the box mouth) through the centre.
    opening = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -1.0))
               .rect(_opening_w, _opening_h).extrude(plate_t + 2.0))
    plate = plate.cut(opening)

    # Device screws (mount plate to box).
    plate = _device_holes(plate, -1.0, plate_t + 2.0)
    # Wall screws in the outboard ears (two each side).
    ex = gang_w / 2.0 + ear_w / 2.0
    for sx in (+ex, -ex):
        for sy in (+1.0, -1.0):
            plate = _bore_z(plate, sx, sy * plate_h * 0.3, wall_screw,
                            -1.0, plate_t + 2.0)
    return plate


def build_box_standoff():
    """A rectangular standoff frame that lifts the box off a rough/uneven
    surface: a base flange with wall screws, four short walls forming the box
    pocket, and the device-screw pattern on the top rim so the box bolts on."""
    # Collar must extend in Y past the device screws (+/- pitch/2) with margin so
    # a screw bore in the top rim never clips a wall edge (sliver / non-manifold).
    screw_margin = device_screw / 2.0 + 7.0
    collar_h = device_pitch + 2.0 * screw_margin
    base_w = gang_w + 2.0 * ear_w
    base_h = collar_h + 8.0
    base = (cq.Workplane("XY").box(base_w, base_h, plate_t,
                                   centered=(True, True, False)))
    try:
        base = base.edges("|Z").fillet(min(6.0, ear_w - 2.0))
    except Exception:
        pass

    # Rectangular collar walls rising +Z, forming an open box pocket (the pocket
    # opens through the base too, so no trapped void).
    outer = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, 0))
             .rect(gang_w, collar_h)
             .extrude(ring_h))
    inner = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -1.0))
             .rect(gang_w - 2.0 * plate_t, collar_h - 2.0 * plate_t)
             .extrude(ring_h + plate_t + 2.0))
    collar = outer.cut(inner)
    body = base.union(collar)

    # Cut the base window inside the pocket so wiring passes through (vents).
    window = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -1.0))
              .rect(gang_w - 2.0 * plate_t - 2.0,
                    collar_h - 2.0 * plate_t - 2.0)
              .extrude(plate_t + 2.0))
    body = body.cut(window)

    # Device screws through the top rim front-to-back on the Y centreline.
    body = _device_holes(body, -1.0, ring_h + plate_t + 2.0)
    # Wall screws in the base ears.
    ex = gang_w / 2.0 + ear_w / 2.0
    for sx in (+ex, -ex):
        body = _bore_z(body, sx, 0.0, wall_screw, -1.0, plate_t + 2.0)
    return body


def build_mud_ring():
    """A raised single-gang plaster (mud) ring: a base flange with side wall-ears,
    a raised rectangular collar bringing the device face up to a thick finish,
    and the device-screw pattern on the raised face."""
    # Collar/base must extend in Y past the device screws (at +/- pitch/2) with
    # margin, so a screw bore never clips a wall edge (a partial cut -> sliver /
    # non-watertight). Margin covers the screw radius + a solid rim.
    screw_margin = device_screw / 2.0 + 7.0
    collar_h = device_pitch + 2.0 * screw_margin
    base_w = gang_w + 2.0 * ear_w
    base_h = collar_h + 4.0
    base = (cq.Workplane("XY").box(base_w, base_h, plate_t,
                                   centered=(True, True, False)))
    try:
        base = base.edges("|Z").fillet(min(6.0, ear_w - 2.0))
    except Exception:
        pass

    # Raised collar around the device opening, rising +Z by ring_h.
    outer = (cq.Workplane("XY").rect(gang_w, collar_h).extrude(ring_h))
    body = base.union(outer)

    # Device opening straight through collar + base (vents both ends).
    opening = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -1.0))
               .rect(_opening_w, _opening_h).extrude(ring_h + plate_t + 2.0))
    body = body.cut(opening)

    # Device screws through the raised face into the box.
    body = _device_holes(body, -1.0, ring_h + plate_t + 2.0)
    # Wall screws in the base ears (one each side).
    ex = gang_w / 2.0 + ear_w / 2.0
    for sx in (+ex, -ex):
        body = _bore_z(body, sx, 0.0, wall_screw, -1.0, plate_t + 2.0)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "box_standoff":
    result = build_box_standoff()
elif target_part == "mud_ring":
    result = build_mud_ring()
else:
    result = build_ear_pair()
