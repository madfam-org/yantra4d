"""TPU Scale Mail — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place flexible SCALE-MAIL panel — the additive-manufacturing textile the
Fashion Cabinet `articulated-scale-mail` notion describes and bridges to here for its
geometry. Rows of overlapping scales, each anchored to a thin backing strip by a narrow
flexure neck, print flat as an Assembly and articulate like a dragon-scale garment:
rigid scale, flexible neck. Printed in TPU the necks act as living hinges so each scale
lifts independently while the sheet drapes.

This is the soft-goods↔hard-goods seam made physical (with the chainmail / pleat /
flexure / lattice capsule): the panel is simultaneously a Fashion Cabinet fabric (scale
size, overlap, drape) and a Yantra4D solid (the printable scale-and-neck sheet). One
material identity spans both — `bambu-tpu-95a`.

Modes (dispatched via `target_part`):
  * "panel"  — the full scale field (rows x cols), print-in-place.
  * "swatch" — a 3x3 sample for a print/articulation test.
  * "scale"  — a single scale + neck, for tuning the shape.

Each scale is a box with a chamfered leading edge; scales overlap the row below and are
tied to the backing by a thin neck. Returned as an Assembly (overlaps print as one
sheet) so there is no O(n^2) boolean blow-up.

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
rows        = int(  PARAM(lambda: rows,        7))      # scale rows down the panel
cols        = int(  PARAM(lambda: cols,        6))      # scale cols across the panel
scale_w     = float(PARAM(lambda: scale_w,     20.0))   # scale width (mm)
scale_h     = float(PARAM(lambda: scale_h,     26.0))   # scale height along the drop (mm)
scale_t     = float(PARAM(lambda: scale_t,     2.0))    # scale thickness (mm)
overlap     = float(PARAM(lambda: overlap,     0.45))   # row overlap fraction (0..0.7)
neck_w      = float(PARAM(lambda: neck_w,      5.0))    # flexure neck width (mm)
back_t      = float(PARAM(lambda: back_t,      0.8))    # backing strip thickness (mm)

target_part = str(  PARAM(lambda: target_part, "panel"))  # panel|swatch|scale

# ── Safe clamps ──────────────────────────────────────────────────────────────
rows      = max(1, min(rows, 40))
cols      = max(1, min(cols, 40))
scale_w   = max(8.0, min(scale_w, 60.0))
scale_h   = max(8.0, min(scale_h, 80.0))
scale_t   = max(1.0, min(scale_t, 8.0))
overlap   = max(0.0, min(overlap, 0.7))
neck_w    = max(1.0, min(neck_w, scale_w))
back_t    = max(0.4, min(back_t, scale_t - 0.2))

row_pitch = scale_h * (1.0 - overlap)     # vertical advance per row (rows overlap)
col_pitch = scale_w                        # scales sit edge-to-edge across


def _scale(cx, cy):
    """One scale centred at (cx, cy): a box the size of the scale with its leading
    (lower) edge chamfered to a rounded tip, sitting a little proud of the backing."""
    z0 = back_t                            # scales sit on top of the backing plane
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, z0 + scale_t / 2.0))
        .box(scale_w, scale_h, scale_t)
    )
    # Chamfer the two lower corners so the scale reads as a pointed dragon scale.
    try:
        body = body.edges("|Z and <Y").chamfer(min(scale_w, scale_h) * 0.28)
    except Exception:
        pass                               # chamfer is cosmetic; skip if geometry rejects
    return body


def _neck(cx, cy):
    """The thin flexure neck tying a scale's top to the backing — narrow + thin so the
    scale hinges here. A small box bridging the scale underside to the backing plane."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy + scale_h * 0.32, back_t))
        .box(neck_w, scale_h * 0.25, scale_t * 0.6)
    )


def _backing(n_rows, n_cols):
    """A thin backing sheet the scales anchor to (a single plate spanning the field).
    Scales span X:[-scale_w/2 .. (n_cols-1+0.5)*col_pitch+scale_w/2] and
    Y:[-scale_h/2 .. (n_rows-1)*row_pitch+scale_h/2]; centre the plate on that box."""
    x_lo, x_hi = -scale_w / 2.0, (n_cols - 1) * col_pitch + col_pitch / 2.0 + scale_w / 2.0
    y_lo, y_hi = -scale_h / 2.0, (n_rows - 1) * row_pitch + scale_h / 2.0
    cx, cy = (x_lo + x_hi) / 2.0, (y_lo + y_hi) / 2.0
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, back_t / 2.0))
        .box(x_hi - x_lo, y_hi - y_lo, back_t)
    )


def build_panel(n_rows, n_cols):
    """The scale field: rows of scales (offset alternate rows by half a scale) over a
    thin backing, each scale tied by a neck. Returned as an Assembly (overlaps print as
    one sheet)."""
    asm = cq.Assembly()
    asm.add(_backing(n_rows, n_cols), name="backing", color=cq.Color("#4a5a52"))
    idx = 0
    for r in range(n_rows):
        y = r * row_pitch
        x_off = (col_pitch / 2.0) if (r % 2) else 0.0
        for c in range(n_cols):
            x = c * col_pitch + x_off
            asm.add(_scale(x, y), name=f"scale_{idx}", color=cq.Color("#7f8f86"))
            asm.add(_neck(x, y), name=f"neck_{idx}", color=cq.Color("#5a6a62"))
            idx += 1
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "scale":
    result = build_panel(1, 1)
elif target_part == "swatch":
    result = build_panel(3, 3)
else:
    result = build_panel(rows, cols)
