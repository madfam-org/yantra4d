"""Strap Ring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The strap-ring family: the plain loops a bag maker sews webbing or a leather tab around to
anchor a strap, hang a clip, or turn a corner. Three shapes cover almost every commercial
part: the O-ring (round, free-swivelling), the rectangular ring (a square loop that keeps
the webbing flat and square to the panel), and the triangle ring (a delta whose apex takes
the clip while the flat base takes the sewn tape). This is the rigid hard good the Fashion
Cabinet `strap-ring` notion places and bridges to here for its geometry.

The sibling `d-ring` cartridge covers the flat-bar D shape — the half-round loop whose
straight bar is the sewn side. That one stays as it is; pick it when you specifically want
a D. Pick this one for O, rectangular, or triangle.

Modes (dispatched via `target_part`):
  * "o_ring"        — a plain round ring.
  * "rect_ring"     — a rectangular loop.
  * "triangle_ring" — a triangular loop, flat side down.

Geometry: every ring is an outer plan outline extruded through the ring height, minus an
oversized inner outline — one boolean pair each, then fillets on the resulting rod section
guarded by try/except. No sweeps, no lofts, no post-cut chamfers.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing_w`).
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
webbing_w = float(PARAM(lambda: webbing_w, 25.0))  # webbing width the ring must pass (mm)
opening   = float(PARAM(lambda: opening,   18.0))  # clear opening across the loop (mm)
wire_t    = float(PARAM(lambda: wire_t,     4.0))  # ring rod thickness, in plan (mm)
wire_h    = float(PARAM(lambda: wire_h,     4.5))  # ring rod height, out of plan (mm)
round_r   = float(PARAM(lambda: round_r,    1.2))  # rod section rounding radius (mm)

target_part = str(PARAM(lambda: target_part, "o_ring"))  # o_ring|rect_ring|triangle_ring

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Webbing is sold in nominal 20 / 25 / 38 / 50 mm widths; rings are built to match.
webbing_w = max(10.0, min(webbing_w, 75.0))
opening   = max(6.0, min(opening, webbing_w * 2.0))
wire_t    = max(2.0, min(wire_t, 12.0))
wire_h    = max(2.0, min(wire_h, 14.0))
# The section rounding can never eat more than 45 % of the smaller rod dimension.
round_r   = max(0.2, min(round_r, min(wire_t, wire_h) * 0.45))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Inner opening: webbing_w across the bar the tape wraps, `opening` in the other axis.
inner_w = webbing_w        # X: the bar span the webbing must pass
inner_d = opening          # Y: the clear opening depth
outer_w = inner_w + 2.0 * wire_t
outer_d = inner_d + 2.0 * wire_t


def _round_section(ring):
    """Soften the rod section on all four long edges — guarded, never fatal."""
    for sel, r in (("|Z", round_r), ("%LINE", round_r * 0.6)):
        try:
            ring = ring.edges(sel).fillet(r)
        except Exception:
            pass
    return ring


def _prism(sketch, height, z0=0.0):
    """Extrude a plan sketch through `height`, sitting at z0."""
    return sketch.extrude(height).translate((0, 0, z0))


def _rect_sketch(w, d, r):
    """A rounded-rectangle plan outline centred at the origin."""
    rr = max(0.2, min(r, min(w, d) / 2.0 - 0.15))
    wp = cq.Workplane("XY").rect(w, d)
    return wp, rr


def build_o_ring():
    """A plain round ring: outer circle minus an oversized inner circle."""
    # An O-ring's clear bore is the larger of the webbing span and the opening, so a
    # folded tape genuinely passes through it regardless of which way it is threaded.
    bore = max(inner_w, inner_d)
    outer = cq.Workplane("XY").circle(bore / 2.0 + wire_t).extrude(wire_h)
    inner = (
        cq.Workplane("XY")
        .circle(bore / 2.0)
        .extrude(wire_h + 4.0)
        .translate((0, 0, -2.0))
    )
    ring = outer.cut(inner)
    try:
        ring = ring.edges("%CIRCLE").fillet(round_r)
    except Exception:
        pass
    return ring


def build_rect_ring():
    """A rectangular loop: rounded-rect outer minus an oversized rounded-rect inner."""
    o_sk, o_r = _rect_sketch(outer_w, outer_d, wire_t * 0.9)
    outer = _prism(o_sk, wire_h)
    try:
        outer = outer.edges("|Z").fillet(o_r)
    except Exception:
        pass
    i_sk, i_r = _rect_sketch(inner_w, inner_d, wire_t * 0.5)
    inner = _prism(i_sk, wire_h + 4.0, -2.0)
    try:
        inner = inner.edges("|Z").fillet(i_r)
    except Exception:
        pass
    return _round_section(outer.cut(inner))


def _triangle_sketch(width, depth):
    """An isoceles triangle plan outline: flat base on -Y, apex on +Y.

    Corners are left sharp in the sketch; the fillet pass rounds them on the solid, which
    is where a wire ring's radius actually lives.
    """
    return (
        cq.Workplane("XY")
        .moveTo(-width / 2.0, -depth / 2.0)
        .lineTo(width / 2.0, -depth / 2.0)
        .lineTo(0.0, depth / 2.0)
        .close()
    )


def build_triangle_ring():
    """A triangle ring: flat base takes the sewn tape, apex takes the clip."""
    # The inner triangle must clear the webbing across its base, so grow the outer
    # triangle by the rod thickness measured perpendicular to each face. For an
    # isoceles triangle that offset scales with the apex half-angle.
    half_a = math.atan2(inner_w / 2.0, inner_d)
    grow_x = wire_t / max(0.2, math.sin(half_a))
    grow_y = wire_t / max(0.2, math.cos(half_a)) + wire_t
    outer = _prism(_triangle_sketch(inner_w + 2.0 * grow_x, inner_d + grow_y), wire_h)
    try:
        outer = outer.edges("|Z").fillet(min(wire_t * 1.2, inner_w * 0.2))
    except Exception:
        pass
    inner = _prism(_triangle_sketch(inner_w, inner_d), wire_h + 4.0, -2.0)
    try:
        inner = inner.edges("|Z").fillet(min(wire_t * 0.6, inner_w * 0.15))
    except Exception:
        pass
    return _round_section(outer.cut(inner))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rect_ring":
    result = build_rect_ring()
elif target_part == "triangle_ring":
    result = build_triangle_ring()
else:
    result = build_o_ring()
