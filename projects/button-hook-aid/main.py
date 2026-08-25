"""Button Hook Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The one-hand buttoning aid: a generous handle and a flat rigid hook loop. The loop goes
through the buttonhole from the far side, hooks the button, and is pulled back — the button
follows through the hole. It is the standard occupational-therapy answer for arthritis,
hemiparesis, tremor, limited fine motor control, or one usable hand, and shirt cuffs are
the reason most people meet one.

Occupational-therapy sizing: a button hook's handle wants a large diameter, not a small one.
Grip strength lost to arthritis is recovered by increasing the grip circumference — the
standard built-up handle runs 28-38 mm across, against 8-10 mm for the pen-thin hospital
freebie that nobody can hold. The loop is thin spring wire in the commercial article: here
it is a flat printed loop, thin in the buttonhole direction so it passes a 2 mm buttonhole,
and deep in the pull direction so it does not fold under load.

`loop_dia` is the button diameter the loop must encircle. Shirt buttons are 11 mm (18
ligne), jacket buttons 20 mm (32 ligne), coat buttons 25 mm; the loop is sized to pass over
the button and still fit the hole it came through.

Modes (dispatched via `target_part`):
  * "aid"  — one buttoning aid.
  * "pair" — two aids: one shirt-button size, one printed as given (the usual issue is a
             pair, one for the shirt and one for the coat).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `loop_dia`).
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
grip_len   = float(PARAM(lambda: grip_len,   105.0))  # handle length (mm)
grip_w     = float(PARAM(lambda: grip_w,      32.0))  # handle width across the palm (mm)
grip_t     = float(PARAM(lambda: grip_t,      18.0))  # handle thickness (mm)
loop_dia   = float(PARAM(lambda: loop_dia,    13.0))  # button the loop must encircle (mm)
loop_t     = float(PARAM(lambda: loop_t,       1.8))  # loop wire thickness, hole-wise (mm)
loop_depth = float(PARAM(lambda: loop_depth,   6.0))  # loop wire depth, pull-wise (mm)
neck_len   = float(PARAM(lambda: neck_len,    26.0))  # neck between handle and loop (mm)
finger_scallops = int(PARAM(lambda: finger_scallops, 3))  # finger scallops on the grip

target_part = str(PARAM(lambda: target_part, "aid"))  # aid|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
grip_len   = max(50.0, min(grip_len, 200.0))
grip_w     = max(18.0, min(grip_w, 60.0))
grip_t     = max(8.0, min(grip_t, 40.0))
loop_dia   = max(6.0, min(loop_dia, 40.0))
loop_t     = max(1.0, min(loop_t, 4.0))
loop_depth = max(3.0, min(loop_depth, 14.0))
neck_len   = max(8.0, min(neck_len, 80.0))
finger_scallops = max(0, min(finger_scallops, 6))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Everything is laid out flat: length along +Y, width along X, thickness along Z from 0.
# The loop opening must clear the button by a working margin.
loop_ri = loop_dia / 2.0 + 1.2
loop_ro = loop_ri + loop_t
# The neck tapers from the handle end down to the loop's wire section.
neck_w = max(loop_t * 2.2, min(grip_w * 0.28, 9.0))
# The loop and neck are shallow in Z (they must pass a buttonhole), the handle is deep.
flat_t = min(loop_depth, grip_t)
# Vertical stations along +Y.
y_grip0 = 0.0
y_grip1 = grip_len
y_neck1 = grip_len + neck_len
y_loop_c = y_neck1 + loop_ro          # loop centre
# Scallop geometry: shallow bites out of both long sides of the handle.
scallop_r = min(grip_w * 0.22, grip_len / (2.0 * max(finger_scallops, 1) + 1.0))
scallop_pitch = grip_len * 0.62 / max(finger_scallops, 1)


def _handle():
    """The grip: a deep rounded slab, chamfered on the clean blank before any cuts."""
    body = (
        cq.Workplane("XY")
        .center(0, grip_len / 2.0)
        .rect(grip_w, grip_len)
        .extrude(grip_t)
    )
    try:
        body = body.edges("|Z").fillet(min(grip_w * 0.4, 12.0))
    except Exception:
        pass
    try:
        body = body.edges("|Y").fillet(min(grip_t * 0.3, grip_w * 0.2, 5.0))
    except Exception:
        pass
    return body


def _scallop_cutter():
    """Finger scallops: cylinders biting into both long sides of the grip.

    They are what a built-up handle gets instead of knurling — the fingers of a hand with
    limited grip find a scallop without having to close on it.
    """
    if finger_scallops <= 0:
        return None
    cutters = None
    y0 = grip_len * 0.22
    for i in range(finger_scallops):
        y = y0 + i * scallop_pitch
        for side in (-1.0, 1.0):
            # Cylinder axis along Z, overshooting both Z faces.
            cyl = (
                cq.Workplane("XY")
                .circle(scallop_r)
                .extrude(grip_t + 8.0)
                .translate((side * (grip_w / 2.0 + scallop_r * 0.62), y, -4.0))
            )
            cutters = cyl if cutters is None else cutters.union(cyl)
    return cutters


def _neck_blade():
    """The neck: a flat blade in plan view, tapering from the handle to the loop section.

    Extruded to the flat section thickness and overlapping back into the handle, so the
    union is volumetric and the whole aid still prints flat on one face.
    """
    root_w = min(grip_w * 0.55, grip_w - 2.0)
    over = 3.0
    # Run the blade a wire-thickness PAST the loop's near edge so the union bites into the
    # ring rather than meeting it face to face.
    y_end = y_neck1 + loop_t + 0.6
    blade = (
        cq.Workplane("XY")
        .moveTo(-root_w / 2.0, y_grip1 - over)
        .lineTo(root_w / 2.0, y_grip1 - over)
        .lineTo(neck_w / 2.0, y_end)
        .lineTo(-neck_w / 2.0, y_end)
        .close()
        .extrude(flat_t)
    )
    return blade


def _loop():
    """The hook loop: an open ring in plan view, thin enough to pass a buttonhole.

    Built as an outer disc minus an inner disc, then a mouth is cut on the far side so the
    loop can be slipped over the button shank. Extruded to the flat section thickness, so
    the whole aid still prints flat with no supports.
    """
    ring = (
        cq.Workplane("XY")
        .center(0, y_loop_c)
        .circle(loop_ro)
        .circle(loop_ri)
        .extrude(flat_t)
    )
    # Mouth: a wedge opening away from the handle, wide enough to admit the button shank.
    mouth_w = max(loop_t * 1.6, min(loop_dia * 0.55, loop_ri * 1.5))
    mouth = (
        cq.Workplane("XY")
        .rect(mouth_w, loop_ro * 3.0)
        .extrude(flat_t + 8.0)
        .translate((0, y_loop_c + loop_ro * 1.5, -4.0))
    )
    return ring.cut(mouth)


def build_aid():
    """One buttoning aid: handle, scallops, neck blade, hook loop — a single solid."""
    body = _handle()
    scallops = _scallop_cutter()
    if scallops is not None:
        body = body.cut(scallops)
    body = body.union(_neck_blade())
    body = body.union(_loop())
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    one = build_aid()
    bb = one.val().BoundingBox()
    gap = max(8.0, grip_w * 0.3)
    off = (bb.xlen + gap) / 2.0
    asm = cq.Assembly()
    asm.add(one.translate((-off, 0, 0)), name="aid_a", color=cq.Color("#5f8fa8"))
    # The second is laid head-to-toe, the way a pair packs on a plate.
    asm.add(one.rotate((0, 0, 0), (0, 0, 1), 180).translate((off, bb.ylen, 0)),
            name="aid_b", color=cq.Color("#4f7f98"))
    result = asm
else:
    result = build_aid()
