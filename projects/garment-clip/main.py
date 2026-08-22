"""Garment Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A print-in-place spring clip for garments: two jaws joined by an integral flexure hinge,
printed flat on the bed as a single solid with no assembly and no separate spring. Squeeze
the tails, the flexure bends, the jaws open. It clips a hanger's shoulder to hold trousers,
pins a size ticket to a sample, closes a bag of trim, or holds a hem while it is pressed.

This is a FLEXURE clip, not a torsion-spring clothespin: a printed torsion spring needs a
loose coil and an assembly step, while a flexure is one piece of material bending in its
elastic range. That constrains the material — see the PETG note in the docs.

Modes (dispatched via `target_part`):
  * "clip"    — the plain two-jaw clip.
  * "toothed" — the same with gripping ribs across both jaw faces, for slippery fabric.
  * "hanger"  — the clip with a rod loop on its spine, so it hangs on a rail on its own.

Geometry: each jaw is a rounded slab; the flexure is a thin web whose LAND thickness is
generous and whose ends blend into the jaws through overlapping blocks — never a knife
edge, which is where a printed flexure actually fails. The jaws OVERLAP the flexure
generously so the whole clip is one continuous solid with a real load path.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `jaw_len`).
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
jaw_len   = float(PARAM(lambda: jaw_len,   34.0))  # jaw length, nose to hinge (mm)
jaw_w     = float(PARAM(lambda: jaw_w,     16.0))  # jaw width across the bite (mm)
jaw_t     = float(PARAM(lambda: jaw_t,     4.0))   # jaw slab thickness (mm)
flex_t    = float(PARAM(lambda: flex_t,    1.2))   # flexure web thickness (mm)
flex_len  = float(PARAM(lambda: flex_len,  16.0))  # flexure free length (mm)
bite_gap  = float(PARAM(lambda: bite_gap,  1.6))   # open gap between the jaw faces (mm)
tooth_n   = int(  PARAM(lambda: tooth_n,   4))     # gripping ribs per jaw
rod_dia   = float(PARAM(lambda: rod_dia,   25.0))  # rail the hanger loop clears (mm)

target_part = str(PARAM(lambda: target_part, "clip"))


# ── Safe clamps ──────────────────────────────────────────────────────────────
jaw_len  = max(16.0, min(jaw_len, 80.0))
jaw_w    = max(8.0,  min(jaw_w, 45.0))
jaw_t    = max(2.0,  min(jaw_t, 9.0))
# A printed flexure below 0.8 mm is two extrusion widths and delaminates on the first
# squeeze; above a third of the jaw it stops being a spring and becomes a hinge that
# cracks. Both ends are clamped.
flex_t   = max(0.8,  min(flex_t, 3.0))
flex_t   = min(flex_t, max(0.8, jaw_t * 0.55))
flex_len = max(6.0,  min(flex_len, jaw_len * 0.9))
bite_gap = max(0.6,  min(bite_gap, 6.0))
tooth_n  = max(1,    min(tooth_n, 8))
rod_dia  = max(12.0, min(rod_dia, 45.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
# The clip lies flat on the bed: jaws in the XY plane, stacked along Z with the bite
# gap between them, flexure at the -X end joining their far edges. Printing this way
# means the flexure's layers run ALONG its bending axis, which is the only orientation
# a printed flexure survives.
half_gap = bite_gap / 2.0
z_upper = half_gap + jaw_t / 2.0
z_lower = -z_upper

# The flexure is a C: it leaves the upper jaw's back edge, swings out past the spine,
# and returns to the lower jaw's back edge. Its outer wall is a slab, and its two
# blend blocks overlap the jaws so nothing is ever butted.
spine_x = -jaw_len / 2.0
spine_out = flex_len * 0.55            # how far the C bulges behind the jaws
blend = max(jaw_t * 1.1, 3.0)          # overlap depth of the flexure into each jaw
tooth_h = min(jaw_t * 0.32, 1.2)       # rib height — shallow, so it grips without cutting


def _slab(length, width, thick, rad):
    """A rounded-rect slab in XY, centred at the origin, `thick` along Z."""
    r = max(0.4, min(rad, min(length, width) / 2.0 - 0.3))
    return (
        cq.Workplane("XY")
        .rect(length, width)
        .extrude(thick)
        .translate((0, 0, -thick / 2.0))
        .edges("|Z")
        .fillet(r)
    )


def _jaw(z):
    """One jaw slab, centred at height `z`.

    The nose end is tapered by a lead-in wedge cut on a CLEAN blank (never a
    `.chamfer()` after the flexure cuts), so the clip slides onto fabric instead of
    catching on it.
    """
    jaw = _slab(jaw_len, jaw_w, jaw_t, min(jaw_t, jaw_w * 0.2) * 0.9).translate((0, 0, z))
    # Lead-in wedge at the nose (+X end): a box rotated about Y, oversized in Y so it
    # cuts clean past both side faces.
    wedge_l = min(jaw_len * 0.22, jaw_t * 2.2)
    if wedge_l > 0.6:
        sign = 1.0 if z > 0 else -1.0
        wedge = (
            cq.Workplane("XY")
            .box(wedge_l * 2.5, jaw_w + 8.0, jaw_t * 2.5)
            .rotate((0, 0, 0), (0, 1, 0), sign * 16.0)
            .translate((jaw_len / 2.0 + wedge_l * 0.6,
                        0,
                        z + sign * (jaw_t * 0.5 + jaw_t * 1.25 - tooth_h * 0.5)))
        )
        jaw = jaw.cut(wedge)
    return jaw


def _flexure():
    """The C-shaped flexure web joining the two jaws' back edges.

    Three overlapping slabs: an upper blend that reaches INTO the upper jaw, a vertical
    outer wall, and a lower blend into the lower jaw. Every joint is a real overlap and
    the land is never thinner than `flex_t`, so there is no knife edge anywhere.
    """
    x_out = spine_x - spine_out
    # Each arm runs from `blend` INSIDE the jaw's back edge out to the outer wall, so
    # its overlap with the jaw is a real volume rather than a butt joint.
    arm_len = spine_out + blend
    arm_cx = x_out + arm_len / 2.0
    upper = (
        cq.Workplane("XY")
        .box(arm_len, jaw_w, flex_t)
        .translate((arm_cx, 0, z_upper - jaw_t / 2.0 + flex_t / 2.0))
    )
    lower = (
        cq.Workplane("XY")
        .box(arm_len, jaw_w, flex_t)
        .translate((arm_cx, 0, z_lower + jaw_t / 2.0 - flex_t / 2.0))
    )
    # Outer wall: spans the full height between the two arms, overlapping both.
    wall_h = (z_upper - jaw_t / 2.0 + flex_t) - (z_lower + jaw_t / 2.0 - flex_t)
    wall = (
        cq.Workplane("XY")
        .box(flex_t, jaw_w, wall_h)
        .translate((x_out + flex_t / 2.0, 0, 0))
    )
    return upper.union(wall).union(lower)


def _teeth():
    """Gripping ribs across both jaw faces, as a single unioned cutter-free addition.

    The ribs are ADDED (unioned), not cut — a rib added to a clean face never risks
    the sealed-void or knife-edge failures a cut rib pattern does, and it prints
    without a support.
    """
    body = None
    span = jaw_len * 0.62
    x0 = jaw_len / 2.0 - jaw_len * 0.10 - span
    rib_w = max(0.8, min(span / (tooth_n * 2.2), 2.4))
    for i in range(tooth_n):
        x = x0 + span * (i + 0.5) / float(tooth_n)
        for z, sign in ((z_upper - jaw_t / 2.0, -1.0), (z_lower + jaw_t / 2.0, 1.0)):
            # Each rib overlaps into its jaw by half its height, so it is fused, not
            # perched on the surface.
            rib = (
                cq.Workplane("XY")
                .box(rib_w, jaw_w * 0.86, tooth_h * 2.0)
                .translate((x, 0, z + sign * tooth_h * 0.5))
            )
            body = rib if body is None else body.union(rib)
    return body


def _rod_loop():
    """A closed rod loop on the clip's spine, so the clip hangs on a rail by itself.

    A closed loop (rather than an open hook) is the right shape here: the clip is
    small and a loop cannot shake off a rail. Built as a rounded slab minus an
    oversized rounded-slab bore — no torus needed and no tangency to manage.
    """
    bore_d = rod_dia + 2.4
    ring_t = max(2.4, min(jaw_t * 0.9, 5.0))
    outer_l = bore_d + ring_t * 2.0
    outer_w = min(jaw_w, bore_d + ring_t * 2.0)
    # The loop stands in the XZ plane on the spine's back face, overlapping it.
    x_out = spine_x - spine_out
    bore_w = max(4.0, outer_w - ring_t * 2.0)
    # Ring blank: a rounded slab standing in the XZ plane, centred on Y = 0.
    ring = (
        cq.Workplane("XY")
        .rect(outer_l, ring_t)
        .extrude(outer_w)
        .translate((0, 0, -outer_w / 2.0))
        .edges("|Y")
        .fillet(min(outer_l, outer_w) * 0.30)  # rounds the loop's outline in XZ
    )
    # Bore: the same shape scaled down, overshooting BOTH faces in Y so no cut surface
    # is ever coincident with the ring's own skin.
    bore = (
        cq.Workplane("XY")
        .rect(bore_d, ring_t + 8.0)
        .extrude(bore_w)
        .translate((0, 0, -bore_w / 2.0))
        .edges("|Y")
        .fillet(min(bore_d, bore_w) * 0.38)
    )
    ring = ring.cut(bore)
    # Seat it so it overlaps the flexure's outer wall along X.
    return ring.translate((x_out - outer_l / 2.0 + ring_t * 2.0, 0, 0))


def build_clip():
    """The plain clip: two jaws plus the flexure, folded in one at a time.

    Sequential unions rather than a pre-fused sub-assembly — OCCT's fuse is
    order-sensitive on this composition and the sequential form is the watertight one.
    """
    return _jaw(z_upper).union(_flexure()).union(_jaw(z_lower))


def build_toothed():
    """The clip with gripping ribs across both jaw faces, for slippery fabric."""
    body = build_clip()
    teeth = _teeth()
    if teeth is not None:
        body = body.union(teeth)
    return body


def build_hanger():
    """The toothed clip with a closed rod loop on its spine."""
    return build_toothed().union(_rod_loop())


# ── Dispatch ─────────────────────────────────────────────────────────────────
# Mode ids and part ids match the manifest exactly:
#   clip    -> parts ["clip"]
#   toothed -> parts ["toothed"]
#   hanger  -> parts ["hanger"]
if target_part == "toothed":
    result = build_toothed()
elif target_part == "hanger":
    result = build_hanger()
else:
    result = build_clip()
