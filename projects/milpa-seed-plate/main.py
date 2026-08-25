"""
Milpa Seed Spacing Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hand-held spacing plate for laying out a milpa: the maize-bean-squash polyculture
that has been planted across Mesoamerica for millennia and that gives this commons
its agricultural vocabulary. The plate is not a planter — it is a JIG. You lay it
on prepared ground, drop seed through the holes, and lift. What it guarantees is
the one thing hand-sowing loses: a repeatable, stated spacing.

Why spacing is the whole point:
  Maize is wind-pollinated, so it must be sown in a BLOCK of several short rows,
  never a single long one — a lone row sheds its pollen sideways into nothing and
  sets a cob with scattered, missing kernels. Beans climb the maize, so they go at
  the same hill a little later. Squash runs between the hills and shades the soil.
  All three depend on hill pitch being right: too tight and the maize shades the
  squash out, too loose and the beans have nothing to climb before they sprawl.

The plate therefore declares two independent pitches:
  * `row_spacing_mm`  — the distance between rows (across the plate, X).
  * `hill_spacing_mm` — the distance between hills along a row (Y).
Classic smallholder milpa spacing runs roughly 800-1000 mm between rows and
400-500 mm between hills; the plate's default 250 x 200 mm is a SUB-MULTIPLE that
is actually printable and hand-carryable — you step it across the plot. The README
carries the multiple table.

Modes are dispatched via `target_part`:
  * "plate"      — the spacing plate itself: a stiffened slab with a grid of
                   chamfered seed holes and a handle.
  * "depth_stop" — a collar that slips over a dibber/stick to stop it at a set
                   sowing depth (maize wants ~30-50 mm; too shallow and birds take
                   it, too deep and the coleoptile exhausts itself).
  * "row_marker" — a stake-mounted marker that carries the row pitch to the next
                   pass, so successive plate placements stay on the same grid.

Watertightness strategy:
  Every part is a single extruded/boxed blank with THROUGH cuts only. Nothing is
  shelled or offset. The seed holes are bored from below the bottom face to above
  the top face, so they can never become blind pockets. Derived dimensions are
  clamped against the blank they must live inside — in particular the hole grid's
  footprint is computed FIRST and the plate is then sized to contain it with a full
  margin, rather than sizing the plate independently and hoping the grid fits. That
  ordering is what stops a max-pitch, max-count grid from running off the slab and
  severing it into loose islands.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "plate"))
handle_style = str(PARAM(lambda: handle_style, "bar"))   # bar | loop | none

row_spacing_mm = float(PARAM(lambda: row_spacing_mm, 250.0))    # between rows (X)
hill_spacing_mm = float(PARAM(lambda: hill_spacing_mm, 200.0))  # along a row (Y)
hole_count = float(PARAM(lambda: hole_count, 6.0))              # total seed holes
seed_diameter_mm = float(PARAM(lambda: seed_diameter_mm, 14.0)) # drop-through bore Ø
plate_thickness = float(PARAM(lambda: plate_thickness, 6.0))    # slab thickness
depth_stop_mm = float(PARAM(lambda: depth_stop_mm, 40.0))       # sowing depth
dibber_dia_mm = float(PARAM(lambda: dibber_dia_mm, 25.0))       # dibber/stick Ø

# Clamp so extreme UI values still build watertight.
row_spacing_mm = max(80.0, min(row_spacing_mm, 400.0))
hill_spacing_mm = max(60.0, min(hill_spacing_mm, 400.0))
hole_count = max(2.0, min(round(hole_count), 12.0))
seed_diameter_mm = max(6.0, min(seed_diameter_mm, 30.0))
plate_thickness = max(3.0, min(plate_thickness, 12.0))
depth_stop_mm = max(10.0, min(depth_stop_mm, 120.0))
dibber_dia_mm = max(10.0, min(dibber_dia_mm, 50.0))


# ── Grid layout ──────────────────────────────────────────────────────────────
def grid_shape(n):
    """Split n holes into (cols, rows) as near-square as possible.

    Maize must be sown in a BLOCK, not a line: a single row wind-pollinates itself
    badly and sets a gap-toothed cob. So the layout is deliberately squarish rather
    than a strip, and 2 holes still becomes 2x1 (the honest minimum) instead of
    pretending to be a block."""
    n = int(n)
    cols = max(1, int(round(math.sqrt(n))))
    rows = int(math.ceil(n / cols))
    return cols, rows


def hole_centres():
    """Centres of every seed hole, in plate coordinates, centred on the origin."""
    cols, rows = grid_shape(hole_count)
    pts = []
    for r in range(rows):
        for c in range(cols):
            if len(pts) >= int(hole_count):
                break
            x = (c - (cols - 1) / 2.0) * row_spacing_mm
            y = (r - (rows - 1) / 2.0) * hill_spacing_mm
            pts.append((x, y))
    return pts


# ── Part builders ─────────────────────────────────────────────────────────────
def build_plate():
    """The spacing plate: a stiffened slab whose hole grid IS the sowing pattern.

    The blank is derived FROM the grid, not guessed alongside it. Sizing the slab
    from an independent formula is exactly how a max-pitch grid ends up with its
    outer holes hanging off the edge, which cuts the plate into loose islands that
    still tessellate but are not one body."""
    pts = hole_centres()
    hole_r = seed_diameter_mm / 2.0
    margin = max(12.0, seed_diameter_mm * 1.1)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    half_w = (max(xs) - min(xs)) / 2.0 + hole_r + margin
    half_d = (max(ys) - min(ys)) / 2.0 + hole_r + margin
    width = 2.0 * half_w
    depth = 2.0 * half_d

    body = cq.Workplane("XY").box(width, depth, plate_thickness, centered=(True, True, False))

    # Rounded corners: capped well under the margin so the blend can never reach a
    # hole and eat its wall.
    corner_r = min(10.0, half_w * 0.3, half_d * 0.3, margin * 0.6)
    if corner_r >= 0.5:
        try:
            body = body.edges("|Z").fillet(corner_r)
        except Exception:
            pass

    # Seed bores — THROUGH, opened past both faces so they can never be blind.
    for (x, y) in pts:
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, -1.0))
            .circle(hole_r)
            .extrude(plate_thickness + 2.0)
        )
        body = body.cut(bore)

    # A funnel chamfer at each hole mouth so seed drops in instead of skittering.
    # Built as a cut cone rather than a fillet on a bore edge: a blend on a bore in
    # a thin slab is the classic OCC self-degenerate-face case, and it fails SILENTLY
    # (no exception, just a non-watertight solid), so it is avoided outright.
    cham = min(2.5, plate_thickness * 0.35, hole_r * 0.5)
    if cham >= 0.3:
        for (x, y) in pts:
            cone = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, y, plate_thickness - cham))
                .circle(hole_r)
                .workplane(offset=cham)
                .circle(hole_r + cham)
                .loft()
            )
            try:
                body = body.cut(cone)
            except Exception:
                pass

    # Handle. Added as a volumetric union that overlaps the slab, never a tangent
    # kiss on the edge.
    if handle_style in ("bar", "loop"):
        h_w = min(width * 0.5, 90.0)
        h_t = max(plate_thickness, 5.0)
        h_h = max(14.0, plate_thickness * 2.5)
        grip = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, plate_thickness - h_t * 0.4))
            .box(h_w, h_t * 2.2, h_h, centered=(True, True, False))
        )
        try:
            grip = grip.edges("|Y").fillet(min(h_t * 0.8, h_h * 0.4))
        except Exception:
            pass
        body = body.union(grip)

        if handle_style == "loop":
            # Finger slot under the bar — a through cut along Y, so it opens on both
            # faces of the grip and is never a sealed void.
            slot_h = max(4.0, h_h * 0.45)
            slot_w = max(8.0, h_w * 0.55)
            slot = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0.0, 0.0, plate_thickness + h_h - slot_h - 2.0))
                .box(slot_w, h_t * 6.0, slot_h, centered=(True, True, False))
            )
            try:
                body = body.cut(slot)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_depth_stop():
    """A split collar that clamps on a dibber to stop it at a set sowing depth.

    Maize seed wants roughly 30-50 mm: shallower and birds and ants take it before
    it roots, deeper and the coleoptile spends its reserves reaching light. The
    collar makes that depth repeatable by an unskilled hand."""
    bore_r = dibber_dia_mm / 2.0
    wall = max(3.0, dibber_dia_mm * 0.18)
    out_r = bore_r + wall
    height = max(10.0, min(depth_stop_mm * 0.5, 45.0))
    # Flange that actually meets the soil and stops the stick.
    flange_r = out_r + max(6.0, dibber_dia_mm * 0.35)
    flange_t = max(3.0, wall * 0.9)

    body = cq.Workplane("XY").circle(out_r).extrude(height)
    flange = cq.Workplane("XY").circle(flange_r).extrude(flange_t)
    body = body.union(flange)

    # Through bore, opened past both faces.
    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(bore_r).extrude(height + 2.0)
    )
    body = body.cut(bore)

    # Split slot so the collar can spring onto a stick and be slid. Cut clean
    # through the wall in +X, running past the outside so it is a real opening.
    reach = flange_r * 3.0 + 20.0
    slot_w = max(1.6, wall * 0.5)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(reach / 2.0, 0.0, -1.0))
        .box(reach, slot_w, height + 2.0, centered=(True, True, False))
    )
    body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_row_marker():
    """A stake-top marker carrying the row pitch to the next pass.

    The plate only spans a few hills; a plot is worked by stepping it. The marker is
    what keeps successive placements on ONE grid instead of drifting — you leave it
    in the last hole of a pass and register the plate's end hole against it."""
    peg_r = seed_diameter_mm / 2.0 - 0.4
    peg_r = max(2.0, peg_r)
    peg_h = max(12.0, plate_thickness * 2.5)

    head_r = peg_r + max(6.0, seed_diameter_mm * 0.55)
    head_t = max(4.0, plate_thickness * 0.8)

    # Blade height carries the row pitch visibly above crop debris.
    blade_h = max(30.0, min(row_spacing_mm * 0.35, 140.0))
    blade_w = max(8.0, head_r * 1.1)
    blade_t = max(3.0, plate_thickness * 0.6)

    body = cq.Workplane("XY").circle(peg_r).extrude(peg_h)
    head = cq.Workplane("XY").workplane(offset=peg_h - 0.01).circle(head_r).extrude(head_t)
    body = body.union(head)

    blade = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, peg_h + head_t - 0.5))
        .box(blade_w, blade_t, blade_h, centered=(True, True, False))
    )
    try:
        blade = blade.edges("|Y").fillet(min(blade_t * 0.4, blade_w * 0.2))
    except Exception:
        pass
    body = body.union(blade)

    # Sight hole near the blade top — through in Y, so never a sealed void.
    sight_r = min(blade_w * 0.25, blade_h * 0.08)
    if sight_r >= 1.0:
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0.0, peg_h + head_t + blade_h - sight_r * 3.0, 0.0))
            .circle(sight_r)
            .extrude(blade_t * 6.0, both=True)
        )
        try:
            body = body.cut(hole)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "plate": build_plate,
    "depth_stop": build_depth_stop,
    "row_marker": build_row_marker,
}

result = _dispatch.get(target_part, build_plate)()
