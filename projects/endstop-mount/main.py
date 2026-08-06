"""
Endstop / Limit-Switch Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Holds a limit switch at a repeatable position on a motion axis. The switch face
carries the Omron-style microswitch footprint — two M2 holes on ~9.5 mm centres
for a ~20 x 6 mm subminiature switch (SS / D2F family). Adjustment slots let the
trigger point be dialled in.

Modes (dispatched via `target_part`):
  * "switch_bracket"    — a flat plate with the microswitch bolt holes plus two
                          lengthwise adjustment SLOTS so the whole bracket slides
                          to set the trigger point.
  * "optical_endstop"   — a plate sized for a small optical-endstop PCB (board
                          bolt holes + a clearance window for the fork/flag).
  * "extrusion_endstop" — an L-foot for a 2020 aluminium T-slot extrusion: the
                          switch bolts to the upstand, the foot drops M5 T-nuts
                          into the slot.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `hole_span`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
# Omron SS / D2F subminiature microswitch: 2x M2 holes on ~9.5 mm centres,
# body ~20 x 6 mm. Optical endstops (Makerbot/RAMPS style) ~33 x 10 mm PCB.
hole_span   = float(PARAM(lambda: hole_span,     9.5))   # switch hole spacing (Omron ≈ 9.5)
switch_hole = float(PARAM(lambda: switch_hole,   2.2))   # switch bolt clearance (M2)
plate_t     = float(PARAM(lambda: plate_t,       3.0))   # plate thickness
plate_w     = float(PARAM(lambda: plate_w,      14.0))   # plate width (across the switch)
slot_len    = float(PARAM(lambda: slot_len,     12.0))   # adjustment slot travel
mount_d     = float(PARAM(lambda: mount_d,       5.2))   # frame/extrusion bolt (M5 T-nut)
board_len   = float(PARAM(lambda: board_len,    33.0))   # optical PCB length
board_hole  = float(PARAM(lambda: board_hole,    3.2))   # optical PCB bolt (M3)
foot_len    = float(PARAM(lambda: foot_len,     28.0))   # extrusion foot length

target_part = str(  PARAM(lambda: target_part, "switch_bracket"))
# "switch_bracket" | "optical_endstop" | "extrusion_endstop"


# ── Derived / clamped geometry ───────────────────────────────────────────────
plate_t = max(2.0, plate_t)
plate_w = max(10.0, plate_w)
hole_span = max(4.0, hole_span)
switch_r = max(0.8, switch_hole / 2.0)
mount_r = max(1.5, mount_d / 2.0)
board_r = max(1.2, board_hole / 2.0)
slot_len = max(4.0, slot_len)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _plate(length, width, thick, fillet_r):
    """A rounded rectangular plate on XY, base at z=0, centred in X/Y. Filleted as
    a clean blank (no features yet)."""
    p = cq.Workplane("XY").box(length, width, thick, centered=(True, True, False))
    fr = min(fillet_r, width / 2.0 - 0.5, length / 2.0 - 0.5)
    if fr > 0.2:
        p = p.edges("|Z").fillet(fr)
    return p


def _drill(body, pts, r, thick):
    if not pts or r <= 0.05:
        return body
    cutter = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(r)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return body.cut(cutter)


def _slot(body, cx, cy, length, r, thick, along_x=True):
    """Cut an obround slot centred at (cx,cy): a box plus rounded ends."""
    if along_x:
        box = (
            cq.Workplane("XY")
            .box(length, 2.0 * r, thick + 2.0, centered=(True, True, False))
            .translate((cx, cy, -1.0))
        )
        ends = [(cx - length / 2.0, cy), (cx + length / 2.0, cy)]
    else:
        box = (
            cq.Workplane("XY")
            .box(2.0 * r, length, thick + 2.0, centered=(True, True, False))
            .translate((cx, cy, -1.0))
        )
        ends = [(cx, cy - length / 2.0), (cx, cy + length / 2.0)]
    body = body.cut(box)
    body = _drill(body, ends, r, thick)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_switch_bracket():
    """Flat plate: two microswitch holes on `hole_span` centres, and two
    lengthwise adjustment slots so the bracket slides to set the trigger point."""
    length = hole_span + 2.0 * (switch_r + 3.0) + slot_len + 6.0
    plate = _plate(length, plate_w, plate_t, switch_r + 1.5)

    # Switch holes near one end (centred on the switch footprint).
    sx = -length / 2.0 + (switch_r + 4.0)
    sw_pts = [(sx, -hole_span / 2.0), (sx, hole_span / 2.0)]
    plate = _drill(plate, sw_pts, switch_r, plate_t)

    # Two adjustment slots near the other end (mount to the frame).
    mx = length / 2.0 - (slot_len / 2.0 + mount_r + 2.0)
    for sy in (-1, 1):
        yc = sy * (plate_w / 2.0 - mount_r - 2.0)
        plate = _slot(plate, mx, yc, slot_len, mount_r, plate_t, along_x=True)
    return plate


def build_optical_endstop():
    """Plate for a small optical-endstop PCB: board bolt holes at the board's
    length spacing, plus a clearance window through the middle for the fork/flag
    to pass. Distinct footprint and a through-window (no slots)."""
    length = board_len + 2.0 * (board_r + 4.0)
    width = max(plate_w, 12.0)
    plate = _plate(length, width, plate_t, board_r + 1.5)

    # Two PCB bolt holes on the board length (diagonal-safe: centre row).
    bx = board_len / 2.0
    pcb_pts = [(-bx, 0.0), (bx, 0.0)]
    plate = _drill(plate, pcb_pts, board_r, plate_t)

    # Clearance window for the optical fork (rectangular through-hole).
    win_w = min(width - 4.0 * board_r, width * 0.5)
    win_l = min(board_len * 0.4, 12.0)
    window = (
        cq.Workplane("XY")
        .box(win_l, win_w, plate_t + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    plate = plate.cut(window)
    return plate


def build_extrusion_endstop():
    """An L-foot for a 2020 extrusion: a horizontal foot (M5 T-nut holes on 20 mm
    centres) with a vertical upstand carrying the microswitch holes."""
    up_h = hole_span + 2.0 * (switch_r + 4.0)
    # Horizontal foot.
    foot = _plate(foot_len, plate_w, plate_t, mount_r + 1.0)
    # T-nut holes on 20 mm centres along the foot.
    n = max(1, int(foot_len // 20.0))
    if n == 1:
        foot_pts = [(0.0, 0.0)]
    else:
        start = -((n - 1) * 20.0) / 2.0
        foot_pts = [(start + i * 20.0, 0.0) for i in range(n)]
    foot = _drill(foot, foot_pts, mount_r, plate_t)

    # Vertical upstand at the foot's -X end, carrying the switch holes.
    up = _plate(up_h, plate_w, plate_t, switch_r + 1.5)
    up = up.rotate((0, 0, 0), (0, 1, 0), 90.0)
    # After +90° about Y: was z:0..plate_t → x:-plate_t..0, spans y & z about 0.
    up = up.translate((-foot_len / 2.0 + plate_t / 2.0, 0, up_h / 2.0 + plate_t))
    # Switch holes through the upstand (holes run along X → through its thickness).
    body = foot.union(up)
    hole_cut = (
        cq.Workplane("YZ")
        .workplane(offset=-foot_len / 2.0 - 1.0)
        .pushPoints([(-hole_span / 2.0, up_h / 2.0 + plate_t),
                     (hole_span / 2.0, up_h / 2.0 + plate_t)])
        .circle(switch_r)
        .extrude(plate_t + 2.0)
    )
    body = body.cut(hole_cut)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "optical_endstop":
    result = build_optical_endstop()
elif target_part == "extrusion_endstop":
    result = build_extrusion_endstop()
else:  # "switch_bracket"
    result = build_switch_bracket()
