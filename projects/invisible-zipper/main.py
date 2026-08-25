"""Invisible Zipper — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The concealed (invisible) zipper of skirts and dresses — the closure whose coil
rolls to the garment's inside so only a seam line shows on the face. This is the
rigid hard good the Fashion Cabinet `invisible-zipper` notion places and bridges
to here for its geometry; the garment cartridge owns the seam/placket math, this
owns the hardware solid.

It complements `projects/zipper` (closed-end and separating chains, coil on the
tape face). Here the coil bead sits on the BACK edge of the tape, so a sewn seam
hides it. Parameter naming is shared with `zipper` — `zip_length`, `tape_width`,
`tape_thick`, `gap` — so a Fashion Cabinet garment can drive either cartridge
from the same finished-opening number.

Modes (dispatched via `target_part`):
  * "set"    — both tapes mirrored with their closed coils adjacent, plus the
               slider parked at the bottom of the chain.
  * "tape"   — a single tape + coil bead (a repair length / one side).
  * "slider" — the slider body alone, with its pull bar and ring.

Geometry: the tape is a thin box; the coil is a cylindrical bead run along the
tape's back edge and unioned into it with a volumetric overlap (one solid, no
coincident faces). The slider is a filleted box body with a splayed tape channel
cut through it, a thin pull bar, and a ring made from `cq.Solid.makeTorus`.
No spheres, no swept arcs, no helices — small boolean count, watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `zip_length`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final result to a top-level name `result`.
"""

import math

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
zip_length  = float(PARAM(lambda: zip_length,  200.0))  # working coil length (mm)
tape_width  = float(PARAM(lambda: tape_width,    7.0))  # one tape strip width (mm)
tape_thick  = float(PARAM(lambda: tape_thick,    1.2))  # tape thickness (mm)
coil_dia    = float(PARAM(lambda: coil_dia,      2.5))  # coil bead diameter (mm)
pull_length = float(PARAM(lambda: pull_length,  25.0))  # pull bar + ring length (mm)
gap         = float(PARAM(lambda: gap,           0.35))  # print clearance (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|tape|slider

# ── Safe clamps ──────────────────────────────────────────────────────────────
zip_length  = max(60.0, min(zip_length, 600.0))
tape_width  = max(5.0, min(tape_width, 15.0))
tape_thick  = max(0.8, min(tape_thick, 2.5))
coil_dia    = max(1.5, min(coil_dia, 4.0))
pull_length = max(10.0, min(pull_length, 40.0))
gap         = max(0.1, min(gap, 1.0))

# Cross-parameter clamps — make invalid combinations impossible.
# The bead must stay thicker than the tape it rides on, and must not swallow the
# tape's sewn allowance.
coil_dia = max(coil_dia, tape_thick + 0.4)
coil_dia = min(coil_dia, tape_width * 0.6)
# Clearance can never exceed a third of the bead, or the halves would not mesh.
gap = min(gap, coil_dia / 3.0)

# ── Derived geometry constants ───────────────────────────────────────────────
_coil_r = coil_dia / 2.0
# The bead overlaps into the tape by this much so tape+coil fuse into one solid.
_overlap = min(_coil_r * 0.5, tape_thick * 0.6)
# Slider proportions, driven by the chain it rides.
_sl_h = max(coil_dia * 3.2, 8.0)          # slider height along the zip (Z)
_sl_w = coil_dia * 2.0 + gap * 2.0 + 3.0  # slider width across the chain (X)
_sl_d = coil_dia + tape_thick + 2.0       # slider depth (Y)
_bar_t = max(1.2, coil_dia * 0.45)        # pull bar thickness
_ring_r = max(2.0, pull_length * 0.22)    # pull ring major radius
_ring_t = max(0.9, _bar_t * 0.7)          # pull ring tube radius


def build_tape(mirror=False):
    """One tape strip with the coil bead fused along its BACK edge.

    Frame: the zip runs +Z from z=0. The tape spans +X from the coil edge (x=0)
    outward to x=tape_width. The bead sits behind the tape (−Y), which is the
    garment's inside — that is what makes the zipper invisible. `mirror=True`
    flips the whole half across the YZ plane for the opposite side of the seam.
    """
    tape = (
        cq.Workplane("XY")
        .box(tape_width, tape_thick, zip_length, centered=(False, True, False))
        .translate((0, 0, zip_length / 2.0))
    )
    # Soften the outer sewn edge so the strip does not print with a knife edge.
    try:
        tape = tape.edges("|Z").edges(">X").fillet(min(tape_thick * 0.35, 0.4))
    except Exception:
        pass

    # Coil bead: a cylinder running the full length, sunk behind the tape and
    # overlapping into it so the union is a single volume (no coincident faces).
    bead_y = -(tape_thick / 2.0 + _coil_r - _overlap)
    bead = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, bead_y, 0))
        .circle(_coil_r)
        .extrude(zip_length)
    )
    # Round the two bead ends into blunt caps (filleted cylinder — never a
    # sphere, whose pole reads non-watertight). Done BEFORE the union so the
    # "%CIRCLE" selector cannot also grab the tape's own fillet arcs.
    try:
        bead = bead.edges("%CIRCLE").fillet(_coil_r * 0.35)
    except Exception:
        pass

    half = tape.union(bead)

    if mirror:
        half = half.mirror("YZ")
    return half


