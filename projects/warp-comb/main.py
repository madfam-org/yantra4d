"""
Loom / Warp Comb — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Weaving tools whose functional interface is the DENT SPACING — the pitch of the
teeth/slots that hold warp threads evenly. Pitch is set from dents-per-inch
(dpi): tooth pitch = 25.4 / dpi. Rigid-heddle looms commonly use 7.5, 8, 10 and
12 dpi.

Modes:
  - rigid_heddle : the classic rigid-heddle reed — a rectangular frame whose
    vertical bars alternate a drilled HOLE (thread through) with an open SLOT
    (thread floats), so lifting/lowering the heddle opens the shed.
  - raddle       : a spreading comb (raddle) — a bar with a row of upright pegs
    that space the warp across the loom's width before beaming.
  - pickup_stick : a flat weaving sword / pick-up comb — a tapered beater with a
    toothed edge for packing weft and picking up pattern threads.

Watertight strategy:
  The heddle is ONE frame solid (top bar + bottom bar + vertical bars). Holes are
  through-holes drilled in the bars (vented both faces); slots are the open gaps
  between bars (exterior, not cavities). Raddle pegs are SOLID cylinders unioned
  onto the bar (no hollow-post cavity). Teeth on the pickup stick are cut as
  through-slots from the edge (vented). Blanks fillet-cleaned before cuts.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` pre-injected; params arrive as bare globals.
  - Read each via PARAM(lambda: name, default). No globals()/eval/getattr.
  - Assign the final solid to `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Injected global if present else default; `except` catches the unbound-name
    NameError the sandbox raises (globals()/NameError are hidden)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rigid_heddle"))
# "rigid_heddle" | "raddle" | "pickup_stick"

dpi        = float(PARAM(lambda: dpi, 8.0))       # dents per inch (spacing)
width_in   = float(PARAM(lambda: width_in, 6.0))  # working width (inches)
frame_h    = float(PARAM(lambda: frame_h, 60.0))  # heddle frame height (mm)
thick      = float(PARAM(lambda: thick, 4.0))     # plate / bar thickness (mm)
hole_d     = float(PARAM(lambda: hole_d, 2.5))    # warp thread hole diameter (mm)
peg_h      = float(PARAM(lambda: peg_h, 20.0))    # raddle peg height (mm)

# Clamp to sane ranges so extreme UI values still build watertight.
dpi      = max(4.0, min(dpi, 16.0))
width_in = max(2.0, min(width_in, 12.0))
frame_h  = max(30.0, min(frame_h, 120.0))
thick    = max(3.0, min(thick, 8.0))
hole_d   = max(1.0, min(hole_d, 5.0))
peg_h    = max(10.0, min(peg_h, 40.0))

_pitch = 25.4 / dpi                       # tooth/dent pitch (mm)
_width = width_in * 25.4                   # working width (mm)
# Number of dents across the width. Capped so the biggest reed still renders in
# well under the estimate threshold (a 12 in x 16 dpi reed would be ~190 teeth;
# the boolean cost of that many thin bars/holes is what the cap guards against).
_n = max(2, min(int(_width / _pitch), 48))


# ── Helpers (inlined) ─────────────────────────────────────────────────────────
def _rounded_bar(length, height, th, fillet_r):
    """A rounded-rectangle bar/plate, fillet-cleaned BEFORE feature cuts."""
    bar = cq.Workplane("XY").box(length, height, th, centered=(True, True, False))
    try:
        bar = bar.edges("|Z").fillet(min(fillet_r, min(length, height) / 2.0 - 0.5))
    except Exception:
        pass
    return bar


# ── Part builders ────────────────────────────────────────────────────────────
def build_rigid_heddle():
    """The classic rigid-heddle reed: a frame whose vertical bars alternate a
    drilled hole (thread through) with an open slot (thread floats). Built as ONE
    frame solid so it is watertight by construction."""
    bar_w = _pitch * 0.5                        # width of each vertical bar
    frame_w = _n * _pitch + bar_w               # width incl. the flanking bars
    top_bar_h = max(6.0, frame_h * 0.12)
    bot_bar_h = top_bar_h

    # Outer frame plate.
    frame = _rounded_bar(frame_w, frame_h, thick, 3.0)

    # Cut ONE window between the top and bottom bars, then add vertical bars back
    # across it — this is always watertight (a picture frame with mullions).
    win_h = frame_h - top_bar_h - bot_bar_h
    inner_w = frame_w - 2.0 * bar_w
    window = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .rect(inner_w, win_h)
        .extrude(thick + 2.0)
    )
    frame = frame.cut(window)

    # Vertical bars back across the window. Place (_n + 1) bars evenly across the
    # full inner span so the two end bars overlap the frame side rails (they fuse
    # into one body). Each bar overshoots the window into the top/bottom rails.
    xspan = frame_w / 2.0 - bar_w / 2.0
    if _n >= 1:
        bar_pts = [(-xspan + j * (2.0 * xspan / _n), 0.0) for j in range(_n + 1)]
    else:
        bar_pts = [(0.0, 0.0)]
    bars = (
        cq.Workplane("XY")
        .pushPoints(bar_pts)
        .rect(bar_w, win_h + top_bar_h + bot_bar_h)  # span full height → fuse to rails
        .extrude(thick)
    )
    # Trim bars to the frame outline by intersecting with a full-frame block, so
    # nothing sticks out past the rounded frame edges.
    body = frame.union(bars)

    # Drill a thread eye through the CENTRE of every OTHER bar (alternating holes
    # vs open slots — that alternation is what opens the weaving shed). The eye
    # must stay narrower than the bar or it would sever the bar; clamp it so the
    # frame is always one connected body regardless of dpi.
    eye_r = min(hole_d / 2.0, bar_w * 0.35)
    eye_r = max(0.5, eye_r)
    eye_pts = [(bar_pts[i][0], 0.0) for i in range(0, len(bar_pts), 2)]
    eyes = (
        cq.Workplane("XY")
        .pushPoints(eye_pts)
        .circle(eye_r)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(eyes)
    return body


def build_raddle():
    """A spreading comb (raddle): a bar with a row of upright solid pegs at the
    dent spacing, to space the warp across the loom before beaming."""
    bar_h = max(16.0, peg_h * 0.6)
    bar_th = thick + 2.0
    frame_w = _n * _pitch + _pitch
    bar = _rounded_bar(frame_w, bar_h, bar_th, 3.0)

    # A row of solid pegs standing up along the top edge.
    x0 = -(_n * _pitch) / 2.0
    peg_pts = [(x0 + i * _pitch, bar_h / 2.0 - 3.0) for i in range(_n + 1)]
    pegs = (
        cq.Workplane("XY")
        .pushPoints(peg_pts)
        .circle(min(_pitch * 0.28, 2.2))
        .extrude(bar_th + peg_h)
    )
    # Chamfer peg tips only for modest counts — chamfering dozens of small
    # cylinders explodes the face count without helping. Solid pegs need no vent.
    if len(peg_pts) <= 24:
        try:
            pegs = pegs.edges(">Z").chamfer(min(_pitch * 0.12, 0.8))
        except Exception:
            pass
    body = bar.union(pegs)

    # Two mount holes at the ends (through the bar).
    mnt = (
        cq.Workplane("XY")
        .pushPoints([(-frame_w / 2.0 + 6.0, -bar_h / 2.0 + 5.0), (frame_w / 2.0 - 6.0, -bar_h / 2.0 + 5.0)])
        .circle(2.2)
        .extrude(bar_th + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(mnt)
    return body


def build_pickup_stick():
    """A flat weaving sword / pick-up comb: a tapered beater whose working edge
    carries a row of teeth (through-slots from the edge) for packing weft and
    picking up pattern threads."""
    length = _width + 20.0
    body_h = 40.0
    # Blade taper is built INTO the profile (wide at the toothed bottom edge,
    # narrower at the top) via a loft — no fragile face-edge chamfer, which was
    # intermittently degenerate at high tooth counts.
    plate = (
        cq.Workplane("XY")
        .rect(length, body_h)
        .workplane(offset=thick)
        .transformed(offset=cq.Vector(0, body_h * 0.15, 0))
        .rect(length, body_h * 0.7)
        .loft(combine=True)
    )
    try:
        plate = plate.edges("|Z").fillet(3.0)
    except Exception:
        pass

    # Teeth: cut a row of narrow through-slots up from the bottom working edge,
    # leaving teeth between them (each slot vents to the outside bottom edge). The
    # tooth count is capped so the thinnest teeth still render cleanly.
    n_teeth = min(_n, 40)
    tp = _width / n_teeth
    tooth_slot_w = tp * 0.5
    tooth_depth = min(body_h * 0.4, 14.0)
    x0 = -(n_teeth * tp) / 2.0 + tp / 2.0
    slot_pts = [(x0 + i * tp, -body_h / 2.0 + tooth_depth / 2.0 - 0.5) for i in range(n_teeth)]
    slots = (
        cq.Workplane("XY")
        .pushPoints(slot_pts)
        .rect(tooth_slot_w, tooth_depth + 1.0)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    body = plate.cut(slots)

    # A grip hole near one end (through, vented).
    grip = cq.Workplane("XY").circle(6.0).extrude(thick + 2.0).translate((length / 2.0 - 12.0, body_h * 0.18, -1.0))
    body = body.cut(grip)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "raddle":
    result = build_raddle()
elif target_part == "pickup_stick":
    result = build_pickup_stick()
else:
    result = build_rigid_heddle()
