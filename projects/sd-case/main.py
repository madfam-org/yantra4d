"""
SD / MicroSD Card Case — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A memory-card organizer that holds SD, microSD, and CompactFlash cards in a
gridded array of slots. Part of the card-format family — the slot block shares
the card-footprint pocket convention with card-holder and deck-box, so a case
sized here tiles alongside them.

Modes are dispatched via `target_part`:
  * "sd_tray"    — a row×column grid of full-size SD slots.
  * "micro_tray" — a denser grid of microSD slots (with a thumb ramp per slot).
  * "combo_case" — a mixed block: a bank of SD slots beside a bank of microSD slots.

Reference dimensions (mm):
  * SD card:        24.0 × 32.0 × 2.1
  * microSD card:   11.0 × 15.0 × 1.0
  * CompactFlash:   43.0 × 36.0 × 3.3
Slots are cut with per-side clearance so real cards drop in and pull out.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals.
  - Access them via PARAM(lambda: <name>, <default>). Never use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Card table (width × height × thickness, mm) ──────────────────────────────
_CARDS = {
    "SD": {"w": 24.0, "h": 32.0, "t": 2.1},
    "MICROSD": {"w": 11.0, "h": 15.0, "t": 1.0},
    "CF": {"w": 43.0, "h": 36.0, "t": 3.3},
}


def card_spec(key):
    k = str(key).strip().upper().replace(" ", "").replace("-", "")
    if k in ("SD",):
        return _CARDS["SD"]
    if k in ("MICROSD", "MICRO", "TF"):
        return _CARDS["MICROSD"]
    if k in ("CF", "COMPACTFLASH"):
        return _CARDS["CF"]
    return _CARDS["SD"]


# ── Parameters ───────────────────────────────────────────────────────────────
card_type = str(PARAM(lambda: card_type, "SD"))    # SD | microSD | CF
cols = int(PARAM(lambda: cols, 4))                  # slot columns
rows = int(PARAM(lambda: rows, 3))                  # slot rows
wall = float(PARAM(lambda: wall, 2.0))             # wall between/around slots
floor = float(PARAM(lambda: floor, 1.6))           # base thickness under slots
clearance = float(PARAM(lambda: clearance, 0.4))   # per-side slot clearance

target_part = str(PARAM(lambda: target_part, "sd_tray"))

# ── Clamp to printable ranges ────────────────────────────────────────────────
cols = max(1, min(cols, 8))
rows = max(1, min(rows, 6))
wall = max(1.2, min(wall, 5.0))
floor = max(1.0, min(floor, 5.0))
clearance = max(0.15, min(clearance, 1.0))


def _fillet_safe(wp, selector, radius):
    """Fillet the blank BEFORE cutting slots; fall back if OCCT refuses."""
    try:
        return wp.edges(selector).fillet(radius)
    except Exception:
        return wp


def _slot_grid(spec, ncols, nrows, extra_floor=0.0):
    """A block with an ncols×nrows grid of card slots, each open to the top face.
    Each slot gets a small thumb ramp at its front so a card can be pushed out."""
    sw = spec["w"] + 2 * clearance
    sh = spec["h"] + 2 * clearance
    slot_depth = spec["h"] * 0.72 + floor + extra_floor   # depth into the block
    pitch_x = sw + wall
    pitch_y = sh + wall
    body_l = ncols * sw + (ncols + 1) * wall
    body_w = nrows * sh + (nrows + 1) * wall
    body_h = min(slot_depth + floor, spec["h"] * 0.85 + floor)

    block = (
        cq.Workplane("XY")
        .box(body_l, body_w, body_h, centered=(True, True, False))
    )
    block = _fillet_safe(block, "|Z", min(3.0, wall + 0.5))

    # Slot centres.
    pts = []
    x0 = -(ncols - 1) * pitch_x / 2.0
    y0 = -(nrows - 1) * pitch_y / 2.0
    for i in range(ncols):
        for j in range(nrows):
            pts.append((x0 + i * pitch_x, y0 + j * pitch_y))

    # Card slots: rounded rectangles, open to the top face — cut in one boolean.
    block = (
        block.faces(">Z").workplane()
        .pushPoints(pts)
        .rect(spec["w"] + 2 * clearance, spec["h"] + 2 * clearance)
        .cutBlind(-(body_h - floor))
    )

    # Thumb notch per slot: a shallow scoop opening the top rim of each slot so a
    # fingertip reaches the card edge. Cut for ALL slots in a SINGLE boolean via
    # pushPoints — batching keeps the render fast and the mesh watertight.
    notch_w = min(sw * 0.55, 12.0)
    notch_d = sh * 0.35
    notch_h = min(body_h * 0.6, spec["h"] * 0.4)
    notch_pts = [(px, py + sh / 2.0 - notch_d / 2.0) for (px, py) in pts]
    block = (
        block.faces(">Z").workplane()
        .pushPoints(notch_pts)
        .rect(notch_w, notch_d)
        .cutBlind(-notch_h)
    )
    return block


# ── Mode 1: full-size card grid (SD / microSD / CF, per card_type) ───────────
def build_sd_tray():
    return _slot_grid(card_spec(card_type), cols, rows)


# ── Mode 2: denser microSD grid ──────────────────────────────────────────────
def build_micro_tray():
    # microSD is small; give it an extra column and row for a denser tray.
    return _slot_grid(_CARDS["MICROSD"], cols + 1, rows + 1)


# ── Mode 3: combo case (SD bank + microSD bank) ──────────────────────────────
def build_combo_case():
    """A single block with an SD slot bank on the left and a microSD bank on the
    right, unioned across a shared central wall (overlapping union, no seam)."""
    sd = _slot_grid(_CARDS["SD"], cols, rows)
    micro = _slot_grid(_CARDS["MICROSD"], cols, rows + 1)

    sd_bb = sd.val().BoundingBox()
    micro_bb = micro.val().BoundingBox()
    # Match base heights so the two banks share a flat bottom, then abut with an
    # overlap of one wall so the union is solid (not tangent).
    gap = sd_bb.xlen / 2.0 + micro_bb.xlen / 2.0 - wall
    micro = micro.translate((gap, 0, 0))

    # Level both to Z=0 (they already start at Z=0) and union.
    combo = sd.union(micro)
    # Re-centre on X for a tidy origin.
    cb = combo.val().BoundingBox()
    combo = combo.translate((-(cb.xmin + cb.xmax) / 2.0, 0, 0))
    return combo


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "sd_tray":
    result = build_sd_tray()
elif target_part == "micro_tray":
    result = build_micro_tray()
elif target_part == "combo_case":
    result = build_combo_case()
else:
    result = build_sd_tray()
