"""
Zipper — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The closure itself, not just the pull. A parametric printable zipper: two tape
strips carrying a molded coil of interlocking teeth, plus the slider that mates
them. This is the solid the Fashion Cabinet `zipper-notion` bridges to — the
garment cartridge owns the placket/seam-allowance math; this owns the hardware.

Sized to real zipper gauges: the coil `length_mm` and `tape_width_mm` map
straight from a Fashion Cabinet zipper notion (params_map: length_mm=zipper_length,
tape_width_mm=tape_width). Tooth pitch/size follow the nominal chain size (#3, #5,
#8, #10 — the standard coil widths in mm across the closed chain).

Modes (dispatched via `target_part`):
  * "closed"     — a continuous (closed-end) zipper chain: both tapes joined at
                   both ends by a bottom stop and a top stop, teeth meshed, with
                   the slider parked at the top. One printable assembly.
  * "separating" — an open-end (jacket) zipper: a box/pin retainer at the bottom
                   so the two halves fully part. Slider parked at the bottom.
  * "slider"     — the slider body alone (a Y-channel puller), for repairs.

Every part is a watertight solid (or an assembly of watertight solids). Teeth are
fused to their tape via a volumetric overlap so each tape+coil is one solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `zip_length`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final result to a top-level name `result`.
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


# ── Nominal chain sizes (mm across the closed coil) ──────────────────────────
# Standard zipper gauges. Value = closed-chain width; drives tooth size + pitch.
_CHAIN = {"3": 3.0, "5": 5.0, "8": 8.0, "10": 10.0}


# ── Parameters ───────────────────────────────────────────────────────────────
zip_length   = float(PARAM(lambda: zip_length,   200.0))   # working coil length (mm)
tape_width   = float(PARAM(lambda: tape_width,     6.0))    # single tape width (mm)
chain_size   = str(  PARAM(lambda: chain_size,    "5"))     # 3|5|8|10 nominal gauge
tape_thick   = float(PARAM(lambda: tape_thick,     1.4))    # tape thickness (mm)
gap          = float(PARAM(lambda: gap,            0.35))   # print clearance between halves (mm)

target_part  = str(  PARAM(lambda: target_part,  "closed"))  # closed|separating|slider

# ── Safe clamps ──────────────────────────────────────────────────────────────
zip_length = max(20.0, min(zip_length, 1200.0))
tape_width = max(4.0, min(tape_width, 20.0))
tape_thick = max(1.0, min(tape_thick, 3.0))
gap        = max(0.15, min(gap, 0.8))
if chain_size not in _CHAIN:
    chain_size = "5"

chain_w   = _CHAIN[chain_size]          # coil width across the meshed chain (mm)
tooth_w   = chain_w / 2.0               # each tooth reaches to the centreline
tooth_h   = chain_w * 0.9              # tooth height along tape (the pitch cell)
pitch     = tooth_h * 1.35            # centre-to-centre tooth spacing along Z
tooth_t   = max(tape_thick + 0.6, chain_w * 0.5)   # tooth thickness (out of tape plane)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _tape_strip(length, width, t):
    """A flat tape strip standing in the XZ-ish frame: length runs +Z, width runs
    +X from x=0 (the coil edge) outward, thickness centred on Y=0."""
    return (
        cq.Workplane("XY")
        .box(width, t, length, centered=(False, True, False))
        .translate((0, 0, length / 2.0))
    )


def _tooth(z):
    """One coil tooth, a rounded nub reaching from the tape edge (x=0) toward the
    centreline (+X toward -X side is mirrored by the other half). Fused into the
    tape by starting slightly inside the tape (x negative overlap)."""
    overlap = 0.8
    body = (
        cq.Workplane("XY")
        .box(tooth_w + overlap, tooth_t, tooth_h, centered=(False, True, False))
        .translate((-overlap, 0, z))
    )
    try:
        body = body.edges("|Y").fillet(min(tooth_w, tooth_h) * 0.28)
    except Exception:
        pass
    return body


def _half_coil(length, width, mirror=False):
    """One side of the zipper: a tape with a column of teeth fused along its inner
    edge. Returns a single watertight solid. `mirror=True` flips it across X so the
    two halves face each other across the centreline gap."""
    tape = _tape_strip(length, width, tape_thick)
    # Column of teeth from the first pitch cell up to the last that fits.
    n = max(1, int((length - tooth_h) / pitch))
    coil = tape
    z0 = tooth_h / 2.0 + (length - (n - 1) * pitch - tooth_h) / 2.0
    for i in range(n):
        coil = coil.union(_tooth(z0 + i * pitch))
    if mirror:
        coil = coil.mirror("YZ")
    return coil


def _slider_body():
    """The slider: a boxy puller with a Y-shaped internal channel that guides the
    two tape edges together. A hollow shell (outer box minus two angled tape slots
    minus a top exit) with a hang lug for a pull. One watertight solid."""
    w = chain_w * 2.0 + tape_width * 2.0 + gap * 2.0 + 3.0
    d = tooth_t + 2.4
    h = pitch * 2.6
    outer = cq.Workplane("XY").box(w, d, h)
    # Two tape slots entering from the bottom, splayed apart, exiting merged at top.
    slot_w = tape_width + chain_w + gap + 0.6
    slot_d = tooth_t + gap
    # Bottom (separate) slots.
    left_slot = (
        cq.Workplane("XY")
        .box(slot_w, slot_d, h * 0.75, centered=(True, True, False))
        .translate((-(chain_w / 2.0 + gap + 0.2), 0, -h / 2.0 - 0.1))
    )
    right_slot = left_slot.mirror("YZ")
    # Top (merged) exit slot.
    exit_slot = (
        cq.Workplane("XY")
        .box(chain_w + tape_width * 2.0 + gap * 2.0, slot_d, h * 0.5, centered=(True, True, False))
        .translate((0, 0, 0.05))
    )
    body = outer.cut(left_slot).cut(right_slot).cut(exit_slot)
    # Hang lug on top for the pull tab.
    lug = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h / 2.0 + chain_w * 0.6, 0))
        .box(chain_w * 1.6, chain_w * 1.4, d * 0.5)
    )
    body = body.union(lug)
    lug_hole = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h / 2.0 + chain_w * 0.7, 0))
        .cylinder(d, chain_w * 0.5)
    )
    body = body.cut(lug_hole)
    return body


def _stop(width, at_z):
    """A bottom/top stop bar: a small block clamped across one tape end that keeps
    the slider on and (for the closed zip) joins the two halves at that end."""
    return (
        cq.Workplane("XY")
        .box(chain_w * 2.0 + gap * 2.0 + width * 2.0, tooth_t + 0.8, pitch * 0.7,
             centered=(True, True, True))
        .translate((0, 0, at_z))
    )


# ── Part builders ─────────────────────────────────────────────────────────────
def build_chain(separating: bool):
    """Both tape halves side by side across the centre gap, teeth meshed, plus the
    slider and the end stops. `separating=True` puts a box/pin retainer at the
    bottom (halves fully part) and parks the slider low; otherwise both ends are
    stopped and the slider parks high. Returns an Assembly of watertight solids."""
    half_shift = chain_w / 2.0 + gap / 2.0
    left = _half_coil(zip_length, tape_width).translate((-half_shift - tape_width, 0, 0))
    # Right half is the mirror, shifted the other way, its teeth interleaved by
    # half a pitch so the coils mesh rather than collide.
    right = _half_coil(zip_length, tape_width, mirror=True).translate(
        (half_shift + tape_width, 0, pitch / 2.0)
    )

    asm = cq.Assembly()
    asm.add(left, name="tape_left", color=cq.Color("#3a5468"))
    asm.add(right, name="tape_right", color=cq.Color("#3a5468"))

    # Top stop (always) — keeps the slider from flying off the top.
    asm.add(_stop(1.0, zip_length - pitch * 0.5), name="top_stop",
            color=cq.Color("#26333f"))

    if separating:
        # Box/pin retainer block at the very bottom (the insertable pin box).
        box = (
            cq.Workplane("XY")
            .box(chain_w * 2.0 + gap * 2.0 + tape_width * 2.0, tooth_t + 1.6, pitch * 1.6,
                 centered=(True, True, False))
            .translate((0, 0, 0.0))
        )
        asm.add(box, name="pin_box", color=cq.Color("#26333f"))
        slider_z = pitch * 2.2
    else:
        asm.add(_stop(1.0, pitch * 0.5), name="bottom_stop",
                color=cq.Color("#26333f"))
        slider_z = zip_length - pitch * 2.4

    asm.add(_slider_body().translate((0, 0, slider_z)), name="slider",
            color=cq.Color("#8a99a6"))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "slider":
    result = _slider_body()
elif target_part == "separating":
    result = build_chain(separating=True)
else:
    result = build_chain(separating=False)
