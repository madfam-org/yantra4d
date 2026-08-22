"""Thimble — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The closed-top tailor's thimble of the sewing room — the domed cap that rides the middle
finger and drives a hand needle through heavy cloth without piercing the fingertip. Sized
from a measured finger girth (the same circumference measure the Fashion Cabinet garment
side uses for glove and cuff fits), so a maker prints their own size rather than hunting a
0-12 retail size run.

Modes (dispatched via `target_part`):
  * "thimble" — one closed-top thimble.
  * "set"     — a three-size run (girth, girth +4 mm, girth +8 mm) laid out for one plate.

Geometry: a revolved wall profile (a straight outer flank turning through a shoulder into
a flat crown) — never a cylinder unioned with a sphere cap, which cracks at the seam. The
grip dimples are DEBOSSED: small spheres are cut into the crown and flank so the needle eye
seats in a pocket instead of skating off a bump. Open at the bottom, so no sealed void.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `finger_girth`).
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
finger_girth = float(PARAM(lambda: finger_girth, 56.0))  # measured finger circumference (mm)
wall_t       = float(PARAM(lambda: wall_t,       1.6))   # shell wall thickness (mm)
thimble_h    = float(PARAM(lambda: thimble_h,    22.0))  # overall height incl. crown (mm)
dimple_dia   = float(PARAM(lambda: dimple_dia,   1.8))   # debossed dimple diameter (mm)
dimple_rows  = int(  PARAM(lambda: dimple_rows,  4))     # rings of dimples down the flank
taper        = float(PARAM(lambda: taper,        1.2))   # crown-to-rim taper per side (mm)

target_part = str(PARAM(lambda: target_part, "thimble"))  # thimble|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
finger_girth = max(40.0, min(finger_girth, 80.0))
wall_t       = max(1.0, min(wall_t, 3.0))
thimble_h    = max(14.0, min(thimble_h, 32.0))
dimple_dia   = max(0.8, min(dimple_dia, 3.0))
dimple_rows  = max(0, min(dimple_rows, 8))
taper        = max(0.0, min(taper, 3.0))


def build_thimble(girth):
    """Revolve a closed-top wall profile, then deboss the grip dimples."""
    r_rim = girth / (2.0 * math.pi) + wall_t          # outer radius at the open rim
    r_crown = max(r_rim - taper, wall_t + 1.0)        # outer radius at the crown
    crown_t = wall_t * 1.6                            # crown is thicker — it takes the needle
    shoulder = min(r_crown * 0.55, thimble_h * 0.30)  # height of the domed shoulder

    # Half-profile in the XZ plane, revolved about Z. Outer flank rises from the rim,
    # tapers in, rounds over the shoulder to a flat crown; inner wall returns down.
    pts = [
        (r_rim, 0.0),
        (r_crown, thimble_h - shoulder),
        (r_crown * 0.72, thimble_h - shoulder * 0.30),
        (r_crown * 0.34, thimble_h),
        (0.0, thimble_h),
        (0.0, thimble_h - crown_t),
        (r_crown * 0.30, thimble_h - crown_t),
        (r_crown * 0.66, thimble_h - shoulder * 0.30 - crown_t),
        (r_crown - wall_t, thimble_h - shoulder),
        (r_rim - wall_t, 0.0),
    ]
    body = cq.Workplane("XZ").polyline(pts).close().revolve(360.0, (0, 0, 0), (0, 1, 0))

    if dimple_dia <= 0.0 or dimple_rows <= 0:
        return body

    # Deboss: collect every spherical pocket into ONE compound cutter and subtract it in a
    # single boolean. Cutting the spheres one at a time is correct but pathologically slow
    # (each cut re-solves the whole shell), so batch them.
    # Bite 40 % of each sphere in — a real thimble's dimples are shallow seats, not holes —
    # and never deeper than half the wall, so a pocket can't breach into the finger bore.
    depth = min(dimple_dia * 0.40, wall_t * 0.55)
    centres = []
    flank_top = thimble_h - shoulder - dimple_dia * 0.8   # stay clear of the shoulder break
    flank_bot = dimple_dia * 1.1                          # stay clear of the open rim
    span = max(flank_top - flank_bot, 0.001)
    # The flank is a slanted line from (r_rim, 0) to (r_crown, thimble_h - shoulder):
    # seat each sphere along that face's true normal, not along a horizontal radius.
    run = r_crown - r_rim
    rise = max(thimble_h - shoulder, 0.001)
    nlen = math.hypot(run, rise)
    n_r, n_z = rise / nlen, -run / nlen                   # outward normal of the flank
    for row in range(dimple_rows):
        z = flank_bot + span * (row / float(max(dimple_rows - 1, 1)))
        if z >= flank_top + 0.001:
            continue
        r_face = r_rim + run * min(z / rise, 1.0)
        # 3.2 x diameter of circumferential pitch, NOT 2.6: at the tighter pitch adjacent
        # pockets intersect each other and leave knife-edge webs between them that OCCT
        # cannot stitch — the mesh then reads as dozens of zero-volume bodies.
        count = max(6, int(2.0 * math.pi * r_face / (dimple_dia * 3.2)))
        stagger = math.pi / count if row % 2 else 0.0
        off = dimple_dia / 2.0 - depth                    # centre offset along the normal
        seat_r = r_face + n_r * off
        seat_z = z + n_z * off
        for i in range(count):
            a = 2.0 * math.pi * i / count + stagger
            centres.append((seat_r * math.cos(a), seat_r * math.sin(a), seat_z))

    balls = [cq.Solid.makeSphere(dimple_dia / 2.0, cq.Vector(*c), angleDegrees1=-90)
             for c in centres]
    if balls:
        body = body.cut(cq.Workplane(obj=cq.Compound.makeCompound(balls)))

    # Crown seat: ONE dished pocket in the flat crown, the needle-eye seat. Two rules here,
    # both learned the hard way: a ring of small pockets would overlap each other and the
    # crown edge and leave knife-edge webs; and a SPHERE centred on the revolve axis puts
    # its own pole on that axis, which meshes as a degenerate zero-area triangle. So the
    # seat is a REVOLVED dish whose profile has a small flat across the axis — no pole.
    crown_r = r_crown * 0.34
    seat_r = max(min(crown_r * 0.85, dimple_dia * 1.6), dimple_dia * 0.5)
    seat_depth = min(dimple_dia * 0.55, crown_t * 0.45)
    flat_r = seat_r * 0.30                       # the flat that kills the pole singularity
    z_top = thimble_h + 1.0                      # overshoot above the crown face
    seat_prof = [
        (0.0, z_top),
        (seat_r, z_top),
        (seat_r, thimble_h),
        (flat_r, thimble_h - seat_depth),
        (0.0, thimble_h - seat_depth),
    ]
    seat = (
        cq.Workplane("XZ")
        .polyline(seat_prof)
        .close()
        .revolve(360.0, (0, 0, 0), (0, 1, 0))
    )
    body = body.cut(seat)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "set":
    # Three genuinely separate thimbles: a COMPOUND, never .union() of non-touching
    # solids (that yields a "solid" whose lumps share no skin and reads as leaky).
    step = (finger_girth + 8.0) / (2.0 * math.pi) + wall_t + 7.0
    sizes = [finger_girth,
             min(finger_girth + 4.0, 80.0),
             min(finger_girth + 8.0, 80.0)]
    solids = []
    for i, g in enumerate(sizes):
        w = build_thimble(g).translate(((i - 1) * 2.0 * step, 0, 0))
        solids.extend(w.solids().vals())
    result = cq.Workplane(obj=cq.Compound.makeCompound(solids))
else:
    result = build_thimble(finger_girth)
