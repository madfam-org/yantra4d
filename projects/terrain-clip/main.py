"""
Terrain Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Modular-terrain hardware: connectors and magnet bases that let printed / boxed
terrain tiles lock together and hold their layout during play, then break down flat
for storage. Uses the ubiquitous 6x2 mm disc magnet.

Three parts (dispatched via `target_part`):
  * "magnet_base"  — a flat base plate with a grid of 6x2 mm magnet pockets, glued
                     under a terrain piece so it snaps to a steel sheet or to other
                     magnetized pieces.
  * "peg_connector"— a low dumbbell with two cylindrical pegs that plug into holes in
                     two adjacent terrain tiles, joining them edge to edge.
  * "clip"         — a U-channel clip that slides over the touching edges of two
                     panels and squeezes them together.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `mag_cols`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.

Watertight strategy: the magnet base is a solid plate with BLIND magnet pockets cut
from the underside (never through the top). The peg connector and the clip are pure
unions of extruded boxes and cylinders (all closed primitives). No sphere-tangent
unions; no through-hollows.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "magnet_base"))   # magnet_base|peg_connector|clip

magnet_d    = float(PARAM(lambda: magnet_d,   6.0))   # magnet diameter (mm)
magnet_h    = float(PARAM(lambda: magnet_h,   2.0))   # magnet pocket depth (mm)

plate_th    = float(PARAM(lambda: plate_th,   3.0))   # magnet-base plate thickness (mm)
mag_cols    = int(  PARAM(lambda: mag_cols,     2))   # magnet pockets across X
mag_rows    = int(  PARAM(lambda: mag_rows,     2))   # magnet pockets across Y
mag_pitch   = float(PARAM(lambda: mag_pitch, 20.0))   # spacing between pockets (mm)
mag_margin  = float(PARAM(lambda: mag_margin, 5.0))   # plate margin around outer pockets (mm)

peg_d       = float(PARAM(lambda: peg_d,      6.0))   # connector peg diameter (mm)
peg_h       = float(PARAM(lambda: peg_h,      6.0))   # peg height above the bar (mm)
peg_span    = float(PARAM(lambda: peg_span,  24.0))   # centre-to-centre distance of the two pegs (mm)
bar_th      = float(PARAM(lambda: bar_th,     3.0))   # connector bar thickness (mm)

clip_gap    = float(PARAM(lambda: clip_gap,   4.0))   # panel thickness the clip grips (mm)
clip_arm    = float(PARAM(lambda: clip_arm,  10.0))   # clip arm length / grip depth (mm)
clip_w      = float(PARAM(lambda: clip_w,    16.0))   # clip width along the edge (mm)
clip_wall   = float(PARAM(lambda: clip_wall,  3.0))   # clip wall thickness (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight. ────────
magnet_d   = max(2.0, min(magnet_d, 12.0))
magnet_h   = max(0.8, min(magnet_h, 4.0))
plate_th   = max(magnet_h + 0.8, min(plate_th, 8.0))
mag_cols   = max(1, min(mag_cols, 6))
mag_rows   = max(1, min(mag_rows, 6))
mag_pitch  = max(magnet_d + 4.0, min(mag_pitch, 60.0))
mag_margin = max(2.0, min(mag_margin, 15.0))
peg_d      = max(3.0, min(peg_d, 12.0))
peg_h      = max(3.0, min(peg_h, 20.0))
peg_span   = max(peg_d + 6.0, min(peg_span, 80.0))
bar_th     = max(2.0, min(bar_th, 8.0))
clip_gap   = max(1.5, min(clip_gap, 20.0))
clip_arm   = max(4.0, min(clip_arm, 30.0))
clip_w     = max(6.0, min(clip_w, 40.0))
clip_wall  = max(1.6, min(clip_wall, 6.0))


# ── Magnet base ────────────────────────────────────────────────────────────────
def build_magnet_base():
    """Flat plate with a grid of blind magnet pockets in the underside."""
    plate_w = (mag_cols - 1) * mag_pitch + magnet_d + 2.0 * mag_margin
    plate_d = (mag_rows - 1) * mag_pitch + magnet_d + 2.0 * mag_margin
    body = cq.Workplane("XY").box(plate_w, plate_d, plate_th, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(mag_margin, 3.0))
    except Exception:
        pass

    x0 = -((mag_cols - 1) * mag_pitch) / 2.0
    y0 = -((mag_rows - 1) * mag_pitch) / 2.0
    pockets = None
    for r in range(mag_rows):
        for c in range(mag_cols):
            cx = x0 + c * mag_pitch
            cy = y0 + r * mag_pitch
            pk = (
                cq.Workplane("XY")           # from the underside (z=0), blind upward
                .center(cx, cy).circle(magnet_d / 2.0).extrude(magnet_h)
            )
            pockets = pk if pockets is None else pockets.union(pk)
    if pockets is not None:
        body = body.cut(pockets)
    return body


# ── Peg connector ────────────────────────────────────────────────────────────
def build_peg_connector():
    """A low bar with two upward pegs that plug into holes in adjacent tiles."""
    bar_len = peg_span + peg_d + 8.0
    bar_wid = peg_d + 6.0
    bar = cq.Workplane("XY").box(bar_len, bar_wid, bar_th, centered=(True, True, False))
    try:
        bar = bar.edges("|Z").fillet(min(bar_wid * 0.35, 4.0))
    except Exception:
        pass
    body = bar
    for sx in (-1.0, 1.0):
        x = sx * peg_span / 2.0
        peg = (
            cq.Workplane("XY").workplane(offset=bar_th)
            .center(x, 0).circle(peg_d / 2.0).extrude(peg_h)
        )
        # chamfer the peg tip so it self-locates into the hole
        try:
            peg = peg.edges(">Z").chamfer(min(peg_d * 0.25, 1.2))
        except Exception:
            pass
        body = body.union(peg)
    return body


# ── Clip ──────────────────────────────────────────────────────────────────────
def build_clip():
    """A U-channel clip: a spine plus two arms forming a slot of width `clip_gap`
    that grips two touching panels. All boxes — fully manifold."""
    slot = clip_gap
    arm_t = clip_wall
    outer_x = slot + 2.0 * arm_t

    # Spine (the closed back of the U), lying flat at the bottom.
    spine = cq.Workplane("XY").box(outer_x, clip_w, clip_wall, centered=(True, True, False))
    body = spine
    # Two arms rising from the spine ends.
    for sx in (-1.0, 1.0):
        x = sx * (slot / 2.0 + arm_t / 2.0)
        arm = (
            cq.Workplane("XY").workplane(offset=clip_wall)
            .center(x, 0).box(arm_t, clip_w, clip_arm, centered=(True, True, False))
        )
        body = body.union(arm)
    # A small inward lip at each arm tip to retain the panels (a gentle snap).
    lip_h = min(clip_wall, 2.0)
    lip_x = max(0.6, arm_t * 0.5)
    for sx in (-1.0, 1.0):
        x = sx * (slot / 2.0 - lip_x / 2.0 + 0.01)
        lip = (
            cq.Workplane("XY").workplane(offset=clip_wall + clip_arm - lip_h)
            .center(x, 0).box(lip_x, clip_w, lip_h, centered=(True, True, False))
        )
        body = body.union(lip)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "peg_connector":
    result = build_peg_connector()
elif target_part == "clip":
    result = build_clip()
else:
    result = build_magnet_base()
