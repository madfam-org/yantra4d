"""TPU Lattice Panel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place flexible ARMOR LATTICE — the additive-manufacturing textile the Fashion
Cabinet `lattice-armor-panel` notion describes and bridges to here for its geometry. A
grid of rigid tiles joined by thin flexure bridges prints flat as ONE solid and drapes
like a scale garment: rigid plate, flexible seam. Printed in TPU the thin bridges act as
living hinges between the stiff tiles, so the sheet conforms to the body while the tiles
protect.

This is the soft-goods↔hard-goods seam made physical (after tpu-chainmail-panel and the
pleat/flexure capsule): the panel is simultaneously a Fashion Cabinet fabric (tile size,
drape, cut planning) and a Yantra4D solid (the printable tile-and-bridge lattice). One
material identity spans both — `bambu-tpu-95a`.

Modes (dispatched via `target_part`):
  * "panel"  — the full tile lattice (rows x cols), print-in-place.
  * "swatch" — a 3x3 sample for a print/drape test.
  * "cell"   — a single tile + its bridges, for tuning stiffness.

Every tile is a box; bridges are thin boxes spanning the gaps, kept narrower than the
tile so the sheet flexes only at the bridges. Tiles and bridges OVERLAP and are returned
as an Assembly (like the chainmail rings) — the slicer prints the overlapping geometry
as one connected sheet, which avoids the O(n^2) blow-up of fusing dozens of boxes.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rows`).
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
rows        = int(  PARAM(lambda: rows,        8))      # tile rows down the panel
cols        = int(  PARAM(lambda: cols,        6))      # tile cols across the panel
tile        = float(PARAM(lambda: tile,        18.0))   # tile edge length (mm)
tile_thick  = float(PARAM(lambda: tile_thick,  2.5))    # tile thickness (mm)
gap         = float(PARAM(lambda: gap,         3.0))    # gap between tiles (bridge span)
bridge_w    = float(PARAM(lambda: bridge_w,    5.0))    # bridge width (mm)
bridge_t    = float(PARAM(lambda: bridge_t,    0.8))    # bridge thickness (flexes here, mm)

target_part = str(  PARAM(lambda: target_part, "panel"))  # panel|swatch|cell

# ── Safe clamps ──────────────────────────────────────────────────────────────
rows       = max(1, min(rows, 40))
cols       = max(1, min(cols, 40))
tile       = max(6.0, min(tile, 60.0))
tile_thick = max(1.0, min(tile_thick, 10.0))
gap        = max(1.0, min(gap, 12.0))
bridge_w   = max(1.0, min(bridge_w, tile))
bridge_t   = max(0.4, min(bridge_t, tile_thick - 0.2))

pitch = tile + gap                       # tile-to-tile centre spacing


def _tile(cx, cy):
    """One rigid tile centred at (cx, cy), sitting on z=0."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, tile_thick / 2.0))
        .box(tile, tile, tile_thick)
    )


def _bridge(cx, cy, along_x):
    """A thin flexure bridge centred at (cx, cy). Spans the gap plus a little overlap
    into each tile so the fuse is solid; thin in Z so it is the only place that flexes.
    `along_x` True = bridge runs in X (joins left/right tiles)."""
    span = gap + tile * 0.2               # overlap into both tiles
    if along_x:
        w, d = span, bridge_w
    else:
        w, d = bridge_w, span
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, bridge_t / 2.0))
        .box(w, d, bridge_t)
    )


def build_panel(n_rows, n_cols):
    """The tile lattice: an n_rows x n_cols grid of tiles, each joined to its right and
    lower neighbour by a thin flexure bridge. Returned as an Assembly of overlapping
    tile + bridge solids (the print fuses them) — O(n) placement, no boolean blow-up."""
    asm = cq.Assembly()
    idx = 0
    for r in range(n_rows):
        for c in range(n_cols):
            cx, cy = c * pitch, r * pitch
            asm.add(_tile(cx, cy), name=f"tile_{idx}", color=cq.Color("#6f7f8a"))
            idx += 1
            if c < n_cols - 1:
                asm.add(_bridge(cx + pitch / 2.0, cy, True),
                        name=f"bridge_x_{idx}", color=cq.Color("#5a6a74"))
                idx += 1
            if r < n_rows - 1:
                asm.add(_bridge(cx, cy + pitch / 2.0, False),
                        name=f"bridge_y_{idx}", color=cq.Color("#5a6a74"))
                idx += 1
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cell":
    result = build_panel(2, 2)
elif target_part == "swatch":
    result = build_panel(3, 3)
else:
    result = build_panel(rows, cols)
