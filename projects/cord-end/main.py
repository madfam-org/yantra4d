"""Cord End (Aglet & Bell Tip) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The tip that finishes a drawcord: a straight aglet (shoelace point) or a flared
bell tip for hoodie and waistband strings. It crimps onto the cord end so the
braid cannot fray or vanish back into its channel. The Fashion Cabinet `cord-end`
notion places the tip on a garment and bridges here for the solid; the companion
`cord-lock` cartridge owns the stop function, so this object is purely the tip.

Modes (dispatched via `target_part`):
  * "set"   — an aglet and a bell tip side by side.
  * "aglet" — the straight sleeve tip.
  * "bell"  — the flared cone-frustum tip.

Geometry: an outer body of diameter cord_dia + 2*wall standing on Z, with the
cord bore cut from the open mouth (z = 0) up to depth tip_length - wall, leaving a
solid closed end. The aglet body is a plain cylinder; the bell body is a cone
frustum flaring to bell_flare * outer at the mouth. The closed tip is rounded by
lofting the outer section to a SMALL FLAT circle (never to a point, never a
sphere) so no pole singularity can read non-watertight. The optional lanyard hole
is one small cylinder cut clean through both faces near the closed tip.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cord_dia`).
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
cord_dia     = float(PARAM(lambda: cord_dia,     4.0))    # cord diameter (mm)
wall         = float(PARAM(lambda: wall,         1.5))    # sleeve wall (mm)
tip_length   = float(PARAM(lambda: tip_length,  15.0))    # overall tip length (mm)
bell_flare   = float(PARAM(lambda: bell_flare,   1.4))    # mouth diameter multiplier
lanyard_hole = bool( PARAM(lambda: lanyard_hole, False))  # cross-hole near the tip

target_part = str(PARAM(lambda: target_part, "set"))  # set|aglet|bell

# ── Safe clamps ──────────────────────────────────────────────────────────────
cord_dia   = max(2.0, min(cord_dia, 8.0))
wall       = max(0.8, min(wall, 3.0))
tip_length = max(8.0, min(tip_length, 30.0))
bell_flare = max(1.0, min(bell_flare, 2.0))

# Cross-parameter clamps: the bore must leave a real solid tip and the sleeve
# must be long enough to hold the cord.
bore_r  = cord_dia / 2.0 + 0.15            # cord bore radius with a little clearance
outer_r = bore_r + wall                    # sleeve outer radius
# Keep the closed end at least `wall` thick and the bore at least 2 mm deep.
tip_length = max(tip_length, wall + 2.0)
bore_depth = max(2.0, tip_length - wall)

# The rounded closed end occupies the top of the body; keep it shorter than the
# solid cap so the loft never eats into the bore.
nose_h = min(outer_r * 0.9, max(0.6, tip_length - bore_depth - 0.2))
flat_r = max(0.35, outer_r * 0.22)         # small FLAT circle ending the nose

# Lanyard hole: small, placed in the solid cap between the bore top and the nose.
lan_r = max(0.5, min(cord_dia * 0.16, (outer_r - 0.5) / 2.0))
lan_z = bore_depth + max(0.5, (tip_length - nose_h - bore_depth) / 2.0)
# Only enable if it actually fits inside the solid cap.
lan_ok = bool(lanyard_hole) and (lan_z + lan_r + 0.3) <= (tip_length - nose_h) and lan_r >= 0.5


def _nose(base_r, z0):
    """Round the closed end by lofting `base_r` up to a small flat circle.

    Never a sphere and never a loft to a point — a flat top keeps the surface
    manifold. `z0` is the z of the loft base, the loft rises `nose_h`.
    """
    # Quarter-cosine profile: r(t) = flat + (base - flat) * cos(t * pi/2).
    span_r = base_r - flat_r
    mid_r = max(flat_r + 0.05, flat_r + span_r * math.cos(math.pi * 0.55 / 2.0))
    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(base_r)
        .workplane(offset=nose_h * 0.55)
        .circle(mid_r)
        .workplane(offset=nose_h * 0.45)
        .circle(flat_r)
        .loft(ruled=False)
    )


def _finish(body):
    """Cut the cord bore, the optional lanyard hole, and ease the mouth rim."""
    # Cord bore: open at z = 0, oversized past the bottom face so no coincident
    # surfaces, blind at the top (a real solid cap).
    bore = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .circle(bore_r)
        .extrude(bore_depth + 1.0)
    )
    body = body.cut(bore)

    if lan_ok:
        hole = (
            cq.Workplane("XZ")
            .workplane(offset=-(outer_r * bell_flare + 2.0))
            .center(0.0, lan_z)
            .circle(lan_r)
            .extrude(2.0 * (outer_r * bell_flare + 2.0))
        )
        body = body.cut(hole)

    # Ease the mouth rim (non-fatal).
    try:
        body = body.edges(cq.selectors.NearestToPointSelector((0, 0, 0))).fillet(
            min(wall * 0.3, 0.4)
        )
    except Exception:
        pass
    return body


def build_aglet():
    """Straight sleeve tip: a plain outer cylinder with a rounded closed end."""
    shaft_h = tip_length - nose_h
    body = (
        cq.Workplane("XY")
        .circle(outer_r)
        .extrude(shaft_h)
    )
    body = body.union(_nose(outer_r, shaft_h))
    return _finish(body)


def build_bell():
    """Flared tip: a cone frustum from the mouth up to the sleeve, then a nose.

    The mouth diameter is bell_flare * outer diameter; the frustum narrows over
    the lower ~55% of the length and the rest is a straight sleeve, so the bore
    always stays inside the wall.
    """
    mouth_r = outer_r * bell_flare
    flare_h = max(1.0, (tip_length - nose_h) * 0.55)
    straight_h = max(0.5, tip_length - nose_h - flare_h)

    body = (
        cq.Workplane("XY")
        .circle(mouth_r)
        .workplane(offset=flare_h)
        .circle(outer_r)
        .loft(ruled=True)
    )
    body = body.union(
        cq.Workplane("XY")
        .workplane(offset=flare_h)
        .circle(outer_r)
        .extrude(straight_h)
    )
    body = body.union(_nose(outer_r, flare_h + straight_h))
    return _finish(body)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "aglet":
    result = build_aglet()
elif target_part == "bell":
    result = build_bell()
else:
    gap = outer_r * 1.2
    span = outer_r * (1.0 + bell_flare) / 2.0 + gap / 2.0
    result = (
        build_aglet().translate((-span, 0, 0))
        .union(build_bell().translate((span, 0, 0)))
    )