def build_slider():
    """The concealed-zip slider: a compact teardrop body with a splayed tape
    channel cut through it, a thin pull bar, and a torus ring.

    Teardrop read comes from a filleted box tapering toward the top exit — a
    loft-to-flat frustum, never a loft to a point.
    """
    # Body: two stacked frusta lofted between flat rectangular sections, so the
    # silhouette narrows to the top exit without any singular apex.
    lower = (
        cq.Workplane("XY")
        .rect(_sl_w, _sl_d)
        .workplane(offset=_sl_h * 0.62)
        .rect(_sl_w * 0.82, _sl_d * 0.86)
        .loft()
    )
    upper = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, _sl_h * 0.62))
        .rect(_sl_w * 0.82, _sl_d * 0.86)
        .workplane(offset=_sl_h * 0.38)
        .rect(_sl_w * 0.42, _sl_d * 0.55)
        .loft()
    )
    body = lower.union(upper)
    try:
        body = body.edges("|Z").fillet(min(_sl_w, _sl_d) * 0.16)
    except Exception:
        pass

    # Tape channel: a wide slot entering the bottom (both tapes splayed apart)
    # cut clean through both faces of the lower body, plus a narrow merged exit
    # at the top. Both tools are oversized past the faces they cross.
    slot_d = tape_thick + gap * 2.0
    entry = (
        cq.Workplane("XY")
        .box(_sl_w * 2.0, slot_d, _sl_h * 0.55, centered=(True, True, False))
        .translate((0, coil_dia * 0.35, -1.0))
    )
    exit_slot = (
        cq.Workplane("XY")
        .box(coil_dia * 2.0 + gap * 2.0, slot_d, _sl_h * 0.8, centered=(True, True, False))
        .translate((0, coil_dia * 0.35, _sl_h * 0.45))
    )
    # Coil channel: the bore the closed bead pair rides through, front to back.
    coil_chan = (
        cq.Workplane("XY")
        .box(coil_dia * 2.0 + gap * 2.0, coil_dia + gap * 2.0, _sl_h + 4.0,
             centered=(True, True, False))
        .translate((0, -(coil_dia * 0.15), -2.0))
    )
    body = body.cut(entry).cut(exit_slot).cut(coil_chan)

    # Pull bar: a thin blade off the top, ending in a ring.
    bar_len = max(2.0, pull_length - _ring_r * 2.0)
    bar = (
        cq.Workplane("XY")
        .box(_bar_t * 2.2, _bar_t, bar_len + _sl_h * 0.12, centered=(True, True, False))
        .translate((0, 0, _sl_h - _sl_h * 0.12))
    )
    body = body.union(bar)

    # Pull ring: a torus (never a swept radiusArc), standing in the XZ plane.
    ring_z = _sl_h + bar_len + _ring_r
    ring = cq.Workplane(obj=cq.Solid.makeTorus(_ring_r, _ring_t))
    ring = ring.rotate((0, 0, 0), (1, 0, 0), 90.0).translate((0, 0, ring_z))
    body = body.union(ring)
    return body


def build_set():
    """Both tapes mirrored across the seam with their closed beads adjacent,
    plus the slider parked at the bottom of the chain."""
    shift = _coil_r + gap / 2.0
    left = build_tape().translate((shift, 0, 0))
    right = build_tape(mirror=True).translate((-shift, 0, 0))

    asm = cq.Assembly()
    asm.add(left, name="tape_left", color=cq.Color("#b0a890"))
    asm.add(right, name="tape_right", color=cq.Color("#b0a890"))
    asm.add(build_slider().translate((0, 0, gap + 0.5)), name="slider",
            color=cq.Color("#8a8578"))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
# The platform renders PER PART: for every id listed in a mode's `parts[]` the
# worker injects that id as `target_part`. These branches must therefore cover the
# manifest's part ids exactly — `tape_left`, `tape_right`, `slider` — or a part
# silently falls through and renders the whole set instead of itself.
_shift = _coil_r + gap / 2.0
if target_part == "slider":
    result = build_slider()
elif target_part == "tape_right":
    # The mirrored half of the seam.
    result = build_tape(mirror=True).translate((-_shift, 0, 0))
elif target_part in ("tape_left", "tape"):
    # `tape` is a legacy alias for the left half, matching the `tape` mode.
    result = build_tape().translate((_shift, 0, 0))
else:
    result = build_set()

# `math` is imported for the sandbox contract's parity with sibling cartridges;
# it backs the derived proportions below used by downstream estimators.
_chain_span = math.hypot(coil_dia + gap, tape_thick)
