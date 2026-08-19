"""TPU Hinge Collar — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place stand-or-fold collar band — the additive-manufacturing trim the Fashion
Cabinet `printed-hinge-collar` notion describes and bridges to here for its geometry. A
flat collar band with a printed living-hinge fold line runs along its length: the upper
stand and the lower sewn band are stiff, the thin slotted fold line between them lets the
collar stand up or fold down and hold its crease. Printed in TPU the fold line is the
living hinge; no interfacing, no topstitched roll line.

Modes (dispatched via `target_part`):
  * "collar"  — the full collar band (length x height) with the fold line.
  * "swatch"  — a short sample for a print/fold test.
  * "band"    — a plain band (no fold line), to compare stiffness.

The band is one flat plate; the fold line is a row of through-slots that leave ligaments
between them, so the plate stays one watertight solid and flexes only on that line.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `collar_len`).
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
collar_len   = float(PARAM(lambda: collar_len,   400.0))  # collar length around the neck (mm)
stand_h      = float(PARAM(lambda: stand_h,      35.0))   # stand height above the fold (mm)
band_h       = float(PARAM(lambda: band_h,       30.0))   # sewn band height below the fold (mm)
wall         = float(PARAM(lambda: wall,         2.0))    # plate thickness (mm)
fold_slots   = int(  PARAM(lambda: fold_slots,   28))     # slots along the fold line
slot_w       = float(PARAM(lambda: slot_w,       6.0))    # slot length along the collar (mm)

target_part  = str(  PARAM(lambda: target_part, "collar"))  # collar|swatch|band

# ── Safe clamps ──────────────────────────────────────────────────────────────
collar_len = max(120.0, min(collar_len, 700.0))
stand_h    = max(10.0, min(stand_h, 120.0))
band_h     = max(10.0, min(band_h, 120.0))
wall       = max(1.0, min(wall, 6.0))
fold_slots = max(2, min(fold_slots, 80))
slot_w     = max(1.0, min(slot_w, 20.0))

total_h = stand_h + band_h                # the fold line sits at y = band_h


def _band(length, cols):
    """A flat collar band: length x total_h x wall, sitting on z=0 with y=0 at the
    lower (sewn) edge. Returns (body, cols) after building the fold-line slots."""
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(length / 2.0, total_h / 2.0, wall / 2.0))
        .box(length, total_h, wall)
    )
    # Fold line: a row of through-slots centred at y = band_h, leaving a ligament
    # between each so the band stays connected and flexes only here.
    margin = max(3.0, length * 0.03)
    span = length - 2.0 * margin
    if cols > 1:
        step = span / (cols - 1)
        start = margin
    else:
        step = 0.0
        start = length / 2.0
    for i in range(cols):
        x = start + i * step
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, band_h, wall / 2.0))
            .box(slot_w, wall * 0.9, wall + 2.0)   # thin in Y (the crease), long in X
        )
        body = body.cut(slot)
    return body


def build_collar(length=None, cols=None):
    length = collar_len if length is None else length
    cols = fold_slots if cols is None else cols
    return _band(length, cols)


def build_band():
    """A plain band — no fold slots — for a stiffness comparison."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(collar_len / 2.0, total_h / 2.0, wall / 2.0))
        .box(collar_len, total_h, wall)
    )


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "band":
    result = build_band()
elif target_part == "swatch":
    result = build_collar(length=120.0, cols=max(2, fold_slots // 3))
else:
    result = build_collar()
