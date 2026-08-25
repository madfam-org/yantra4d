"""TPU Gusset Flexure — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place stretch GUSSET — the additive-manufacturing insert the Fashion Cabinet
`printed-gusset-flexure` notion describes and bridges to here for its geometry. A diamond
gusset (the four-point insert sewn into an underarm, crotch, or side vent for range of
motion) printed as a thin TPU panel cut with a slit lattice, so it stretches biaxially
where a woven gusset only eases on the bias. Printed thin the ligaments between slits
flex; sewn into the seam it opens as the wearer moves.

Modes (dispatched via `target_part`):
  * "gusset"  — the full diamond gusset with the slit lattice.
  * "swatch"  — a small square sample of the slit pattern.
  * "solid"   — the plain diamond (no slits), to compare stretch.

The diamond is an extruded rhombus (straight segments — no arcs); the slit lattice is a
grid of short through-slots that leave ligaments, so the panel stays one watertight solid
and stretches at the slits.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `diag_w`).
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
diag_w    = float(PARAM(lambda: diag_w,    70.0))    # gusset width (horizontal diagonal, mm)
diag_h    = float(PARAM(lambda: diag_h,    90.0))    # gusset height (vertical diagonal, mm)
wall      = float(PARAM(lambda: wall,      1.4))     # panel thickness (mm)
slit_rows = int(  PARAM(lambda: slit_rows, 5))       # rows of slits
slit_cols = int(  PARAM(lambda: slit_cols, 4))       # slits per row
slit_len  = float(PARAM(lambda: slit_len,  9.0))     # slit length (mm)

target_part = str(PARAM(lambda: target_part, "gusset"))  # gusset|swatch|solid

# ── Safe clamps ──────────────────────────────────────────────────────────────
diag_w    = max(20.0, min(diag_w, 200.0))
diag_h    = max(20.0, min(diag_h, 260.0))
wall      = max(0.8, min(wall, 4.0))
slit_rows = max(1, min(slit_rows, 16))
slit_cols = max(1, min(slit_cols, 12))
slit_len  = max(2.0, min(slit_len, min(diag_w, diag_h) * 0.4))


def _diamond():
    """The rhombus panel: points at (+-diag_w/2, 0) and (0, +-diag_h/2), extruded."""
    hw, hh = diag_w / 2.0, diag_h / 2.0
    return (
        cq.Workplane("XY")
        .polyline([(-hw, 0.0), (0.0, -hh), (hw, 0.0), (0.0, hh)])
        .close()
        .extrude(wall)
    )


def build_gusset():
    """The diamond with a staggered slit lattice cut through it. Slits sit well inside
    the outline (scaled to ~55% of each diagonal) so the border stays intact and the
    panel never splits — the ligaments between slits are the stretch."""
    body = _diamond()
    # Slit field spans the central 55% of each diagonal.
    fw, fh = diag_w * 0.55, diag_h * 0.55
    for r in range(slit_rows):
        # Row y from -fh/2 .. +fh/2.
        y = (-fh / 2.0 + fh * r / (slit_rows - 1)) if slit_rows > 1 else 0.0
        offset = (fw / slit_cols / 2.0) if (r % 2) else 0.0
        for c in range(slit_cols):
            x = (-fw / 2.0 + fw * (c + 0.5) / slit_cols) + offset
            # Keep the slit inside the diamond at this y (rhombus half-width shrinks
            # linearly toward the points).
            half_at_y = (diag_w / 2.0) * (1.0 - abs(y) / (diag_h / 2.0))
            if abs(x) + slit_len / 2.0 > half_at_y - 2.0:
                continue
            slit = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, y, wall / 2.0))
                .box(slit_len, wall * 0.9, wall + 2.0)
            )
            body = body.cut(slit)
    return body


def build_swatch():
    """A small square of the slit pattern (for a print/stretch test)."""
    side = 40.0
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall / 2.0))
        .box(side, side, wall)
    )
    for r in range(3):
        y = -12.0 + r * 12.0
        offset = 6.0 if (r % 2) else 0.0
        for c in range(3):
            x = -12.0 + c * 12.0 + offset
            slit = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, y, wall / 2.0))
                .box(slit_len, wall * 0.9, wall + 2.0)
            )
            body = body.cut(slit)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "solid":
    result = _diamond()
elif target_part == "swatch":
    result = build_swatch()
else:
    result = build_gusset()
