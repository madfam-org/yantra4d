import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:  # noqa: BLE001 — NameError is absent from older
        # cq_runner sandbox builtin allowlists, so catching it by name raises
        # inside the sandbox; the broad catch is the portable probe.
        return default


target_part   = PARAM(lambda: target_part, "feeler_rack")
blade_width   = float(PARAM(lambda: blade_width, 12.7))    # feeler blade width = 1/2 in
blade_count   = int(float(PARAM(lambda: blade_count, 13)))    # metric set 0.05–1.00 mm = 13 blades
slot_pitch    = float(PARAM(lambda: slot_pitch, 4.0))
wall          = float(PARAM(lambda: wall, 4.0))
body_height   = float(PARAM(lambda: body_height, 22.0))
index_cols    = int(float(PARAM(lambda: index_cols, 10)))
index_rows    = int(float(PARAM(lambda: index_rows, 6)))
max_bit_dia   = float(PARAM(lambda: max_bit_dia, 6.5))     # #1–#60 wire-gauge range top


# ─── Mode 1: Feeler Rack (upright blade slots) ────────────────────────────────
def build_feeler_rack():
    """A block holding N feeler blades upright, each in a thin obround slot cut
    from the top face. Slots are open to the top (no trapped void) and matched to
    the 12.7 mm standard blade width."""
    n = max(2, blade_count)
    length = slot_pitch * n + 2.0 * wall
    depth = blade_width + 2.0 * wall
    body = cq.Workplane("XY").box(length, depth, body_height)
    # Fillet the blank BEFORE cutting the slots.
    body = body.edges("|Z").fillet(4.0)
    body = body.edges(">Z").fillet(1.0)

    slot_depth = body_height * 0.7
    x0 = -slot_pitch * (n - 1) / 2.0
    z_plane = body_height / 2.0
    for i in range(n):
        x = x0 + i * slot_pitch
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=z_plane - slot_depth)
            .center(x, 0.0)
            .slot2D(blade_width + 0.6, 1.6, 0)
            .extrude(slot_depth + 1.0)
        )
        body = body.cut(cutter)
    return body


# ─── Mode 2: Drill Index (grid of graduated blind holes) ──────────────────────
def build_drill_index():
    """A stand for a numbered drill / gauge set: a grid of blind holes whose
    diameters step linearly from small to the set maximum, each open to the top
    face. A canonical CDG grid interface."""
    cols = max(2, index_cols)
    rows = max(1, index_rows)
    total = cols * rows

    min_d = 1.0
    max_d = max_bit_dia
    pitch = max_d + 3.5
    length = pitch * cols + 2.0 * wall
    depth = pitch * rows + 2.0 * wall
    height = max(body_height, max_d + 8.0)

    body = cq.Workplane("XY").box(length, depth, height)
    body = body.edges("|Z").fillet(5.0)
    body = body.edges(">Z").fillet(1.0)

    x0 = -pitch * (cols - 1) / 2.0
    y0 = -pitch * (rows - 1) / 2.0
    hole_depth = height * 0.7
    z_top = height / 2.0
    idx = 0
    for r in range(rows):
        for c in range(cols):
            frac = idx / max(1, total - 1)
            d = min_d + frac * (max_d - min_d)
            x = x0 + c * pitch
            y = y0 + r * pitch
            cutter = (
                cq.Workplane("XY")
                .workplane(offset=z_top - hole_depth)
                .center(x, y)
                .circle(d / 2.0)
                .extrude(hole_depth + 1.0)
            )
            body = body.cut(cutter)
            idx += 1
    return body


# ─── Mode 3: Blade Tray (flat storage slots) ──────────────────────────────────
def build_blade_tray():
    """A shallow tray that stores loose blades / gauge leaves flat in parallel
    channels. Each channel is a long obround pocket open to the top face AND
    through the front wall (so a blade slides in from the front and can be pushed
    out) — no trapped void and no thin front lip to fracture at small scale."""
    n = max(2, blade_count)
    channel_len = blade_width + 20.0
    # Derive pitch/width from wall so channel walls never thin below ~1.4 mm.
    pitch = max(3.0, 1.8 + 1.6)
    width = pitch * n + 2.0 * wall
    depth = channel_len + wall + 4.0
    height = 10.0

    body = cq.Workplane("XY").box(width, depth, height)
    body = body.edges("|Z").fillet(3.0)
    body = body.edges(">Z").fillet(0.8)

    ch_depth = height * 0.55
    z_top = height / 2.0
    x0 = -pitch * (n - 1) / 2.0
    # Channels open to the front face. Define the obround by explicit front/back Y:
    #   front protrudes 5 mm past the front wall  => guaranteed open exit
    #   back stops (wall + 2) short of the back face => solid back stop, never zero-thick
    front_y = -depth / 2.0 - 5.0
    back_y = depth / 2.0 - (wall + 2.0)
    slot_len = back_y - front_y
    slot_cy = (front_y + back_y) / 2.0
    for i in range(n):
        x = x0 + i * pitch
        cutter = (
            cq.Workplane("XY")
            .workplane(offset=z_top - ch_depth)
            .center(x, slot_cy)
            .slot2D(slot_len, 1.8, 90)
            .extrude(ch_depth + 1.0)
        )
        body = body.cut(cutter)
    return body


# ─── Dispatch ────────────────────────────────────────────────────────────────
_dispatch = {
    "feeler_rack": build_feeler_rack,
    "drill_index": build_drill_index,
    "blade_tray":  build_blade_tray,
}

result = _dispatch.get(target_part, build_feeler_rack)()
