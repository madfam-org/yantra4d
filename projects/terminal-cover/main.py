"""
Wire Nut / Terminal Cover — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Insulating covers, guards and barriers for terminals and busbars on a DIN rail.
The footprint follows DIN rail and DIN feed-through terminal-block dimensions, so
a printed hood drops over a real block row and a finger guard shrouds a busbar.
Pick the block width and pole count and the cover spans the row with wire-entry
slots at each end.

Modes are dispatched via `target_part`:
  * "block_cover"  — a clip-over insulating hood for a row of DIN terminal blocks:
                     an open-bottom shell with an end wire-entry slot.
  * "busbar_guard" — a finger-safe comb guard: a bar with a row of slots that let
                     conductors pass while shrouding the live metal (IP20).
  * "end_barrier"  — a single end/partition plate that clips on the DIN rail to
                     separate circuits or close off a block row.

Standards encoded (mm):
  DIN rail TS35 (EN 60715) = 35.0 wide x 7.5 deep top-hat section.
  DIN feed-through terminal block pitch ~ 5.2 (small) to 8.0 (medium); a row of
  N poles spans N * pitch. Block body height above the rail ~ 30-40 mm.

Watertightness: the hood is a solid block with a pocket cut from BELOW that opens
to the bottom face (open cavity, never sealed). Comb slots are single box cuts.
Fillet the blank BEFORE cutting.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pole_count`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Standard dimensions (mm) ─────────────────────────────────────────────────
DIN_RAIL_W = 35.0      # TS35 top-hat rail width (EN 60715)
DIN_RAIL_D = 7.5       # TS35 rail depth


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "block_cover"))
pole_count  = int(PARAM(lambda: pole_count, 6))       # number of terminal poles
pitch       = float(PARAM(lambda: pitch, 6.2))        # terminal-block pitch (mm)
height      = float(PARAM(lambda: height, 34.0))      # cover height above rail (mm)
depth       = float(PARAM(lambda: depth, 40.0))       # cover depth across the block (mm)
wall        = float(PARAM(lambda: wall, 2.0))         # shell wall thickness (mm)
slot_w      = float(PARAM(lambda: slot_w, 10.0))      # wire-entry slot width (mm)

# Clamp to sane ranges.
pole_count = max(1, min(pole_count, 24))
pitch = max(3.5, min(pitch, 16.0))
height = max(10.0, min(height, 60.0))
depth = max(12.0, min(depth, 80.0))
wall = max(1.2, min(wall, 5.0))
slot_w = max(3.0, min(slot_w, 30.0))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_block_cover():
    """Clip-over insulating hood: a solid block, hollowed from BELOW (open bottom),
    with a wire-entry slot at each end. Open cavity -> always watertight."""
    row_len = pole_count * pitch + 2.0 * wall
    outer = cq.Workplane("XY").box(row_len, depth, height, centered=(True, True, False))
    try:
        outer = outer.edges("|Z").fillet(min(2.0, wall))
    except Exception:
        pass

    # Hollow from below: a pocket that opens to the bottom face (z=0). It stops
    # `wall` short of the top so the roof stays closed — but is open to a face.
    cav = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(row_len - 2.0 * wall, depth - 2.0 * wall, height - wall + 1.0,
             centered=(True, True, False))
    )
    body = outer.cut(cav)

    # Wire-entry slots: a window at each depth-end (front & back) so conductors
    # reach the terminals. Cut from the lower part of each end wall to the bottom.
    for sy in (-1.0, 1.0):
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy * (depth / 2.0), -1.0))
            .box(min(slot_w * (pole_count * 0.5 + 1), row_len - 2.0 * wall),
                 wall * 3.0, height * 0.45 + 1.0, centered=(True, True, False))
        )
        body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_busbar_guard():
    """Finger-safe comb guard: a solid bar with a row of slots that let conductors
    pass while shrouding live metal. Each slot is a single box cut (IP20 comb)."""
    row_len = pole_count * pitch + 2.0 * wall
    bar_h = max(10.0, height * 0.5)
    bar_d = max(8.0, depth * 0.35)
    bar = cq.Workplane("XY").box(row_len, bar_d, bar_h, centered=(True, True, False))
    try:
        bar = bar.edges("|Z").fillet(min(1.5, wall))
    except Exception:
        pass

    # Comb slots: one per pole, opening from the top, stopping short of the floor.
    slot_gap = pitch * 0.55
    x0 = -(pole_count - 1) * pitch / 2.0
    for i in range(pole_count):
        cx = x0 + i * pitch
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, wall))
            .box(slot_gap, bar_d + 2.0, bar_h, centered=(True, True, False))
        )
        bar = bar.cut(slot)

    try:
        bar = bar.clean()
    except Exception:
        pass
    return bar


def build_end_barrier():
    """A single end / partition plate that clips on the DIN rail: a thin plate with
    a DIN-rail-width foot notch at the bottom so it straddles the TS35 rail."""
    plate_t = max(1.2, wall)
    plate_h = height
    plate_d = depth
    body = cq.Workplane("XY").box(plate_t, plate_d, plate_h, centered=(True, True, False))
    try:
        body = body.edges("|X").fillet(min(2.0, plate_t * 0.9, 2.0))
    except Exception:
        pass

    # Rail notch: a slot at the bottom sized to the TS35 rail depth so the plate
    # seats over the rail (open to the bottom face -> no sealed void).
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(plate_t + 2.0, DIN_RAIL_W, DIN_RAIL_D + 1.0, centered=(True, True, False))
    )
    body = body.cut(notch)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "block_cover": build_block_cover,
    "busbar_guard": build_busbar_guard,
    "end_barrier": build_end_barrier,
}

result = _dispatch.get(target_part, build_block_cover)()
