"""Epaulette Board — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A structured shoulder board — the rigid hard good the Fashion Cabinet `printed-epaulette`
notion places and bridges to here for its geometry. A tapered plate (wide at the shoulder
seam, narrow at the collar) with a raised rim and a button post at the collar end, it
gives a uniform or costume shoulder its crisp military line. A hard finding, not a
textile: printed rigid, it slips under a fabric epaulette or is worn bare.

Modes (dispatched via `target_part`):
  * "board"  — the shoulder board (plate + rim + button post).
  * "plate"  — just the flat tapered plate (no rim), for a softer look.

The plate is an extruded trapezoid (straight line segments only — no arcs); the rim is a
slightly larger extruded trapezoid with the plate footprint cut from its top; the button
post is a small cylinder. Small boolean count → fast, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `board_len`).
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
board_len   = float(PARAM(lambda: board_len,   140.0))  # shoulder-seam to collar (mm)
wide_w      = float(PARAM(lambda: wide_w,       60.0))   # width at the shoulder seam (mm)
narrow_w    = float(PARAM(lambda: narrow_w,     40.0))   # width at the collar end (mm)
plate_t     = float(PARAM(lambda: plate_t,      2.5))    # plate thickness (mm)
rim_h       = float(PARAM(lambda: rim_h,        3.0))    # raised rim height (mm)
rim_w       = float(PARAM(lambda: rim_w,        3.0))    # rim wall width (mm)
button_dia  = float(PARAM(lambda: button_dia,   10.0))   # collar button post diameter (mm)

target_part = str( PARAM(lambda: target_part, "board"))  # board|plate

# ── Safe clamps ──────────────────────────────────────────────────────────────
board_len  = max(60.0, min(board_len, 260.0))
wide_w     = max(20.0, min(wide_w, 120.0))
narrow_w   = max(15.0, min(narrow_w, wide_w))
plate_t    = max(1.5, min(plate_t, 6.0))
rim_h      = max(1.0, min(rim_h, 8.0))
rim_w      = max(1.5, min(rim_w, min(wide_w, narrow_w) / 2.0 - 1.0))
button_dia = max(4.0, min(button_dia, narrow_w - 4.0))


def _trapezoid(w0, w1, length, thick):
    """An extruded trapezoid on z=0: width w0 at y=0 tapering to w1 at y=length,
    centred on X, `thick` tall. Straight segments only."""
    return (
        cq.Workplane("XY")
        .polyline([(-w0 / 2.0, 0.0), (w0 / 2.0, 0.0),
                   (w1 / 2.0, length), (-w1 / 2.0, length)])
        .close()
        .extrude(thick)
    )


def build_plate():
    return _trapezoid(wide_w, narrow_w, board_len, plate_t)


def build_board():
    """Plate + a raised rim around its edge + a button post at the collar end."""
    plate = build_plate()

    # Rim: a taller trapezoid, minus the plate footprint inset by rim_w, so only a wall
    # of width rim_w stands proud above the plate.
    outer = _trapezoid(wide_w, narrow_w, board_len, plate_t + rim_h)
    inner = _trapezoid(wide_w - 2.0 * rim_w, narrow_w - 2.0 * rim_w,
                       board_len - 2.0 * rim_w, plate_t + rim_h + 2.0)
    inner = inner.translate((0.0, rim_w, plate_t))     # sit the cut above the plate
    rim = outer.cut(inner)

    body = plate.union(rim)

    # Button post at the collar end (near y = board_len).
    post = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, board_len - narrow_w * 0.35,
                                      plate_t + button_dia * 0.2))
        .circle(button_dia / 2.0)
        .extrude(button_dia * 0.4)
    )
    return body.union(post)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "plate":
    result = build_plate()
else:
    result = build_board()
