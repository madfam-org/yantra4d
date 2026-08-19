"""Bra Ring & Slider — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The ring-and-slider set that adjusts bra, camisole, and lingerie straps — the rigid hard
good the Fashion Cabinet `bra-ring-slider` notion places and bridges to here for its
geometry. The O-ring joins the strap to the cup; the figure-8 slider adjusts the length.
Printed rigid (nylon for a little give) it stands in for the metal/plastic set.

Modes (dispatched via `target_part`):
  * "set"    — ring + slider side by side.
  * "ring"   — just the O-ring.
  * "slider" — just the figure-8 slider.

Geometry: the ring is a torus (makeTorus — boolean-robust); the slider is a rounded
rectangle prism with two bar holes (a centre bar). Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strap_w`).
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
strap_w   = float(PARAM(lambda: strap_w,  12.0))     # strap width (mm)
wire_d    = float(PARAM(lambda: wire_d,   2.6))      # ring/slider section diameter (mm)
slider_h  = float(PARAM(lambda: slider_h, 5.0))      # slider height (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|ring|slider

# ── Safe clamps ──────────────────────────────────────────────────────────────
strap_w  = max(5.0, min(strap_w, 30.0))
wire_d   = max(1.5, min(wire_d, 6.0))
slider_h = max(3.0, min(slider_h, 10.0))

ring_id = strap_w + 1.0                              # ring inner opening ≈ strap width


def build_ring():
    """An O-ring: a torus sized so the strap threads it. Wrapped in a Workplane so it
    composes with the slider's Workplane via .union()."""
    r_center = (ring_id + wire_d) / 2.0
    torus = cq.Solid.makeTorus(r_center, wire_d / 2.0,
                               pnt=cq.Vector(0, 0, 0), dir=cq.Vector(0, 0, 1))
    return cq.Workplane(obj=torus)


def build_slider():
    """A figure-8 / centre-bar slider: a rounded-rect frame with two openings the strap
    weaves through, split by a centre bar."""
    outer_w = strap_w + 3.0 * wire_d
    outer_d = 2.0 * (strap_w * 0.5) + 3.0 * wire_d
    frame = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, slider_h / 2.0))
        .rect(outer_w, outer_d)
        .extrude(slider_h)
    )
    try:
        frame = frame.edges("|Z").fillet(wire_d)
    except Exception:
        pass
    # Two openings split by a centre bar (of width wire_d) along X.
    open_d = (outer_d - 3.0 * wire_d) / 2.0
    for sy in (+(wire_d / 2.0 + open_d / 2.0), -(wire_d / 2.0 + open_d / 2.0)):
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy, slider_h / 2.0))
            .box(strap_w, open_d, slider_h + 2.0)
        )
        frame = frame.cut(hole)
    return frame


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "ring":
    result = build_ring()
elif target_part == "slider":
    result = build_slider()
else:
    gap = strap_w
    result = build_ring().translate((-(ring_id / 2.0 + gap), 0, wire_d / 2.0)).union(
        build_slider().translate((strap_w, 0, 0)))
