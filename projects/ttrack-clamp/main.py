"""
T-Track Hold-Down Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Hold-down clamps for standard 3/4 in woodworking T-track (jigs, fences, drill
tables, router sleds). A T-bolt rides in the track's lower channel and passes up
through the clamp; a star knob tightens it down onto the workpiece. The FUNCTIONAL
interface is the 3/4 in (19.05 mm) track slot and the stud clearance slot that
lets the clamp slide along the track before locking.

T-track reference (imperial, the de-facto standard):
  slot mouth  = 3/4 in  = 19.05 mm    channel depth ≈ 3/8 in = 9.53 mm
  stud        = 1/4-20  (≈ 6.5 mm clearance) with a star / knob on top

Modes (dispatched via `target_part`):
  * "hold_down"  — a low pressing arm with a fore/aft stud SLOT so it reaches
                   over the workpiece edge and the stud slides to fit.
  * "step_block" — a stepped riser (staircase of ledges) so one clamp presses
                   workpieces of several thicknesses; stud slot up the spine.
  * "push_block" — an L push/stop that registers a workpiece edge sideways and
                   locks to the track through a single stud hole.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read them via PARAM(lambda: <name>, <default>) — no globals()/eval/getattr.
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


# ── T-track / stud constants (3/4 in standard) ───────────────────────────────
TRACK_SLOT = 19.05     # 3/4 in slot mouth (mm) — clamp base sits over this
STUD_TABLE = {
    "1/4-20":  6.6,    # 1/4 in clearance
    "5/16-18": 8.4,    # 5/16 in clearance
    "M6":      6.6,
    "M8":      8.6,
}


def stud_clear(key):
    return STUD_TABLE.get(str(key).strip(), STUD_TABLE["1/4-20"])


# ── Parameters ───────────────────────────────────────────────────────────────
stud         = str(  PARAM(lambda: stud,        "1/4-20"))  # stud thread → clearance
body_len     = float(PARAM(lambda: body_len,      70.0))    # length of the clamp body (mm)
body_w       = float(PARAM(lambda: body_w,        22.0))    # width across the track (mm)
body_h       = float(PARAM(lambda: body_h,        14.0))    # base body height (mm)
reach        = float(PARAM(lambda: reach,         18.0))    # how far the nose overhangs the work (mm)
slot_len     = float(PARAM(lambda: slot_len,      28.0))    # fore/aft stud-slot travel (mm)
steps        = int(  PARAM(lambda: steps,            4))    # step_block ledge count
counterbore  = bool( PARAM(lambda: counterbore,   True))    # recess the knob washer on top

target_part = str(PARAM(lambda: target_part, "hold_down"))  # hold_down|step_block|push_block


# ── Derived / clamped geometry ───────────────────────────────────────────────
stud_d = stud_clear(stud)
body_len = max(40.0, min(body_len, 160.0))
body_w = max(TRACK_SLOT - 3.0, min(body_w, 40.0))
body_h = max(8.0, min(body_h, 30.0))
reach = max(6.0, min(reach, 40.0))
slot_len = max(stud_d + 4.0, min(slot_len, body_len - 12.0))
steps = max(2, min(steps, 8))
cbore_d = stud_d * 2.6            # washer / knob flange recess
cbore_depth = min(body_h * 0.4, 5.0)


# ── Helpers ──────────────────────────────────────────────────────────────────
def _obround(length, w, dia):
    """A vertical stadium (obround) prism of overall footprint `length`×`dia`,
    height `w`, built from CadQuery's native single-wire `slot2D` (one closed
    profile — NOT a box unioned with tangent end-cap cylinders, which leaves
    zero-volume seams). Centred on the origin, extruded symmetrically in ±Z."""
    return (
        cq.Workplane("XY")
        .slot2D(max(dia + 0.01, length), dia, angle=0)
        .extrude(w)
        .translate((0, 0, -w / 2.0))
    )


def _stud_slot(body, cx, length, total_h, z_top):
    """Cut a vertical fore/aft stud slot (obround) through the body, plus an
    optional knob counterbore recessed into the top face. The counterbore is a
    RECTANGULAR pocket (planar faces only): a shallow-wide obround coaxial with
    the slot tessellates into a non-manifold arc seam, so a box pocket is used
    to keep the mesh watertight at every slot length."""
    slot = _obround(length, total_h + 4.0, stud_d).translate((cx, 0, total_h / 2.0))
    body = body.cut(slot)
    if counterbore and cbore_depth > 0.3:
        pocket = (
            cq.Workplane("XY")
            .box(length, cbore_d, cbore_depth + 0.02, centered=(True, True, False))
            .translate((cx, 0, z_top - cbore_depth))
        )
        body = body.cut(pocket)
    return body


# ── Builders ─────────────────────────────────────────────────────────────────
def build_hold_down():
    """A pressing arm: a rectangular base that spans the track, tapering to a
    lower nose that overhangs the work by `reach`. Stud slot runs fore/aft."""
    base_len = body_len
    # Main body as a wedge: full height at the back, stepping down to a nose.
    body = cq.Workplane("XY").box(base_len, body_w, body_h, centered=(True, True, False))
    # Nose: a lower lip extending in +X past the body to reach over the work.
    nose_h = max(3.0, body_h * 0.45)
    nose = (
        cq.Workplane("XY")
        .box(reach + 4.0, body_w, nose_h, centered=(False, True, False))
        .translate((base_len / 2.0 - 2.0, 0, 0))
    )
    body = body.union(nose)
    # Round the trailing top edge for print/ergonomics.
    try:
        body = body.edges("|Y and <X and >Z").fillet(min(3.0, body_h * 0.4))
    except Exception:
        pass
    # Stud slot centred over the base (biased back from the nose).
    body = _stud_slot(body, -reach * 0.25, slot_len, body_h, body_h)
    return body


def build_step_block():
    """A staircase riser: `steps` descending ledges so one clamp presses several
    workpiece heights. A single obround stud slot runs up the spine."""
    n = steps
    total_len = body_len
    step_len = total_len / n
    top_h = body_h + (n - 1) * 3.0     # each step drops 3 mm
    body = None
    for i in range(n):
        h = top_h - i * 3.0
        seg = (
            cq.Workplane("XY")
            .box(step_len + 0.02, body_w, h, centered=(False, True, False))
            .translate((-total_len / 2.0 + i * step_len, 0, 0))
        )
        body = seg if body is None else body.union(seg)
    # Stud slot fore/aft over the middle of the stack.
    body = _stud_slot(body, 0.0, slot_len, top_h, top_h)
    return body


def build_push_block():
    """An L-shaped side push / stop: a base that locks to the track and a
    vertical fence face that registers a workpiece edge. One stud hole."""
    t = max(5.0, body_h * 0.6)
    base = cq.Workplane("XY").box(body_len, body_w, t, centered=(True, True, False))
    # Vertical fence rising along the +X end.
    fence_h = body_h + reach
    fence = (
        cq.Workplane("XY")
        .box(t, body_w, fence_h, centered=(False, True, False))
        .translate((body_len / 2.0 - t, 0, 0))
    )
    body = base.union(fence)
    # Gusset web tying fence to base.
    web = (
        cq.Workplane("XZ")
        .workplane(offset=body_w / 2.0)
        .polyline([(body_len / 2.0 - t, t), (body_len / 2.0 - t, fence_h * 0.7),
                   (body_len / 2.0 - t - reach, t)])
        .close()
        .extrude(-body_w)
    )
    body = body.union(web)
    # Single stud hole through the base (no slot — a fixed stop position).
    hole = cq.Workplane("XY").cylinder(t + 2.0, stud_d / 2.0).translate((-reach, 0, t / 2.0))
    body = body.cut(hole)
    if counterbore and cbore_depth > 0.3:
        cb = (
            cq.Workplane("XY")
            .cylinder(cbore_depth + 0.02, cbore_d / 2.0)
            .translate((-reach, 0, t - cbore_depth / 2.0 + 0.01))
        )
        body = body.cut(cb)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "step_block":
    result = build_step_block()
elif target_part == "push_block":
    result = build_push_block()
else:
    result = build_hold_down()
