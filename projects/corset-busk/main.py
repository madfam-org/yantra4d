"""Corset Busk — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The two-part front-closure busk of a corset — the rigid hard good the Fashion Cabinet
`printed-corset-busk` notion places and bridges to here for its geometry. One flat steel
plate carries stud knobs; the mating plate carries keyhole slots that drop over them, so
the corset front opens and closes without unlacing. A hard finding, not a textile:
printed rigid (PLA/PETG), it replaces the traditional spring-steel busk.

Modes (dispatched via `target_part`):
  * "busk"      — both plates side by side (a complete closure), print-ready.
  * "knob_side" — just the stud-knob plate.
  * "loop_side" — just the keyhole-slot plate.

Each plate is a thin box; knobs are small cylinders on posts; keyholes are a round hole
plus a slot, box/cylinder-cut through the mating plate. Boolean count is small (a handful
per plate) so a fused solid stays fast and watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `busk_len`).
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
busk_len   = float(PARAM(lambda: busk_len,   300.0))   # busk length down the front (mm)
plate_w    = float(PARAM(lambda: plate_w,    16.0))    # plate width (mm)
plate_t    = float(PARAM(lambda: plate_t,    3.0))     # plate thickness (mm)
knobs      = int(  PARAM(lambda: knobs,      5))       # number of stud knobs / keyholes
knob_dia   = float(PARAM(lambda: knob_dia,   6.0))     # knob head diameter (mm)
post_dia   = float(PARAM(lambda: post_dia,   3.5))     # knob post diameter (mm)

target_part = str( PARAM(lambda: target_part, "busk"))  # busk|knob_side|loop_side

# ── Safe clamps ──────────────────────────────────────────────────────────────
busk_len = max(120.0, min(busk_len, 500.0))
plate_w  = max(8.0, min(plate_w, 40.0))
plate_t  = max(1.5, min(plate_t, 8.0))
knobs    = max(2, min(knobs, 12))
knob_dia = max(3.0, min(knob_dia, plate_w - 2.0))
post_dia = max(1.5, min(post_dia, knob_dia - 1.0))
end_gap  = min(30.0, busk_len * 0.12)


def _knob_ys():
    if knobs == 1:
        return [busk_len / 2.0]
    usable = busk_len - 2.0 * end_gap
    step = usable / (knobs - 1)
    return [end_gap + i * step for i in range(knobs)]


def _plate(x0):
    """A flat plate on z=0, spanning X:[x0, x0+plate_w], Y:[0, busk_len]."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x0 + plate_w / 2.0, busk_len / 2.0, plate_t / 2.0))
        .box(plate_w, busk_len, plate_t)
    )


def build_knob_side(x0=0.0):
    """The stud-knob plate: a plate with knobs (post + head) standing proud on top."""
    body = _plate(x0)
    cx = x0 + plate_w / 2.0
    for y in _knob_ys():
        post = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, y, plate_t + post_dia * 0.4))
            .circle(post_dia / 2.0)
            .extrude(post_dia * 0.8)
        )
        head = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, y, plate_t + post_dia * 0.8 + plate_t * 0.4))
            .circle(knob_dia / 2.0)
            .extrude(plate_t * 0.8)
        )
        body = body.union(post).union(head)
    return body


def build_loop_side(x0=0.0):
    """The keyhole plate: a plate pierced by keyholes (a round hole + a drop slot) that
    slip over the knobs. Holes leave a margin at both edges so the plate never splits."""
    body = _plate(x0)
    cx = x0 + plate_w / 2.0
    for y in _knob_ys():
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, y, plate_t / 2.0))
            .circle(knob_dia / 2.0 + 0.4)
            .extrude(plate_t + 2.0)
            .translate((0, 0, -1.0))
        )
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, y - knob_dia * 0.6, plate_t / 2.0))
            .box(post_dia + 0.6, knob_dia, plate_t + 2.0)
        )
        body = body.cut(hole).cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "knob_side":
    result = build_knob_side()
elif target_part == "loop_side":
    result = build_loop_side()
else:
    gap = plate_w * 0.6
    result = build_knob_side(0.0).union(build_loop_side(plate_w + gap))
