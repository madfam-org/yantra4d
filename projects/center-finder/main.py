"""
Center Finder / Marking Gauge — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Layout tools that scribe or find a reference line. A 90° vee registers on a round
or square end so a slot down its bisector marks dead centre; a fenced marking
gauge scribes a line a set distance from an edge; a mortise gauge scribes two
parallel lines for a mortise or tenon.

Three modes, dispatched by `target_part`:
  - center_finder : a vee-block whose bisector slot finds the centre of round or
                    square stock up to `stock_max`.
  - marking_gauge : a fence with a scribe-pin slot at a set beam length.
  - mortise_gauge : a fence with two parallel scribe-pin slots at a fixed spacing
                    for marking mortises / tenons.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `stock_max`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
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


# ── Parameters ───────────────────────────────────────────────────────────────
stock_max   = float(PARAM(lambda: stock_max,  50.0))   # largest stock the vee accepts
thick       = float(PARAM(lambda: thick,      12.0))   # tool thickness
scribe_w    = float(PARAM(lambda: scribe_w,    1.6))   # scribe pencil/pin slot width
beam_len    = float(PARAM(lambda: beam_len,   90.0))   # marking-gauge beam length
fence_h     = float(PARAM(lambda: fence_h,    30.0))   # fence height
mortise_gap = float(PARAM(lambda: mortise_gap, 8.0))   # spacing between the two scribes

target_part = str(PARAM(lambda: target_part, "center_finder"))


# ── Helpers ──────────────────────────────────────────────────────────────────
def block(w, d, h, cx=True, cy=True):
    return cq.Workplane("XY").box(w, d, h, centered=(cx, cy, False))


def scribe_channel(length, width, at, along="y"):
    """A narrow through-slot for a pencil/scribe, cut top-down."""
    if along == "y":
        cut = block(width, length, thick + 2.0).translate((at[0], 0, -1.0))
    else:
        cut = block(length, width, thick + 2.0).translate((0, at[1], -1.0))
    return cut


# ── Center finder (vee register + bisector slot) ─────────────────────────────
def build_center_finder():
    """An L/vee body: two arms meet at 90°; the inside corner is the vee. A slot
    runs along the 45° bisector — held on round or square stock, a pencil in the
    slot marks the centre line."""
    arm = stock_max * 0.9 + 15.0
    leg = stock_max * 0.6 + 12.0
    # Two arms forming a right angle opening toward +X+Y (the vee).
    ax = block(arm, leg, thick, cx=False, cy=False).translate((0, 0, 0))
    ay = block(leg, arm, thick, cx=False, cy=False)
    body = ax.union(ay)

    # Cut the vee opening: remove a square notch so an inside 90° corner remains
    # that cradles the stock; the corner apex is at (leg, leg).
    notch = block(arm, arm, thick + 2.0, cx=False, cy=False).translate((leg, leg, -1.0))
    body = body.cut(notch)

    # Bisector scribe slot along the 45° line from the apex outward.
    diag_len = arm * 1.5
    slot = (
        cq.Workplane("XY")
        .box(diag_len, scribe_w, thick + 2.0, centered=(True, True, False))
        .rotate((0, 0, 0), (0, 0, 1), 45.0)
        .translate((leg, leg, -1.0))
    )
    body = body.cut(slot)
    try:
        body = body.edges("|Z").fillet(min(thick * 0.3, 2.0))
    except Exception:
        pass
    return body


# ── Marking gauge (fence + single scribe slot) ───────────────────────────────
def build_marking_gauge():
    """A beam carrying a scribe slot, with a fence at one end that rides the
    workpiece edge. Sliding the workpiece sets the scribe distance; a pin/pencil
    drops through the slot."""
    beam = block(beam_len, thick + 8.0, thick, cx=False, cy=True)
    # Fence at the beam's near (−X) end, standing up and down from the beam so it
    # straddles the workpiece edge.
    fence = block(thick + 4.0, fence_h, fence_h, cx=True, cy=True).translate(
        (0, 0, -fence_h / 2.0 + thick / 2.0)
    )
    body = beam.union(fence)
    # Scale of scribe graduation slots along the beam (a long open slot the pin
    # rides in, so distance is adjustable).
    slot = block(beam_len - 20.0, scribe_w, thick + 2.0, cx=False, cy=True).translate(
        (15.0, 0, -1.0)
    )
    body = body.cut(slot)
    try:
        body = body.edges("|Z").fillet(min(thick * 0.25, 2.0))
    except Exception:
        pass
    return body


# ── Mortise gauge (fence + two parallel scribe slots) ────────────────────────
def build_mortise_gauge():
    """Like the marking gauge but with TWO parallel scribe slots `mortise_gap`
    apart, so both cheeks of a mortise/tenon are marked at once."""
    beam = block(beam_len, thick + mortise_gap + 12.0, thick, cx=False, cy=True)
    fence = block(thick + 4.0, fence_h, fence_h, cx=True, cy=True).translate(
        (0, 0, -fence_h / 2.0 + thick / 2.0)
    )
    body = beam.union(fence)
    for sy in (-1, 1):
        slot = block(beam_len - 20.0, scribe_w, thick + 2.0, cx=False, cy=True).translate(
            (15.0, sy * mortise_gap / 2.0, -1.0)
        )
        body = body.cut(slot)
    try:
        body = body.edges("|Z").fillet(min(thick * 0.25, 2.0))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "marking_gauge":
    result = build_marking_gauge()
elif target_part == "mortise_gauge":
    result = build_mortise_gauge()
else:
    result = build_center_finder()
