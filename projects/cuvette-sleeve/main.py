import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "sleeve")
cuvette_size = float(PARAM(lambda: cuvette_size, 10.0))
holder_size = float(PARAM(lambda: holder_size, 12.5))
sleeve_h = float(PARAM(lambda: sleeve_h, 45.0))
clearance = float(PARAM(lambda: clearance, 0.4))
floor_th = float(PARAM(lambda: floor_th, 2.0))
riser = float(PARAM(lambda: riser, 8.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Standard spectrophotometer cuvette: 10 mm optical path, ~12.5 mm square outer
#   footprint, ~45 mm tall (ISO / Beckman / Hellma macro-cuvette convention).
#   Matches the cuvette-rack (10 mm) and filter-wheel (12.5 mm square well) parts.
CORNER_FILLET = 0.8


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


def _square_prism(size, height, z0=0.0):
    """A square prism centred on Z, standing from z0."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .rect(size, size)
        .extrude(height)
    )


# ─── Mode 1: square-to-square drop sleeve ─────────────────────────────────────
def build_sleeve():
    """A square sleeve whose OUTER footprint matches the 12.5 mm holder slot and
    whose square INNER pocket accepts a 10 mm cuvette (plus clearance). A closed
    floor sets the cuvette height and seals the bottom (pocket opens to the top
    only → no trapped void). Drops into any 12.5 mm cuvette holder."""
    outer = max(holder_size, cuvette_size + 1.5)
    inner = cuvette_size + 2.0 * clearance
    h = max(sleeve_h * 0.5, riser + floor_th + 5.0)

    body = _square_prism(outer, h)
    body = _fillet_safe(body, "|Z", CORNER_FILLET)

    # Inner pocket from the top down to the floor (extended past the top face so
    # the cut opens cleanly to the top; floor stays solid → no trapped void).
    pocket_depth = h - floor_th
    pocket = _square_prism(inner, pocket_depth + 2.0, z0=floor_th)
    body = body.cut(pocket)
    return body


# ─── Mode 2: round-to-square adapter ──────────────────────────────────────────
def build_round_adapter():
    """Adapts a ROUND cuvette / vial into a SQUARE 12.5 mm holder slot: a square
    outer prism with a round inner bore (cuvette_size = the vial diameter). Closed
    floor; bore opens to the top only → watertight."""
    outer = max(holder_size, cuvette_size + 1.5)
    bore_r = (cuvette_size + 2.0 * clearance) / 2.0
    h = max(sleeve_h * 0.5, riser + floor_th + 5.0)

    body = _square_prism(outer, h)
    body = _fillet_safe(body, "|Z", CORNER_FILLET)

    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_th))
        .cylinder(h, bore_r, centered=(True, True, False))
    )
    body = body.cut(bore)
    return body


# ─── Mode 3: height riser sleeve (short-path cuvette in a tall holder) ─────────
def build_riser_sleeve():
    """A sleeve with a taller solid riser skirt below the pocket so a short (semi-
    micro) cuvette sits with its 10 mm window centred in a tall holder's light
    path. Outer square = holder slot; the pocket opens to the top over a solid
    riser base → no trapped void."""
    outer = max(holder_size, cuvette_size + 1.5)
    inner = cuvette_size + 2.0 * clearance
    base = floor_th + riser
    h = base + max(12.0, sleeve_h * 0.45)

    body = _square_prism(outer, h)
    body = _fillet_safe(body, "|Z", CORNER_FILLET)

    pocket = _square_prism(inner, h, z0=base)
    body = body.cut(pocket)

    # Thumb slot: a vertical half-round cut through one wall down to the pocket
    # floor so a finger can push a short cuvette back up. Opens to a side face and
    # to the pocket (never sealed) → stays watertight, and makes this mode's
    # topology distinct from the plain sleeve.
    slot_r = inner * 0.42
    slot = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, base + (h - base) / 2.0, -outer))
        .circle(slot_r)
        .extrude(outer * 2.0)
    )
    body = body.cut(slot)
    return body


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "sleeve":
    result = build_sleeve()
elif target_part == "round_adapter":
    result = build_round_adapter()
elif target_part == "riser_sleeve":
    result = build_riser_sleeve()
else:
    result = build_sleeve()
