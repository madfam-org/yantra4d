"""Veil Comb — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A hair comb whose spine is a veil-gathering bar. The tulle of a birdcage veil, a blusher or
a mantilla is gathered along that bar and sewn through a row of slots cut down it, so the
gather is anchored to the hardware instead of hanging off a few tacking stitches.

Millinery practice: a bridal veil is attached by gathering the raw edge to a comb — the
gather is the whole craft, because it is what turns a flat rectangle of tulle into a
volume that sits on a head. Stock combs give you a plain spine and a needle; you gather by
eye and hope the fullness is even. Here the spine carries `slot_count` sew slots on a stated
`slot_pitch`, so the gather pitch is a number rather than a guess, and each slot is a slot
rather than a hole so the thread can be drawn along it as the gather is set.

Comb geometry follows the real article: teeth 25-40 mm long on a 35-50 mm spine, tapered
and rounded at the tip so they part hair instead of catching it, with the tooth row batched
into a single `pushPoints` operation.

Modes (dispatched via `target_part`):
  * "comb" — one veil comb.
  * "pair" — two combs, the standard fitting for a wide veil (one each side).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bar_length`).
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
bar_length  = float(PARAM(lambda: bar_length,  44.0))  # gathering bar / spine length (mm)
bar_h       = float(PARAM(lambda: bar_h,        7.0))  # bar height, tooth to top edge (mm)
bar_t       = float(PARAM(lambda: bar_t,        2.4))  # bar thickness (mm)
slot_count  = int(  PARAM(lambda: slot_count,     7))  # sew slots down the bar
slot_pitch  = float(PARAM(lambda: slot_pitch,   5.5))  # centre-to-centre slot spacing (mm)
slot_w      = float(PARAM(lambda: slot_w,       1.6))  # slot width along the bar (mm)
teeth       = int(  PARAM(lambda: teeth,          7))  # comb teeth (count)
tooth_len   = float(PARAM(lambda: tooth_len,   30.0))  # tooth length below the bar (mm)
tooth_w     = float(PARAM(lambda: tooth_w,      2.2))  # tooth width at the root (mm)

target_part = str(PARAM(lambda: target_part, "comb"))  # comb|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
bar_length = max(20.0, min(bar_length, 120.0))
bar_h      = max(4.0, min(bar_h, 18.0))
bar_t      = max(1.4, min(bar_t, 5.0))
slot_count = max(0, min(slot_count, 24))
slot_pitch = max(2.5, min(slot_pitch, 20.0))
slot_w     = max(0.8, min(slot_w, 4.0))
teeth      = max(2, min(teeth, 24))
tooth_len  = max(8.0, min(tooth_len, 70.0))
tooth_w    = max(1.2, min(tooth_w, 6.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
# The slot row must fit inside the bar with an end margin, so the pitch yields to the bar.
end_margin = max(2.5, bar_length * 0.06)
if slot_count > 1:
    max_pitch = (bar_length - 2.0 * end_margin - slot_w) / (slot_count - 1.0)
    slot_pitch = min(slot_pitch, max(1.2, max_pitch))
slot_run = (slot_count - 1.0) * slot_pitch if slot_count > 1 else 0.0
# Slot height: a slot, not a hole — long across the bar so the thread can be drawn along it,
# but leaving a top rail and a root rail intact.
slot_h = max(1.2, min(bar_h * 0.45, bar_h - 2.6))
slot_w = min(slot_w, max(0.6, slot_pitch - 1.0))

# The tooth row spans the bar with the same end margin, so no tooth hangs off the spine.
tooth_span = max(1.0, bar_length - 2.0 * (end_margin + tooth_w / 2.0))
tooth_pitch = tooth_span / (teeth - 1.0) if teeth > 1 else 0.0
tooth_w = min(tooth_w, max(0.8, (tooth_pitch if teeth > 1 else bar_length) * 0.8))
# Teeth taper to a narrow flat tip — never to a point (a point is a tessellation
# singularity) — and are thinner than the bar so the comb slides into hair.
tip_w = max(0.7, tooth_w * 0.45)
tooth_t = min(bar_t, max(1.2, bar_t * 0.8))
# Teeth overlap up into the bar so every union is volumetric.
root_bite = min(1.2, bar_h * 0.4)


def _bar():
    """The gathering bar: a flat rounded rail lying along X, standing in Z above z=0."""
    bar = (
        cq.Workplane("XY")
        .box(bar_length, bar_t, bar_h, centered=(True, True, False))
    )
    # Round the ends on the clean blank, before any slot or tooth work.
    try:
        bar = bar.edges("|Z").fillet(min(bar_t * 0.45, bar_length * 0.1))
    except Exception:
        pass
    try:
        bar = bar.edges(">Z").fillet(min(bar_t * 0.3, 0.8))
    except Exception:
        pass
    return bar


def _slot_cutter():
    """The sew-slot row: one batched pushPoints op cutting clean through the bar."""
    if slot_count <= 0:
        return None
    xs = [(-slot_run / 2.0 + i * slot_pitch) for i in range(slot_count)]
    z_mid = bar_h - slot_h / 2.0 - 1.2      # slots ride the upper half, clear of the roots
    slots = (
        cq.Workplane("XZ")
        .pushPoints([(x, z_mid) for x in xs])
        .slot2D(max(slot_h, slot_w * 1.2), slot_w, 90.0)
        .extrude(bar_t * 4.0)
        .translate((0, bar_t * 2.0, 0))
    )
    return slots


def _tooth_xs():
    """Tooth centre positions along the bar."""
    if teeth <= 1:
        return [0.0]
    return [(-tooth_span / 2.0 + i * tooth_pitch) for i in range(teeth)]


def _teeth():
    """The comb teeth: a straight prism column batched in ONE pushPoints op, plus a
    lofted taper on each tooth tip.

    The straight run is built for the whole row at once. The tapered tips have to be lofted
    one at a time (a multi-wire loft is not a legal operation), but each loft is a separate
    closed solid that overlaps its prism, so every union is volumetric. The tip is a small
    FLAT rectangle, never a point — a point is a tessellation singularity.
    """
    xs = _tooth_xs()
    taper_len = min(tooth_len * 0.45, tooth_w * 4.0)
    straight = tooth_len - taper_len
    col = (
        cq.Workplane("XY")
        .pushPoints([(x, 0.0) for x in xs])
        .rect(tooth_w, tooth_t)
        .extrude(-(straight + root_bite))
        .translate((0, 0, root_bite))
    )
    body = col
    for x in xs:
        tip = (
            cq.Workplane("XY")
            .workplane(offset=-(straight - 0.4))
            .rect(tooth_w, tooth_t)
            .workplane(offset=-(taper_len + 0.4))
            .rect(tip_w, max(0.7, tooth_t * 0.7))
            .loft(ruled=True)
            .translate((x, 0, 0))
        )
        body = body.union(tip)
    return body


def build_comb():
    """One veil comb: gathering bar with sew slots, plus the tapered tooth row."""
    body = _bar().union(_teeth())
    slots = _slot_cutter()
    if slots is not None:
        body = body.cut(slots)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    one = build_comb()
    gap = max(5.0, bar_length * 0.12)
    off = (bar_length + gap) / 2.0
    asm = cq.Assembly()
    asm.add(one.translate((-off, 0, 0)), name="comb_left", color=cq.Color("#d8d0c0"))
    asm.add(one.translate((off, 0, 0)), name="comb_right", color=cq.Color("#c8c0b0"))
    result = asm
else:
    result = build_comb()
