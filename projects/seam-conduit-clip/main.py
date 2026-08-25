"""Seam Conduit Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A sew-on C-clip that routes a wire bundle along a garment's seam allowance. An e-textile
garment runs its harness inside the shell, and unless the bundle is captured it migrates,
snags in the wash, and eventually pulls a solder joint apart. This clip is stitched flat
onto the seam allowance through two flanking sew tabs, and the open C channel above the
tabs takes the bundle: push it in, and it stays put while still sliding a little so the
garment can move.

NON-GARMENT SIBLING: the existing `conduit-clip` cartridge is a BUILDING-scale part —
snap clips and standoffs that fasten EMT or metric electrical conduit to a wall with a
screw. It is sized by conduit OD and a fastener bore. This one is sized by the seam
allowance and a stitch pattern, has no screw, and is meant to flex with cloth. Same idea,
different world; do not substitute one for the other.

Modes (dispatched via `target_part`):
  * "clip"      — one sew-on C-clip.
  * "clip_run"  — a strip of clips on one plate at the pitch a harness run wants.
  * "set"       — a clip plus a closed-loop variant (a full ring, for a bundle that must
                  never escape) laid out side by side.

Geometry: the tab plate is a rounded-rect slab, chamfered on a CLEAN blank. The C channel
is a tube — outer cylinder minus an oversized bore — trimmed by a mouth cutter that
overshoots every face, then unioned into the plate with real Z overlap. The closed variant
skips the mouth cut. Separate bodies on a plate are Compounds, never unions.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bundle_dia`).
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
bundle_dia = float(PARAM(lambda: bundle_dia, 5.0))   # wire-bundle outside diameter (mm)
mouth_frac = float(PARAM(lambda: mouth_frac, 0.62))  # mouth opening / bundle diameter
wall       = float(PARAM(lambda: wall,       1.4))   # C channel wall thickness (mm)
clip_len   = float(PARAM(lambda: clip_len,   9.0))   # clip length along the bundle (mm)
tab_w      = float(PARAM(lambda: tab_w,      7.0))   # sew-tab width per side (mm)
tab_t      = float(PARAM(lambda: tab_t,      1.6))   # sew-tab plate thickness (mm)
hole_dia   = float(PARAM(lambda: hole_dia,   1.6))   # stitch hole diameter (mm)
run_count  = int(  PARAM(lambda: run_count,  4))     # clips in the clip_run layout
run_pitch  = float(PARAM(lambda: run_pitch,  45.0))  # spacing between clips in a run (mm)

target_part = str(PARAM(lambda: target_part, "clip"))  # clip|clip_run|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
bundle_dia = max(2.0, min(bundle_dia, 16.0))
mouth_frac = max(0.35, min(mouth_frac, 0.9))
wall       = max(0.8, min(wall, 3.5))
clip_len   = max(4.0, min(clip_len, 30.0))
tab_t      = max(1.0, min(tab_t, 4.0))
tab_w      = max(hole_dia * 2.0 + 2.5, min(tab_w, 20.0))
hole_dia   = max(1.0, min(hole_dia, 2.5))
run_count  = max(2, min(run_count, 8))
run_pitch  = max(clip_len + 6.0, min(run_pitch, 140.0))

# Channel geometry: the bore takes the bundle with a running fit so it can slide.
bore_r = bundle_dia / 2.0 + 0.25
outer_r = bore_r + wall
mouth_w = max(1.2, min(bundle_dia * mouth_frac, 2.0 * bore_r - 0.6))

# The channel sits above the tab plate with real overlap so the union is one solid.
overlap = min(tab_t * 0.5, 0.6)
chan_z = tab_t + outer_r - overlap

# Tab plate: spans the channel plus a sew tab on each side.
plate_w = 2.0 * outer_r + 2.0 * tab_w
plate_l = clip_len
corner_r = min(tab_w / 3.0, clip_len / 3.0, 2.0)

# Stitch holes: one per tab, centred in the tab lane.
sew_x = outer_r + tab_w / 2.0
hole_dia = min(hole_dia, max(0.8, tab_w - 2.0))


def _tab_plate():
    """Clean rounded-rect sew plate on Z=0 — chamfer HERE, before any cut."""
    return (
        cq.Workplane("XY")
        .rect(plate_w, plate_l)
        .extrude(tab_t)
        .edges("|Z")
        .fillet(corner_r)
    )


def _channel(open_mouth):
    """The C (or closed O) channel: a tube running along Y, optionally slit on top."""
    length = clip_len
    outer = (
        cq.Workplane("XZ")
        .circle(outer_r)
        .extrude(length)
        .translate((0.0, length / 2.0, 0.0))
    )
    bore = (
        cq.Workplane("XZ")
        .circle(bore_r)
        .extrude(length + 6.0)
        .translate((0.0, length / 2.0 + 3.0, 0.0))
    )
    tube = outer.cut(bore)

    if open_mouth:
        # Mouth slit through the TOP of the tube only — oversized in Y and Z so no
        # coincident faces survive, and stopping short of the bottom so the C keeps a back.
        slit_h = outer_r + wall + 2.0
        slit = (
            cq.Workplane("XY")
            .box(mouth_w, length + 6.0, slit_h)
            .translate((0.0, 0.0, bore_r * 0.25 + slit_h / 2.0))
        )
        tube = tube.cut(slit)

    return tube.translate((0.0, -length / 2.0, chan_z))


def _cut_sew_holes(solid):
    """Both stitch holes in one pass, clean through the tab plate."""
    return (
        solid.faces("<Z")
        .workplane(centerOption="CenterOfBoundBox")
        .pushPoints([(sew_x, 0.0), (-sew_x, 0.0)])
        .circle(hole_dia / 2.0)
        .cutThruAll()
    )


def build_clip(open_mouth=True):
    """Sew tab plate + C channel, unioned with real overlap, then stitched."""
    body = _tab_plate().union(_channel(open_mouth))
    return _cut_sew_holes(body)


def _compound(solids):
    """Separate bodies on one plate — a Compound, never a union of non-touching solids."""
    shapes = []
    for s in solids:
        shapes.extend(s.vals())
    return cq.Workplane(obj=cq.Compound.makeCompound(shapes))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "clip":
    result = build_clip(True)
elif target_part == "set":
    _off = plate_w / 2.0 + max(4.0, plate_w * 0.15) + plate_w / 2.0
    result = _compound([
        build_clip(True),
        build_clip(False).translate((_off, 0.0, 0.0)),
    ])
else:
    # A harness run: clips spaced along Y at the run pitch, all on one plate.
    _pieces = []
    _span = run_pitch * (run_count - 1)
    for _i in range(run_count):
        _y = -_span / 2.0 + run_pitch * _i
        _pieces.append(build_clip(True).translate((0.0, _y, 0.0)))
    result = _compound(_pieces)
