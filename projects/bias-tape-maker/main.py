"""Bias Tape Maker — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The folded-channel bias tape tool: a bias-cut strip is fed in the wide mouth, the tapering
channel folds both raw edges in to the centre, and single-fold tape comes out the narrow
throat under the iron. Retail tools come in a fixed run (6/12/18/25 mm finished width); this
one is one parametric object, so a maker prints the width their pattern actually calls for.

Modes (dispatched via `target_part`):
  * "tool18" — the 18 mm finished-width tool (36 mm strip in).
  * "tool25" — the 25 mm finished-width tool (50 mm strip in).
  * "set"    — both tools side by side on one plate.

Geometry: a solid wedge shell with the folding channel CUT through it end to end. The
channel is a lofted through-cut: a wide flat slot at the mouth narrowing to the throat, so
it is genuinely open at both ends — no sealed void, and no separate top plate to weld on
(the shell stays one solid). The tail carries a pin slot for pinning the fabric on start and
a hang hole. Prints flat on its back, no supports.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tape_width`).
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
tape_width  = float(PARAM(lambda: tape_width,  18.0))  # finished tape width (mm)
fabric_t    = float(PARAM(lambda: fabric_t,    0.9))   # folded fabric stack thickness (mm)
tool_len    = float(PARAM(lambda: tool_len,    58.0))  # mouth-to-throat length (mm)
wall_t      = float(PARAM(lambda: wall_t,      2.4))   # shell wall around the channel (mm)
throat_len  = float(PARAM(lambda: throat_len,  14.0))  # parallel throat after the taper (mm)
hang_hole   = float(PARAM(lambda: hang_hole,   4.0))   # hang hole diameter (mm, 0 = none)

target_part = str(PARAM(lambda: target_part, "tool18"))  # tool18|tool25|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
tape_width  = max(6.0, min(tape_width, 50.0))
fabric_t    = max(0.4, min(fabric_t, 2.5))
tool_len    = max(30.0, min(tool_len, 120.0))
wall_t      = max(1.6, min(wall_t, 5.0))
throat_len  = max(6.0, min(throat_len, tool_len / 2.0))
hang_hole   = max(0.0, min(hang_hole, 8.0))


def build_tool(finished_w):
    """Shell + lofted through-channel + tail features, for one finished tape width."""
    finished_w = max(6.0, min(finished_w, 50.0))
    strip_w = finished_w * 2.0                 # flat bias strip that feeds in
    mouth_w = strip_w + 2.0                    # channel width at the mouth (ease)
    throat_w = finished_w + 0.6                # channel width at the throat (ease)
    slot_h = fabric_t * 2.2                    # channel height (two fabric layers + ease)
    taper_len = tool_len - throat_len

    outer_w = mouth_w + 2.0 * wall_t
    outer_h = slot_h + 2.0 * wall_t
    tail_len = 16.0

    # Outer shell: a plain block from the mouth back through the throat, plus a flat tail.
    body = (
        cq.Workplane("XY")
        .box(outer_w, tool_len, outer_h, centered=(True, False, False))
    )
    tail = (
        cq.Workplane("XY")
        .box(throat_w + 2.0 * wall_t, tail_len + 1.0, outer_h,
             centered=(True, False, False))
        .translate((0, tool_len - 1.0, 0))     # 1 mm overlap into the shell — no seam
    )
    body = body.union(tail)

    # Taper the shell's outside so it narrows with the channel: cut two wedges away.
    half_o_mouth = outer_w / 2.0
    half_o_throat = throat_w / 2.0 + wall_t
    over = outer_h + 4.0
    for sign in (1.0, -1.0):
        wedge = (
            cq.Workplane("XY")
            .polyline([
                (sign * half_o_mouth, -1.0),
                (sign * (half_o_mouth + 12.0), -1.0),
                (sign * (half_o_mouth + 12.0), taper_len + throat_len + tail_len + 1.0),
                (sign * half_o_throat, taper_len + throat_len + tail_len + 1.0),
                (sign * half_o_throat, taper_len),
            ])
            .close()
            .extrude(over)
            .translate((0, 0, -2.0))
        )
        body = body.cut(wedge)

    # Folding channel: one prismatic through-cut whose plan view tapers from the wide
    # mouth to the narrow throat and then runs straight out the back. It overshoots both
    # end faces, so the channel is genuinely open — no sealed void, and no loft needed.
    chan = (
        cq.Workplane("XY")
        .polyline([
            (-mouth_w / 2.0, -2.0), (mouth_w / 2.0, -2.0),
            (throat_w / 2.0, taper_len), (throat_w / 2.0, tool_len + tail_len + 2.0),
            (-throat_w / 2.0, tool_len + tail_len + 2.0), (-throat_w / 2.0, taper_len),
        ])
        .close()
        .extrude(slot_h)
        .translate((0, 0, wall_t))
    )
    body = body.cut(chan)

    # Fold lips: shave the top face open along the centre so the folded edges can be seen
    # and coaxed — this is the open slot every real tape maker has.
    lip_gap = max(finished_w * 0.35, 3.0)
    view_slot = (
        cq.Workplane("XY")
        .box(lip_gap, tool_len + tail_len + 4.0, wall_t + 2.0,
             centered=(True, False, False))
        .translate((0, -2.0, wall_t + slot_h - 0.5))
    )
    body = body.cut(view_slot)

    # Tail: pin slot (start the strip on a pin) and hang hole.
    pin_slot = (
        cq.Workplane("XY")
        .box(2.2, 9.0, outer_h + 4.0, centered=(True, True, False))
        .translate((0, tool_len + tail_len * 0.35, -2.0))
    )
    body = body.cut(pin_slot)
    if hang_hole > 0.05:
        hole = (
            cq.Workplane("XY")
            .circle(hang_hole / 2.0)
            .extrude(outer_h + 4.0)
            .translate((0, tool_len + tail_len * 0.82, -2.0))
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tool25":
    result = build_tool(25.0)
elif target_part == "set":
    off = tape_width * 2.0 + 26.0
    result = build_tool(18.0).translate((-off / 2.0, 0, 0))
    result = result.union(build_tool(25.0).translate((off / 2.0, 0, 0)))
else:
    result = build_tool(tape_width)
