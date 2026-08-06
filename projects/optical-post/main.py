import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
# globals()/eval/NameError are NOT reliable in-sandbox; read every param via PARAM.
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


# Parameters injected by the render worker as bare names; read defensively.
target_part = PARAM(lambda: target_part, "post")
post_height = float(PARAM(lambda: post_height, 75.0))
post_diameter = float(PARAM(lambda: post_diameter, 12.7))
grid_pitch = float(PARAM(lambda: grid_pitch, 25.0))
mount_thread = str(PARAM(lambda: mount_thread, "M6"))
grid_cols = int(PARAM(lambda: grid_cols, 3))
grid_rows = int(PARAM(lambda: grid_rows, 3))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Thorlabs breadboard grid: 25 mm (metric) / 1.00 in centers, 12.5 mm edge border.
# Fasteners: 1/4-20 (imperial, Ø6.35 mm) or M6 (metric). Optical post Ø1/2" = 12.7 mm.
EDGE_BORDER = 12.5           # mm, Thorlabs standard edge-to-first-hole
CBORE_DEPTH = 5.0            # mm, cap-screw head recess


def _fastener_dims(thread):
    """Clearance + counterbore diameters for the two standard breadboard fasteners."""
    key = thread.strip().upper().replace(" ", "")
    table = {
        "M6": (6.6, 11.0),        # M6 clearance, socket-head cap-screw cbore
        "1/4-20": (7.0, 11.5),    # 1/4-20 (Ø6.35) clearance, cap-screw cbore
    }
    return table.get(key, table["M6"])


def _fillet_safe(wp, edges_selector, radius):
    """Fillet the blank BEFORE cutting features; fall back gracefully if OCCT refuses."""
    try:
        return wp.edges(edges_selector).fillet(radius)
    except Exception:
        return wp


# ─── Mode 1: cylindrical optical post ─────────────────────────────────────────
def build_post():
    """Thorlabs TR-style optical post: Ø12.7 mm rod, tapped-head socket on top,
    fastener clearance bore at the base, and a milled setscrew flat.

    The head socket is a counterbored pocket OPEN to the top face (no trapped void);
    it represents the tapped mounting interface without cutting fragile thread grooves.
    """
    r = post_diameter / 2.0
    h = max(20.0, post_height)
    clear_d, cbore_d = _fastener_dims(mount_thread)

    # Solid rod, chamfer the top rim slightly (fillet blank before cutting).
    post = cq.Workplane("XY").circle(r).extrude(h)
    post = _fillet_safe(post, ">Z", min(1.2, r * 0.15))

    # Top mounting socket: counterbore (head recess) opening to the top face.
    socket_d = min(cbore_d, post_diameter - 2.0)
    socket_depth = min(CBORE_DEPTH, h * 0.25)
    post = (
        post.faces(">Z").workplane()
        .circle(socket_d / 2.0).cutBlind(-socket_depth)
    )
    # Pilot/clearance bore continues deeper (still open upward → no sealed cavity).
    pilot_d = min(clear_d - 1.6, socket_d - 2.0)
    post = (
        post.faces(">Z").workplane(offset=-socket_depth)
        .circle(pilot_d / 2.0).cutBlind(-(h * 0.30))
    )

    # Base fastener clearance bore, open to the bottom face.
    base_bore = (
        post.faces("<Z").workplane()
        .circle(clear_d / 2.0).cutBlind(-min(h * 0.30, 12.0))
    )
    post = base_bore

    # Setscrew locking flat milled on the side (open to the outer face).
    flat_depth = r * 0.35
    flat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(r - flat_depth / 2.0, 0, h * 0.55))
        .box(flat_depth, post_diameter * 0.9, h * 0.30)
    )
    return post.cut(flat)


# ─── Mode 2: breadboard base clamp ────────────────────────────────────────────
def build_base_clamp():
    """Thorlabs BA-style base: a footed plate that captures a post and bolts to the
    breadboard on the 25 mm / 1 in grid with two counterbored fastener holes."""
    clear_d, cbore_d = _fastener_dims(mount_thread)
    plate_t = 10.0
    pad = 14.0
    # Footprint spans one grid pitch between the two mounting holes plus a post seat.
    length = grid_pitch + 2 * pad
    width = post_diameter + 2 * pad
    seat_r = post_diameter / 2.0 + 0.3   # slip fit around the post

    base = (
        cq.Workplane("XY")
        .box(length, width, plate_t, centered=(True, True, False))
    )
    base = _fillet_safe(base, "|Z", 4.0)

    # Central post seat: a blind pocket open to the top face (holds the post foot).
    base = (
        base.faces(">Z").workplane()
        .circle(seat_r).cutBlind(-(plate_t * 0.6))
    )
    # Post fastener clearance passes fully through the seat floor to the bottom.
    base = base.faces(">Z").workplane().circle(clear_d / 2.0).cutThruAll()

    # Two grid-mounting counterbores straddling the seat at ±grid_pitch/2.
    hole_x = grid_pitch / 2.0
    base = (
        base.faces(">Z").workplane()
        .pushPoints([(hole_x, 0.0), (-hole_x, 0.0)])
        .cboreHole(clear_d, cbore_d, CBORE_DEPTH, depth=None)
    )
    return base


# ─── Mode 3: mini breadboard grid tile ────────────────────────────────────────
def build_grid_plate():
    """Mini optical breadboard tile: a plate drilled with a rectangular array of
    fastener holes on the real 25 mm metric grid, 12.5 mm edge border."""
    clear_d, cbore_d = _fastener_dims(mount_thread)
    cols = max(2, grid_cols)
    rows = max(2, grid_rows)
    plate_t = 12.7   # 1/2 in, common thin-breadboard thickness

    width = (cols - 1) * grid_pitch + 2 * EDGE_BORDER
    depth = (rows - 1) * grid_pitch + 2 * EDGE_BORDER

    plate = (
        cq.Workplane("XY")
        .box(width, depth, plate_t, centered=(True, True, False))
    )
    plate = _fillet_safe(plate, "|Z", 3.0)

    # Grid of counterbored fastener holes centred on the plate.
    pts = []
    x0 = -(cols - 1) * grid_pitch / 2.0
    y0 = -(rows - 1) * grid_pitch / 2.0
    for i in range(cols):
        for j in range(rows):
            pts.append((x0 + i * grid_pitch, y0 + j * grid_pitch))

    plate = (
        plate.faces(">Z").workplane()
        .pushPoints(pts)
        .cboreHole(clear_d, cbore_d, CBORE_DEPTH, depth=None)
    )
    return plate


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "post":
    result = build_post()
elif target_part == "base_clamp":
    result = build_base_clamp()
elif target_part == "grid_plate":
    result = build_grid_plate()
else:
    result = build_post()
