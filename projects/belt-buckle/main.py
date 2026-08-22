"""Belt Buckle (center-bar + prong) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The classic center-bar belt buckle: a rounded rectangular frame with a bar across its
middle, and a prong that curls around that bar and drops into a punched belt hole. This is
the rigid hard good the Fashion Cabinet `belt-buckle` notion places and bridges to here for
its geometry — kilts, belted coats and waistcoat cinches all need this, while the sibling
`strap-buckle` cartridge covers side-release and tri-glide webbing hardware instead.

Modes (dispatched via `target_part`):
  * "set"   — frame and prong laid out side by side, ready to print together.
  * "frame" — just the frame (with its center bar, and the roller sleeve if enabled).
  * "prong" — just the prong (curl, shaft, tapered tip).

Geometry: the frame is a rounded-rect block minus an oversized rounded-rect cut, edge
filleted toward a rod-like section; the center bar is a cylinder spanning the interior at
mid-width; the prong is a cylinder shaft whose tip is a loft to a small flat circle and
whose back end is a quarter of `cq.Solid.makeTorus` (trimmed with box cuts) so it hooks the
center bar with clearance. With `roller` enabled the outer frame side is replaced by a
fatter smooth cylinder — a fused sleeve, not a free-spinning part (see docs).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strap_width`).
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
strap_width = float(PARAM(lambda: strap_width, 32.0))  # finished belt/strap width (mm)
frame_t     = float(PARAM(lambda: frame_t,     3.5))   # frame rod thickness (mm)
bar_dia     = float(PARAM(lambda: bar_dia,     3.0))   # center bar diameter (mm)
prong_d     = float(PARAM(lambda: prong_d,     3.0))   # prong shaft diameter (mm)
corner_r    = float(PARAM(lambda: corner_r,    4.0))   # frame corner radius (mm)
roller      = bool( PARAM(lambda: roller,      False))  # fatten the outer side into a sleeve

target_part = str(PARAM(lambda: target_part, "set"))   # set|frame|prong

# ── Safe clamps ──────────────────────────────────────────────────────────────
strap_width = max(15.0, min(strap_width, 50.0))
frame_t     = max(2.0, min(frame_t, 6.0))
bar_dia     = max(2.0, min(bar_dia, 6.0))
prong_d     = max(2.0, min(prong_d, 5.0))
# Corner radius can never eat more than a third of the shorter frame dimension.
corner_r    = max(1.0, min(corner_r, min(8.0, strap_width / 3.0)))

# ── Derived geometry (all cross-clamped so no combination is invalid) ────────
inner_w = strap_width + 1.5                    # strap passes through: interior span (Y)
inner_l = max(inner_w * 0.55, 14.0)            # frame interior length (X)
outer_w = inner_w + 2.0 * frame_t
outer_l = inner_l + 2.0 * frame_t
# Roller sleeve diameter: fatter than the frame rod, but never wider than the frame side.
roller_dia = min(frame_t * 1.8, frame_t + 2.5)
prong_clear = 0.45                             # prong-to-bar running clearance (mm)
# Prong curl inner radius hugs the bar plus clearance.
curl_ri = bar_dia / 2.0 + prong_clear
curl_rc = curl_ri + prong_d / 2.0              # torus centreline radius
# Prong reaches from the bar across the interior and a little past the far side.
prong_reach = inner_l * 0.5 + frame_t + 3.0


def _rounded_slab(length, width, thick, rad):
    """A rounded-rectangle slab centred at the origin, thickness along Z."""
    r = max(0.4, min(rad, min(length, width) / 2.0 - 0.2))
    return (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .translate((0, 0, -thick / 2.0))
        .edges("|Z")
        .fillet(r)
    )


def build_frame():
    """Rounded-rect frame ring + center bar (optionally a fatter roller sleeve)."""
    outer = _rounded_slab(outer_l, outer_w, frame_t, corner_r + frame_t)
    # Oversized interior cut, pushed past both Z faces so no coincident surfaces.
    inner_cut = _rounded_slab(inner_l, inner_w, frame_t + 6.0, corner_r)
    ring = outer.cut(inner_cut)
    # Round the rod section so the frame reads like bent wire rather than a flat plate.
    try:
        ring = ring.edges("|Z").fillet(frame_t * 0.35)
    except Exception:
        pass
    try:
        ring = ring.edges("%LINE").fillet(frame_t * 0.22)
    except Exception:
        pass

    # Center bar: a cylinder spanning the interior along Y at mid-length (X = 0),
    # overlapping both frame sides so the union is solid.
    bar_len = inner_w + 2.0 * frame_t + 1.0
    bar = (
        cq.Workplane("XZ")
        .circle(bar_dia / 2.0)
        .extrude(bar_len)
        .translate((0, bar_len / 2.0, 0))
    )
    body = ring.union(bar)

    if roller:
        # Swap the outer frame side (the +X rod) for a fatter smooth cylinder sleeve.
        side_x = inner_l / 2.0 + frame_t / 2.0
        # Remove the existing rod section there (oversized in Z, trimmed in Y to the span).
        strip = (
            cq.Workplane("XY")
            .box(frame_t + 0.6, inner_w, frame_t + 6.0)
            .translate((side_x, 0, 0))
        )
        body = body.cut(strip)
        sleeve_len = inner_w + 2.0 * frame_t
        sleeve = (
            cq.Workplane("XZ")
            .circle(roller_dia / 2.0)
            .extrude(sleeve_len)
            .translate((side_x, sleeve_len / 2.0, 0))
        )
        body = body.union(sleeve)
        try:
            body = body.edges("%CIRCLE").fillet(0.3)
        except Exception:
            pass
    return body


def _curl():
    """A quarter torus hooking the center bar: the prong's curled back end.

    Built from cq.Solid.makeTorus (never a swept radiusArc) and trimmed to a
    three-quarter wrap with oversized box cuts.
    """
    torus = cq.Workplane(obj=cq.Solid.makeTorus(curl_rc, prong_d / 2.0))
    # Torus lies in XY around the origin, axis Z. Rotate so its axis lies along Y —
    # matching the center bar direction.
    torus = torus.rotate((0, 0, 0), (1, 0, 0), 90)
    big = curl_rc + prong_d + 4.0
    # Trim the -X/-Z quadrant away so ~three quarters of the ring remains open toward
    # the shaft. Cut boxes are oversized in every direction (never coincident).
    cutter = (
        cq.Workplane("XY")
        .box(big, big * 2.0, big)
        .translate((-big / 2.0, 0, -big / 2.0))
    )
    return torus.cut(cutter)


def build_prong():
    """Straight shaft, lofted taper to a small flat tip, curled hook at the back end."""
    # Shaft runs along +X from the curl at the origin.
    shaft_len = max(prong_reach - curl_rc, prong_d * 2.0)
    taper_len = min(prong_d * 2.2, shaft_len * 0.45)
    body_len = shaft_len - taper_len
    x0 = curl_rc

    shaft = (
        cq.Workplane("YZ")
        .circle(prong_d / 2.0)
        .extrude(body_len)
        .translate((x0, 0, 0))
    )
    # Tip: loft to a SMALL FLAT circle (never to a point — pole singularity).
    tip = (
        cq.Workplane("YZ")
        .workplane(offset=x0 + body_len)
        .circle(prong_d / 2.0)
        .workplane(offset=taper_len)
        .circle(max(0.5, prong_d * 0.22))
        .loft(ruled=True)
    )
    body = shaft.union(tip)

    curl = _curl()
    # A short stub bridging the curl's open end into the shaft start, so the union
    # is a single solid with real overlap rather than a tangent touch.
    stub = (
        cq.Workplane("YZ")
        .circle(prong_d / 2.0)
        .extrude(curl_rc + 0.6)
        .translate((-0.3, 0, 0))
    )
    return body.union(curl).union(stub)


def _lay_out_gap():
    """Side-by-side gap for the `set` mode: frame half-width plus the prong's swing
    radius, with a printing margin. math.hypot keeps the curl's diagonal in view."""
    swing = math.hypot(curl_rc + prong_d / 2.0, prong_d)
    return outer_w / 2.0 + swing + max(frame_t * 2.0, 6.0)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "frame":
    result = build_frame()
elif target_part == "prong":
    result = build_prong()
else:
    frame = build_frame()
    # Lay the prong alongside the frame, rolled flat, clear of the frame footprint.
    prong = build_prong().rotate((0, 0, 0), (1, 0, 0), 90)
    result = frame.union(prong.translate((-prong_reach / 2.0, _lay_out_gap(), 0)))
