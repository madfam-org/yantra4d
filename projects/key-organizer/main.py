"""
Key Organizer / Bit Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A Swiss-army-style key organizer: two side plates and a pivot bolt clamp a stack of
house keys so they fan out like a pocket knife. This cartridge builds the side
plate, the inter-key spacer that sets the stack gap, and a hex-bit-holder variant.

Three distinct parts:
  - organizer_body : a side plate with a pivot bolt hole at one end, a rounded
                     grip body, and a recessed key-bow pocket + a slotted tension
                     tail. The pivot end carries a counterbore for the bolt head.
  - spacer         : the inter-key spacer washer/comb — a thin plate with the pivot
                     hole and a raised rib that sets the gap between fanned keys.
  - bit_holder     : the same footprint but with a row of hex sockets (1/4 in hex
                     driver bits) opening to the top face instead of a key pocket.

Dimensioning (standard house-key blanks; internal organizer geometry):
  - key blade width  : ~8.5 mm  (Kwikset KW1 blade = 0.335 in)
  - key blade thick  : ~2.2 mm  (KW1 ~2.0 mm, Schlage SC1 ~2.2 mm — the pocket is
                        cut to the thicker SC1 so both blanks clear)
  - pivot bolt       : M5 (5.2 mm clearance) — the common key-organizer bolt
  - hex bit socket   : 6.35 mm across-flats (1/4 in hex), a hexagon pocket

Watertight strategy:
  Every part is a filleted flat blank. The pivot bore, tension-tail slot, key-bow
  pocket and hex sockets are all through- or open-to-a-face cuts (they vent to
  outside → no sealed cavity). The pivot counterbore is a stepped bore open to one
  face. Hex sockets are cut as polygon prisms opening to the top face. Fillets are
  applied to the clean blank BEFORE any feature is cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>).
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


# ── Parameters (standard house-key blanks; internal organizer geometry) ──────
target_part = str(PARAM(lambda: target_part, "organizer_body"))
# "organizer_body" | "spacer" | "bit_holder"

body_len = float(PARAM(lambda: body_len, 62.0))    # plate length (Y, along the keys)
body_w = float(PARAM(lambda: body_w, 22.0))        # plate width (X)
plate_t = float(PARAM(lambda: plate_t, 4.0))       # plate thickness (Z)

pivot_d = float(PARAM(lambda: pivot_d, 5.2))       # pivot bolt Ø (M5 clearance)
pivot_head_d = float(PARAM(lambda: pivot_head_d, 9.5))  # pivot bolt head Ø (counterbore)
key_blade_w = float(PARAM(lambda: key_blade_w, 8.5))    # key blade width (KW1 0.335 in)
key_blade_t = float(PARAM(lambda: key_blade_t, 2.2))    # key blade thickness (SC1)
key_count = int(PARAM(lambda: key_count, 4))       # keys the stack pocket is sized for
hex_af = float(PARAM(lambda: hex_af, 6.35))        # hex bit across-flats (1/4 in)
bit_count = int(PARAM(lambda: bit_count, 4))       # number of hex sockets (bit_holder)

# Clamp to sane ranges so extreme UI values never crash the kernel.
body_len = max(40.0, min(body_len, 120.0))
body_w = max(14.0, min(body_w, 45.0))
plate_t = max(2.5, min(plate_t, 12.0))
pivot_d = max(3.0, min(pivot_d, 8.0))
pivot_head_d = max(pivot_d + 2.5, min(pivot_head_d, body_w - 4.0))
key_blade_w = max(5.0, min(key_blade_w, body_w - 6.0))
key_blade_t = max(1.5, min(key_blade_t, plate_t - 1.0))
key_count = max(1, min(key_count, 12))
hex_af = max(4.0, min(hex_af, body_w - 8.0))
bit_count = max(1, min(bit_count, 8))

# The pivot sits near the +Y end; the working body extends toward -Y.
_pivot_cy = body_len - (pivot_head_d / 2.0 + 3.0)


# ── Primitives ───────────────────────────────────────────────────────────────
def _blank():
    """A filleted flat plate, base at z=0, centred on X, spanning 0..body_len in Y.
    Fillet the CLEAN blank before any feature cut."""
    p = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, body_len / 2.0, 0))
        .box(body_w, body_len, plate_t, centered=(True, True, False))
    )
    try:
        p = p.edges("|Z").fillet(min(body_w / 2.0 - 0.5, 6.0))
    except Exception:
        pass
    return p


def _pivot(counterbore=True):
    """The pivot bolt cut: a through bore, optionally with a counterbore for the
    bolt head open to the TOP face. Both features vent to outside."""
    cuts = []
    cuts.append(
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, _pivot_cy, -0.5))
        .circle(pivot_d / 2.0)
        .extrude(plate_t + 1.0)
    )
    if counterbore:
        cb_depth = min(plate_t * 0.5, 3.0)
        cuts.append(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, _pivot_cy, plate_t - cb_depth))
            .circle(pivot_head_d / 2.0)
            .extrude(cb_depth + 0.5)
        )
    return cuts


# ── Part builders ────────────────────────────────────────────────────────────
def build_organizer_body():
    """A side plate: pivot bolt (counterbored) at the +Y end, a recessed key-bow
    pocket down the body that captures the fanned key bows, and a slotted tension
    tail at the -Y end for a thumb grip / lanyard."""
    body = _blank()

    # Key-bow pocket: a recessed channel on the TOP face running down the -Y body,
    # deep enough to seat the key blades' bow ends. Opens to the top face → vents.
    # Its length grows with the key stack (key_count blades fanning ~key_blade_t
    # apart), capped to the space between the pivot end and the tension tail.
    pocket_w = key_blade_w + 1.5
    pocket_depth = min(plate_t - 1.2, key_blade_t + 0.6)
    max_pocket = _pivot_cy - pivot_head_d / 2.0 - 14.0
    stack_len = key_count * (key_blade_t + 1.2) + 8.0
    pocket_len = max(12.0, min(stack_len, max_pocket))
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, pocket_len / 2.0 + 10.0, plate_t - pocket_depth))
        .slot2D(pocket_len, pocket_w, angle=90)
        .extrude(pocket_depth + 1.0)
    )
    body = body.cut(pocket)

    # Tension tail slot at the -Y end (thumb grip / lanyard hole).
    tail = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 6.0, -0.5))
        .slot2D(7.0, 4.0, angle=90)
        .extrude(plate_t + 1.0)
    )
    body = body.cut(tail)

    for c in _pivot(counterbore=True):
        body = body.cut(c)
    return body


def build_spacer():
    """The inter-key spacer comb: a thinner plate with the pivot hole and a raised
    rib along one edge that sets the fan gap between keys. Shorter than the body."""
    # A spacer is a distinct, shorter, thinner plate.
    spacer_len = body_len * 0.6
    spacer_t = max(2.0, key_blade_t + 1.0)
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, spacer_len / 2.0, 0))
        .box(body_w * 0.8, spacer_len, spacer_t, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|Z").fillet(min(body_w * 0.4 - 0.5, 5.0))
    except Exception:
        pass

    # Raised rib along the +X edge that sets the gap (a bar unioned on top, overlap).
    rib = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(body_w * 0.4 - 2.0, spacer_len / 2.0, 0))
        .box(3.0, spacer_len, spacer_t + 1.5, centered=(True, True, False))
    )
    plate = plate.union(rib)

    # Pivot bore (no counterbore on the spacer).
    piv_cy = spacer_len - (pivot_d / 2.0 + 4.0)
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, piv_cy, -0.5))
        .circle(pivot_d / 2.0)
        .extrude(spacer_t + 2.5)
    )
    plate = plate.cut(bore)
    return plate


def build_bit_holder():
    """A hex-bit-holder variant: the same plate footprint but carrying a row of
    1/4 in hex sockets that open to the TOP face (each vents outward), plus the
    pivot bore so it stacks in the same organizer."""
    body = _blank()

    # A row of hex sockets down the body, opening to the top face.
    # polygon(6, D) treats D as the across-CORNERS (circumscribed) diameter; for a
    # target across-flats of hex_af, D = hex_af / cos(30deg) = hex_af / (sqrt3/2).
    socket_dia = hex_af / (3.0 ** 0.5) * 2.0
    socket_depth = min(plate_t - 1.0, 8.0)
    span_start = 8.0
    span_end = _pivot_cy - pivot_head_d / 2.0 - 6.0
    n = max(1, min(bit_count, int((span_end - span_start) / (hex_af + 3.0)) + 1))
    if n == 1:
        ys = [(span_start + span_end) / 2.0]
    else:
        step = (span_end - span_start) / (n - 1)
        ys = [span_start + i * step for i in range(n)]
    for cy in ys:
        hexsock = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, cy, plate_t - socket_depth))
            .polygon(6, socket_dia)
            .extrude(socket_depth + 1.0)
        )
        body = body.cut(hexsock)

    for c in _pivot(counterbore=True):
        body = body.cut(c)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "spacer":
    result = build_spacer()
elif target_part == "bit_holder":
    result = build_bit_holder()
else:
    result = build_organizer_body()
