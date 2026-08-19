"""D-Ring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The D-ring — the flat-bottomed loop that anchors straps, belts, and webbing on bags, packs,
and overalls — the rigid hard good the Fashion Cabinet `d-ring-slider` notion places and
bridges to here for its geometry. The straight bar takes the sewn webbing; the curved bow
takes the clip or strap. Printed rigid it stands in for the metal D-ring.

Modes (dispatched via `target_part`):
  * "d_ring" — the D-shaped ring.
  * "square" — a square/rectangular ring variant (same builder, no bow).

Geometry: an outer rounded-rectangle prism minus an inner rounded-rectangle hole, so the
ring has a flat straight side (the bar) and a rounded bow. Fillets round the bow; the
section is rectangular. Small boolean count → fast, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing`).
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
webbing   = float(PARAM(lambda: webbing,   25.0))    # webbing width the bar carries (mm)
bow_depth = float(PARAM(lambda: bow_depth, 20.0))    # how far the bow curves out (mm)
wire_t    = float(PARAM(lambda: wire_t,    4.0))     # ring section thickness (mm)
wire_h    = float(PARAM(lambda: wire_h,    5.0))     # ring section height (mm)

target_part = str(PARAM(lambda: target_part, "d_ring"))  # d_ring|square

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing   = max(10.0, min(webbing, 60.0))
bow_depth = max(8.0, min(bow_depth, 60.0))
wire_t    = max(2.0, min(wire_t, 10.0))
wire_h    = max(2.0, min(wire_h, 12.0))

# Inner opening: webbing wide (the bar length) x bow_depth deep.
inner_w = webbing
inner_d = bow_depth
outer_w = inner_w + 2.0 * wire_t
outer_d = inner_d + 2.0 * wire_t


def _rounded_rect_prism(w, d, h, r):
    """A rounded-rectangle prism centred at origin, height h in Z."""
    wp = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, h / 2.0))
        .rect(w, d)
        .extrude(h)
    )
    try:
        wp = wp.edges("|Z").fillet(min(r, min(w, d) / 2.0 - 0.1))
    except Exception:
        pass
    return wp


def build_ring(square):
    """Outer rounded prism minus inner hole. For a D-ring the bow is rounded and the bar
    side flat; for a square ring all corners are lightly rounded."""
    r_out = 0.8 if square else min(outer_d, outer_w) * 0.45
    r_in = 0.6 if square else min(inner_d, inner_w) * 0.45
    outer = _rounded_rect_prism(outer_w, outer_d, wire_h, r_out)
    inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wire_h / 2.0))
        .rect(inner_w, inner_d)
        .extrude(wire_h + 2.0)
        .translate((0, 0, -1.0))
    )
    try:
        inner = inner.edges("|Z").fillet(min(r_in, min(inner_w, inner_d) / 2.0 - 0.1))
    except Exception:
        pass
    ring = outer.cut(inner)
    if not square:
        # Flatten the bar side (−Y): trim a sliver so the bar reads straight and flat.
        trim = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -(outer_d / 2.0), wire_h / 2.0))
            .box(outer_w + 4.0, wire_t * 0.6, wire_h + 2.0)
        )
        ring = ring.cut(trim)
    return ring


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "square":
    result = build_ring(square=True)
else:
    result = build_ring(square=False)
