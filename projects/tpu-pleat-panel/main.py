"""TPU Pleat Panel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place ACCORDION-PLEATED textile panel — the additive-manufacturing fabric
that the Fashion Cabinet `tpu-pleat-panel` fabric card describes as *cloth* and bridges
to here for its geometry. A run of alternating knife folds prints flat and opens/closes
like a pleated skirt panel: rigid facet, flexible crease. Printed in TPU the thin fold
lines act as living hinges, so the panel concertinas.

This is the soft-goods↔hard-goods seam made physical (after `tpu-chainmail-panel`): the
panel is simultaneously a Fashion Cabinet FABRIC (pleat depth, drape, cut planning) and
a Yantra4D SOLID (the printable zig-zag wall). One material identity spans both —
`bambu-tpu-95a`.

Modes (dispatched via `target_part`):
  * "panel"  — the full pleated run (pleats x width), print-in-place.
  * "swatch" — a 3-pleat sample for a print/fold test.
  * "pleat"  — a single fold, for tuning depth + wall thickness.

Geometry is a fused run of angled slabs following a zig-zag centre-line — straight line
segments only (no arcs, which degenerate under sweep). Printed thin in TPU, each fold
line acts as a living hinge so the panel concertinas.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pleats`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
pleats      = int(  PARAM(lambda: pleats,      8))      # number of knife folds
pleat_depth = float(PARAM(lambda: pleat_depth, 12.0))   # fold depth (peak-to-valley, mm)
pleat_pitch = float(PARAM(lambda: pleat_pitch, 16.0))   # crease-to-crease along the run (mm)
panel_width = float(PARAM(lambda: panel_width, 200.0))  # panel width across the pleats (mm)
wall        = float(PARAM(lambda: wall,        1.2))    # facet wall thickness (mm)

target_part = str(  PARAM(lambda: target_part, "panel"))  # panel|swatch|pleat

# ── Safe clamps ──────────────────────────────────────────────────────────────
pleats      = max(1, min(pleats, 40))
pleat_depth = max(3.0, min(pleat_depth, 40.0))
pleat_pitch = max(4.0, min(pleat_pitch, 40.0))
panel_width = max(20.0, min(panel_width, 300.0))
wall        = max(0.6, min(wall, 4.0))


def _pleat_profile(n):
    """A zig-zag centre-line polyline of n pleats in the X–Z plane: alternating up/down
    ramps of run pleat_pitch and rise pleat_depth. Returns the list of (x, z) points."""
    pts = [(0.0, 0.0)]
    x = 0.0
    up = True
    for _ in range(n):
        x += pleat_pitch
        z = pleat_depth if up else 0.0
        pts.append((x, z))
        up = not up
    return pts


def build_panel(n):
    """The pleated wall: a fused run of angled slabs following the zig-zag centre-line,
    each `wall` thick and `panel_width` wide in Y. Overlap at the creases keeps the
    solid watertight; the thin printed walls flex at the fold lines."""
    pts = _pleat_profile(n)
    body = None
    for i in range(len(pts) - 1):
        (x0, z0), (x1, z1) = pts[i], pts[i + 1]
        dx, dz = x1 - x0, z1 - z0
        seg_len = (dx * dx + dz * dz) ** 0.5
        # A slab of length seg_len x panel_width x wall, oriented along the segment.
        ang = math.degrees(math.atan2(dz, dx))
        slab = (
            cq.Workplane("XY")
            .box(seg_len, panel_width, wall)
            .translate((seg_len / 2.0, 0, 0))
            .rotate((0, 0, 0), (0, 1, 0), -ang)
            .translate((x0, 0, z0))
        )
        body = slab if body is None else body.union(slab)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pleat":
    result = build_panel(1)
elif target_part == "swatch":
    result = build_panel(3)
else:
    result = build_panel(pleats)
