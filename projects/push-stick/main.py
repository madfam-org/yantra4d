"""
Push Stick / Push Block — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A safety pusher that keeps hands away from a table-saw blade or jointer cutter.
A heel notch at the rear hooks the trailing end of the stock to push it through;
the grip keeps the hand above and behind the cut.

Three modes, dispatched by `target_part`:
  - push_stick : a long tapered stick with a rear heel notch and a hand grip.
  - push_block : a broad flat block with a downward heel lip and a top grip, for
                 jointers and holding wide stock down and forward.
  - gripper    : a compact centred-grip pusher with front and rear heels that
                 straddles the blade to push on both sides of the cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `length`).
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
length      = float(PARAM(lambda: length,    260.0))   # overall length
body_h      = float(PARAM(lambda: body_h,     90.0))   # body height (grip stand-off)
thick       = float(PARAM(lambda: thick,      18.0))   # material thickness
heel        = float(PARAM(lambda: heel,       12.0))   # heel notch depth (stock caught)
grip_dia    = float(PARAM(lambda: grip_dia,   32.0))   # hand grip bore diameter
block_w     = float(PARAM(lambda: block_w,    80.0))   # push-block width (block/gripper)

target_part = str(PARAM(lambda: target_part, "push_stick"))


# ── Helpers ──────────────────────────────────────────────────────────────────
def grip_hole(solid, at, dia, depth_axis="y", length_through=100.0):
    """Cut a rounded hand-grip aperture through the body."""
    if depth_axis == "y":
        cutter = (
            cq.Workplane("XZ")
            .circle(dia / 2.0)
            .extrude(length_through + 2.0)
            .translate((at[0], 1.0, at[1]))
        )
    else:
        cutter = (
            cq.Workplane("XY")
            .circle(dia / 2.0)
            .extrude(length_through + 2.0)
            .translate((at[0], at[1], -1.0))
        )
    return solid.cut(cutter)


def safe_fillet(solid, sel, r):
    if r <= 0.3:
        return solid
    try:
        return solid.edges(sel).fillet(r)
    except Exception:
        return solid


# ── Push stick (long tapered, rear heel + grip) ──────────────────────────────
def build_push_stick():
    """Profiled in the X (length) / Z (height) plane, extruded `thick` in Y.
    The rear (−X) end drops to a heel that catches the stock; the front tapers."""
    x0 = -length / 2.0
    x1 = length / 2.0
    top = body_h
    heel_x = x0 + 22.0          # heel toe position
    # Side profile as a polyline (closed).
    pts = [
        (x0, 0.0),                    # rear bottom (heel foot)
        (heel_x, 0.0),                # heel toe bottom
        (heel_x, heel),               # up the heel face (catches stock)
        (x1 - 40.0, heel),            # run forward at stock height
        (x1, heel + 8.0),             # nose tapers up
        (x1, top - 20.0),             # front top
        (x1 - 60.0, top),             # top ridge
        (x0 + 30.0, top),             # rear top
        (x0, top - 30.0),             # rear top slope
    ]
    prof = cq.Workplane("XZ").polyline(pts).close()
    body = prof.extrude(thick)
    body = body.translate((0, -thick / 2.0, 0))

    # Hand grip aperture near the rear/top.
    body = grip_hole(body, (x0 + 55.0, top - 42.0), grip_dia, "y", thick)
    body = safe_fillet(body, "|Y", min(thick * 0.3, 4.0))
    return body


# ── Push block (broad, heel lip + top grip) ──────────────────────────────────
def build_push_block():
    """A flat block that rides on top of the stock; a heel lip hangs off the rear
    edge to push the trailing end, and a raised handle spans the top."""
    base = cq.Workplane("XY").box(length * 0.55, block_w, thick, centered=(True, True, False))

    # Heel lip along the rear (−X) edge, hanging below the base.
    lip = (
        cq.Workplane("XY")
        .box(thick, block_w, heel, centered=(True, True, False))
        .translate((-length * 0.55 / 2.0 + thick / 2.0, 0, -heel))
    )
    body = base.union(lip)

    # Raised handle: a bridge with a grip aperture, running along X on top.
    handle = cq.Workplane("XY").box(length * 0.45, block_w * 0.32, body_h, centered=(True, True, False))
    handle = handle.translate((0, 0, thick))
    body = body.union(handle)
    body = grip_hole(body, (0.0, thick + body_h * 0.55), grip_dia, "y", block_w)
    body = safe_fillet(body, "|Y", min(thick * 0.3, 3.0))
    return body


# ── Gripper (centred grip, front + rear heels) ───────────────────────────────
def build_gripper():
    """A compact pusher with a central vertical grip and heels front and rear so
    it can push on both sides of the blade at once."""
    base = cq.Workplane("XY").box(length * 0.40, block_w, thick, centered=(True, True, False))
    span = length * 0.40
    # Front and rear heels hanging below.
    body = base
    for sx in (-1, 1):
        lip = (
            cq.Workplane("XY")
            .box(thick, block_w, heel, centered=(True, True, False))
            .translate((sx * (span / 2.0 - thick / 2.0), 0, -heel))
        )
        body = body.union(lip)
    # Central column grip.
    col = cq.Workplane("XY").box(thick * 1.6, block_w * 0.5, body_h, centered=(True, True, False))
    col = col.translate((0, 0, thick))
    body = body.union(col)
    body = grip_hole(body, (0.0, thick + body_h * 0.5), grip_dia * 0.8, "y", block_w)
    body = safe_fillet(body, "|Y", min(thick * 0.25, 3.0))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "push_block":
    result = build_push_block()
elif target_part == "gripper":
    result = build_gripper()
else:
    result = build_push_stick()
