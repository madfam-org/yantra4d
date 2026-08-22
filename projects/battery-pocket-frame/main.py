"""Battery Pocket Frame — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The stiffener frame for an in-garment battery pocket. A soft pocket sewn into a heated
jacket or a sensing vest sags around the pack, lets it rotate, and lets it slide out the
mouth; a lithium pack that rotates chafes its own leads. This frame is stitched into the
pocket through perimeter sew holes and gives the pack a defined bay: a rounded-rect ring
sized to the pack footprint, with a retention lip stepping inward at the top so the pack
drops in past the lip and is then held against the mouth.

NON-GARMENT SIBLING: the existing `battery-holder` cartridge is a RIGID ENCLOSURE —
printed carriers that hold 18650 or AA cells captive with contact slots for bus strips.
It is a structural box; this is a limp-pocket stiffener with no contacts, no cell bores,
and a sewn interface. Do not substitute one for the other.

Modes (dispatched via `target_part`):
  * "frame"      — the stiffener frame alone.
  * "frame_lid"  — frame plus a thin retainer strap that spans the bay mouth.
  * "set"        — frame and strap laid out side by side on one plate.

Geometry: the frame is an outer rounded-rect slab minus an oversized rounded-rect bay,
built with fillets applied to CLEAN blanks before the cut. The retention lip is a second,
smaller rounded-rect ring unioned onto the frame top with real Z overlap; because the bay
cut runs clear through, nothing seals a void. Sew holes are one pushPoints cutThruAll.
Separate bodies on a plate are Compounds, never unions.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bay_w`).
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
bay_w     = float(PARAM(lambda: bay_w,     62.0))  # battery bay width (mm)
bay_h     = float(PARAM(lambda: bay_h,     92.0))  # battery bay height (mm)
bay_t     = float(PARAM(lambda: bay_t,     12.0))  # battery bay depth / pack thickness (mm)
frame_w   = float(PARAM(lambda: frame_w,   6.0))   # frame rail width around the bay (mm)
frame_t   = float(PARAM(lambda: frame_t,   2.4))   # frame plate thickness (mm)
lip       = float(PARAM(lambda: lip,       2.0))   # retention lip inward step (mm)
corner_r  = float(PARAM(lambda: corner_r,  5.0))   # bay corner radius (mm)
sew_pitch = float(PARAM(lambda: sew_pitch, 12.0))  # spacing between sew holes (mm)
hole_dia  = float(PARAM(lambda: hole_dia,  1.8))   # stitch hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "frame"))  # frame|frame_lid|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
bay_w     = max(20.0, min(bay_w, 140.0))
bay_h     = max(20.0, min(bay_h, 180.0))
bay_t     = max(4.0, min(bay_t, 40.0))
frame_t   = max(1.4, min(frame_t, 6.0))
hole_dia  = max(1.0, min(hole_dia, 3.0))
# The rail must be wide enough for a stitch hole with wall either side.
frame_w   = max(hole_dia + 3.0, min(frame_w, 20.0))
corner_r  = max(1.0, min(corner_r, min(bay_w, bay_h) / 3.0))
sew_pitch = max(hole_dia + 3.0, min(sew_pitch, 40.0))
# The lip can never close the bay or exceed the rail it stands on.
lip       = max(0.0, min(lip, min(frame_w * 0.6, min(bay_w, bay_h) / 4.0)))

outer_w = bay_w + 2.0 * frame_w
outer_h = bay_h + 2.0 * frame_w
outer_r = corner_r + frame_w

# Depth skirt: two short walls dropping from the frame underside along the long sides,
# reaching a fraction of the pack thickness so the pack cannot rock in the pocket.
skirt_h = max(1.5, min(bay_t * 0.45, 14.0))
skirt_t = max(1.2, min(frame_w * 0.7, 3.0))

# Lip ring: stands proud of the frame top and steps inward by `lip`.
lip_h = max(0.8, min(frame_t * 0.8, bay_t * 0.25))
lip_inner_w = max(4.0, bay_w - 2.0 * lip)
lip_inner_h = max(4.0, bay_h - 2.0 * lip)
lip_inner_r = max(0.5, corner_r - lip)

# Stitch lane: a rectangular ring centred in the frame rail.
lane_w = bay_w + frame_w
lane_h = bay_h + frame_w

# Retainer strap: a thin bar spanning the bay mouth, sewn at both ends.
strap_w = max(8.0, min(bay_w * 0.25, 24.0))
strap_len = outer_w
strap_t = max(1.2, min(frame_t * 0.7, 2.5))


def _rounded_slab(length, width, thick, rad, z0=0.0):
    """A rounded-rectangle slab centred on the origin — fillet on a CLEAN blank."""
    r = max(0.4, min(rad, min(length, width) / 2.0 - 0.2))
    return (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .edges("|Z")
        .fillet(r)
        .translate((0, 0, z0))
    )


def _sew_points():
    """Stitch-hole centres marching around a rectangular lane at `sew_pitch`."""
    hx = lane_w / 2.0
    hy = lane_h / 2.0
    pts = []
    # Top and bottom runs.
    n_x = max(2, int(lane_w / sew_pitch))
    for i in range(n_x):
        t = (i + 0.5) / n_x
        x = -hx + lane_w * t
        pts.append((x, hy))
        pts.append((x, -hy))
    # Left and right runs, stopping short of the corners already covered.
    n_y = max(1, int((lane_h - sew_pitch) / sew_pitch))
    inner_h = lane_h - sew_pitch
    for i in range(n_y):
        t = (i + 0.5) / n_y
        y = -inner_h / 2.0 + inner_h * t
        pts.append((hx, y))
        pts.append((-hx, y))
    return pts


def build_frame():
    """Rounded-rect ring + inward retention lip + perimeter stitch holes."""
    total_h = frame_t + lip_h
    outer = _rounded_slab(outer_w, outer_h, frame_t, outer_r)

    if lip > 0.01:
        # Lip ring stands on the frame top, overlapping into it so the union is solid.
        lip_ring = _rounded_slab(
            outer_w, outer_h, lip_h + 0.6, outer_r, z0=frame_t - 0.6
        )
        body = outer.union(lip_ring)
        # Cut the lip's narrower opening first — clear through the lip band only.
        lip_bay = _rounded_slab(
            lip_inner_w, lip_inner_h, lip_h + 6.0, lip_inner_r, z0=frame_t - 1.0
        )
        body = body.cut(lip_bay)
    else:
        body = outer
        total_h = frame_t

    # Depth skirt: a wall dropping from the frame underside along each long side, so the
    # pack registers against it and cannot rock. Unioned with real Z overlap; both walls
    # stay clear of the bay opening so nothing is sealed.
    skirt_x = bay_w / 2.0 + skirt_t / 2.0
    for sx in (skirt_x, -skirt_x):
        wall_solid = (
            cq.Workplane("XY")
            .box(skirt_t, bay_h, skirt_h + 0.6)
            .translate((sx, 0.0, -skirt_h / 2.0 + 0.3))
        )
        body = body.union(wall_solid)

    # Main bay: cut clear through the whole stack, overshooting both faces.
    bay = _rounded_slab(bay_w, bay_h, total_h + skirt_h + 8.0, corner_r,
                        z0=-skirt_h - 4.0)
    body = body.cut(bay)

    # Stitch holes: one pass from the underside, clean through both faces.
    body = (
        body.faces("<Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(x, -y) for (x, y) in _sew_points()])
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )
    return body


def build_strap():
    """A thin retainer bar spanning the bay mouth, with a stitch hole at each end."""
    bar = _rounded_slab(strap_len, strap_w, strap_t, min(strap_w / 3.0, 3.0))
    hx = strap_len / 2.0 - frame_w / 2.0
    return (
        bar.faces("<Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(hx, 0.0), (-hx, 0.0)])
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )


def _compound(solids):
    """Separate bodies on one plate — a Compound, never a union of non-touching solids."""
    shapes = []
    for s in solids:
        shapes.extend(s.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "frame":
    result = build_frame()
elif target_part == "frame_lid":
    _off = outer_h / 2.0 + strap_w / 2.0 + 5.0
    result = _compound([build_frame(), build_strap().translate((0.0, _off, 0.0))])
else:
    _off = outer_h / 2.0 + strap_w / 2.0 + 5.0
    result = _compound([
        build_frame(),
        build_strap().translate((0.0, _off, 0.0)),
        build_strap().translate((0.0, _off + strap_w + 5.0, 0.0)),
    ])
