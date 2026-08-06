"""
DIN Rail Terminal Comb — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Accessories that clip onto standard top-hat DIN rail (TS35, DIN EN 60715 —
35 mm across the lips, 7.5 mm deep) and index against the terminal-block pitch:
a jumper/feed comb that bridges adjacent terminals, an end-stop bracket that
retains a row of terminal blocks, and a marker carrier that presents labels at
terminal pitch. Grows the `din-rail-35` family.

DIN TS35 rail (DIN EN 60715, dimensionally real):
  - rail span across the two rolled lips = 35.0 mm
  - top-hat stand-off depth              = 7.5 mm
  - rolled-lip turn-back (hook grip)     ~ 5.0 mm
  - one rigid reference hook + one compliant spring hook grip the lips.

Watertight strategy:
  The clip back is a mount plate with two hooks, each an XZ profile extruded
  symmetrically about Y=0 and UNIONED with overlap into the plate. Prongs, curbs
  and label frames are unioned overlapping solids. Screw pilots, label windows
  and prong gaps are through-cuts that vent to outside. Fillet clean blanks
  BEFORE feature cuts, wrapped in try/except. No hollow posts on solid bases.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>).
  - Assign the final solid to a top-level name `result`.
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


# ── DIN TS35 rail (DIN EN 60715) — fixed real geometry ───────────────────────
RAIL_SPAN = 35.0     # width across the two rolled lips (catch-to-catch)
RAIL_DEPTH = 7.5     # how far the top-hat stands off the panel
LIP_GRIP = 5.0       # rolled-lip turn-back (hook grip depth)


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "feed_comb"))
# "feed_comb" | "end_bracket" | "marker_carrier"

pitch = float(PARAM(lambda: pitch, 5.2))            # terminal-block pitch (mm)
poles = int(PARAM(lambda: poles, 6))                # number of terminals bridged
prong_d = float(PARAM(lambda: prong_d, 2.6))        # jumper prong diameter
comb_h = float(PARAM(lambda: comb_h, 10.0))         # comb bar height above plate
label_w = float(PARAM(lambda: label_w, 4.2))        # label window width
plate_th = float(PARAM(lambda: plate_th, 4.0))      # mount-plate thickness
screw_d = float(PARAM(lambda: screw_d, 3.4))        # end-stop screw clearance (M3)

# Clamp to sane ranges so extreme UI values never crash the kernel.
pitch = max(3.5, min(pitch, 20.0))
poles = max(2, min(poles, 24))
prong_d = max(1.2, min(prong_d, min(4.0, pitch - 1.0)))
comb_h = max(4.0, min(comb_h, 40.0))
label_w = max(2.0, min(label_w, pitch - 0.6))
plate_th = max(2.5, min(plate_th, 10.0))
screw_d = max(2.5, min(screw_d, 6.0))

# ── Derived clip geometry ────────────────────────────────────────────────────
RAIL_AXIS = 24.0                   # base length along the rail (Y)
JAW_H = RAIL_DEPTH + 2.5
HOOK_WALL = 2.6
CATCH = max(1.5, min(LIP_GRIP - 1.0, 3.0))
CLEAR = 0.35


# ── DIN clip back (self-contained; copy of the din-module idiom) ─────────────
def _extrude_profile_xz(pts, length):
    """Close (x, z) points on XZ and extrude symmetrically about Y=0."""
    return cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)


def _mount_plate(width, length):
    plate = cq.Workplane("XY").box(width, length, plate_th, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(3.0, width / 6.0))
    except Exception:
        pass
    return plate


def _fixed_hook(length):
    """Rigid hook on the +X side (fixed reference jaw)."""
    x_in = RAIL_SPAN / 2.0 - CLEAR
    x_wall = RAIL_SPAN / 2.0 + HOOK_WALL
    x_catch = x_in - CATCH
    pts = [
        (x_catch, plate_th), (x_wall, plate_th),
        (x_wall, -JAW_H), (x_catch, -JAW_H),
        (x_catch, -JAW_H + HOOK_WALL), (x_in, -JAW_H + HOOK_WALL),
        (x_in, 0.0), (x_catch, 0.0),
    ]
    return _extrude_profile_xz(pts, length)


def _spring_hook(length):
    """COMPLIANT sprung hook on the -X side: a slender folded cantilever that
    flexes over the lip and springs back to grip."""
    t = 2.0
    x_lip = -RAIL_SPAN / 2.0
    x_out = x_lip - CLEAR
    x_root_in = x_lip + 7.0
    x_catch = x_out + CATCH
    outer = [
        (x_root_in, plate_th), (x_out, plate_th),
        (x_out, -JAW_H), (x_catch, -JAW_H),
    ]
    inner = [
        (x_catch, -JAW_H + t), (x_out + t, -JAW_H + t),
        (x_out + t, plate_th - t - 3.0), (x_root_in, plate_th - t - 3.0),
    ]
    beam = _extrude_profile_xz(outer + inner, length)
    relief = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x_root_in, 0.0, plate_th - 1.0))
        .box(2.0, length + 2.0, 2.2, centered=(True, True, True))
    )
    try:
        beam = beam.cut(relief)
    except Exception:
        pass
    return beam


def _clip_back(width, length):
    """Mount plate + fixed hook + spring hook, welded into one body."""
    body = _mount_plate(width, length)
    body = body.union(_fixed_hook(length))
    body = body.union(_spring_hook(length))
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_feed_comb():
    """A jumper/feed comb: a horizontal bar sitting above the DIN clip with a row
    of `poles` downward prongs at terminal `pitch`, so it bridges adjacent
    terminals of a block into one potential. Prongs are SOLID posts unioned into
    the bar (no trapped voids); the bar runs along the rail (Y)."""
    span = (poles - 1) * pitch
    length = max(RAIL_AXIS, span + 8.0)
    body = _clip_back(RAIL_SPAN + 8.0, length)

    # Comb bar above the plate, running along Y, welded with +Z overlap.
    bar = (
        cq.Workplane("XY").workplane(offset=plate_th - 0.01)
        .box(RAIL_SPAN * 0.5, span + 6.0, comb_h, centered=(True, True, False))
    )
    body = body.union(bar)

    # Row of solid prongs projecting further up in +Z at terminal pitch.
    prong_len = comb_h * 0.8
    ys = [(-span / 2.0 + i * pitch) for i in range(poles)]
    prongs = (
        cq.Workplane("XY").workplane(offset=plate_th + comb_h - 0.01)
        .pushPoints([(0.0, y) for y in ys])
        .circle(prong_d / 2.0)
        .extrude(prong_len)
    )
    body = body.union(prongs)
    return body


def build_end_bracket():
    """A terminal-block END STOP: a compact block that clips onto the rail and
    presses against the end of a terminal row so the blocks can't slide. A screw
    boss lets it be locked; the screw pilot is a through-hole (vented)."""
    length = 12.0
    body = _clip_back(RAIL_SPAN + 8.0, length)

    # Stop block rising above the plate, full rail span, welded with overlap.
    block = (
        cq.Workplane("XY").workplane(offset=plate_th - 0.01)
        .box(RAIL_SPAN + 6.0, length, comb_h + 4.0, centered=(True, True, False))
    )
    try:
        block = block.edges("|Y").fillet(1.5)
    except Exception:
        pass
    body = body.union(block)

    # Locking screw pilot through the block along Y (vents both ends).
    pilot = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, plate_th + comb_h * 0.5, -length / 2.0 - 1.0))
        .circle(screw_d / 2.0)
        .extrude(length + 2.0)
    )
    body = body.cut(pilot)
    return body


def build_marker_carrier():
    """A low marker/label carrier strip that clips on the rail and presents a row
    of `poles` label windows at terminal `pitch`, so each terminal's tag reads off
    a printed strip. Windows are through-cuts (vent). One welded body."""
    span = (poles - 1) * pitch
    length = max(RAIL_AXIS, span + 10.0)
    body = _clip_back(RAIL_SPAN + 8.0, length)

    # Label frame: a shallow raised rim above the plate carrying the windows.
    frame_h = max(3.0, comb_h * 0.5)
    frame = (
        cq.Workplane("XY").workplane(offset=plate_th - 0.01)
        .box(RAIL_SPAN * 0.6, span + 8.0, frame_h, centered=(True, True, False))
    )
    body = body.union(frame)

    # Row of label windows cut through the frame (each vents top-to-bottom).
    ys = [(-span / 2.0 + i * pitch) for i in range(poles)]
    for y in ys:
        win = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, plate_th - 1.0))
            .box(RAIL_SPAN * 0.4, label_w, frame_h + 2.0,
                 centered=(True, True, False))
        )
        body = body.cut(win)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "end_bracket":
    result = build_end_bracket()
elif target_part == "marker_carrier":
    result = build_marker_carrier()
else:
    result = build_feed_comb()
