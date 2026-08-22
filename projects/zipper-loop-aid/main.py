"""Zipper Loop Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A large finger ring that clips onto any zipper pull tab. One piece: a C-clip that springs
over the tab's edge and a generous ring the user hooks a finger — or two, or a thumb —
through. It is the adaptive answer to a zipper pull that assumes a working pinch grip.

The problem it solves: a standard pull tab is a 2 mm slip of metal about 20 mm long, and
operating it needs a thumb-and-forefinger pinch with fine control. Arthritis, tremor,
neuropathy, hemiparesis, missing digits, a cast, thick gloves, or simply reaching a back
zipper all defeat that pinch. Occupational therapy's usual improvisation is a loop of
cord or a keyring, which slides, twists, and has to be knotted on with the same fingers
that cannot work the zipper. This clips on and stays put.

Zipper hardware sizing: a YKK #5 pull tab is about 1.5-2 mm thick; #8 and #10 outerwear
tabs run 2-3 mm. `tab_t` is that thickness and `tab_w` the tab width the clip must span.
The clip's mouth is deliberately narrower than the tab thickness so it snaps on with
interference rather than sliding off.

Modes (dispatched via `target_part`):
  * "aid"  — one loop aid.
  * "pair" — two, the usual fitting for a jacket with two sliders or a two-way zipper.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `ring_id`).
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
ring_id   = float(PARAM(lambda: ring_id,   28.0))  # finger ring inside diameter (mm)
ring_w    = float(PARAM(lambda: ring_w,     5.0))  # ring wall width, in plane (mm)
part_t    = float(PARAM(lambda: part_t,     4.0))  # part thickness, out of plane (mm)
tab_t     = float(PARAM(lambda: tab_t,      2.0))  # zipper pull tab thickness (mm)
tab_w     = float(PARAM(lambda: tab_w,     10.0))  # zipper pull tab width the clip spans (mm)
clip_wrap = float(PARAM(lambda: clip_wrap,  0.7))  # mouth as a fraction of tab thickness
clip_arm  = float(PARAM(lambda: clip_arm,   3.0))  # clip arm wall thickness (mm)

target_part = str(PARAM(lambda: target_part, "aid"))  # aid|pair

# ── Safe clamps ──────────────────────────────────────────────────────────────
ring_id   = max(14.0, min(ring_id, 70.0))
ring_w    = max(2.5, min(ring_w, 14.0))
part_t    = max(2.0, min(part_t, 14.0))
tab_t     = max(0.8, min(tab_t, 6.0))
tab_w     = max(4.0, min(tab_w, 30.0))
clip_wrap = max(0.35, min(clip_wrap, 0.92))
clip_arm  = max(1.4, min(clip_arm, 8.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Everything lies flat: ring in the XY plane, thickness along Z from 0.
ring_ri = ring_id / 2.0
ring_ro = ring_ri + ring_w
# The clip is a C whose slot receives the tab edge-on. The slot runs along X (the tab
# slides in sideways); the mouth is the gap between the two arm tips.
slot_w = tab_t + 0.25                      # running clearance on the tab
slot_l = tab_w + 1.0                       # the clip spans this much of the tab
mouth = max(0.5, slot_w * clip_wrap)       # narrower than the tab: it snaps on
clip_h = slot_w + 2.0 * clip_arm           # clip outside height, in plane
clip_l = slot_l + 2.0 * clip_arm           # clip outside length, in plane
# The clip sits below the ring, sharing a neck so the two are one solid.
neck_h = max(2.5, ring_w * 0.8)
y_clip_c = -(ring_ro + neck_h + clip_h / 2.0)
# The clip's depth out of plane can be less than the ring's; keep the flat bottom common.
clip_t = min(part_t, max(2.0, tab_w * 0.6))


def _ring():
    """The finger ring: a flat annulus, chamfered on the clean blank before any cuts."""
    ring = (
        cq.Workplane("XY")
        .circle(ring_ro)
        .circle(ring_ri)
        .extrude(part_t)
    )
    try:
        ring = ring.edges(">Z").chamfer(min(ring_w * 0.25, part_t * 0.25, 0.8))
    except Exception:
        pass
    return ring


def _neck():
    """The bar joining the ring to the clip, overlapping both so the union is volumetric."""
    top = -(ring_ro - ring_w * 0.6)          # bite up into the ring wall
    bot = y_clip_c + clip_h / 2.0 - 0.6      # bite down into the clip body
    length = abs(top - bot)
    width = min(clip_l * 0.7, max(ring_w * 1.6, 5.0))
    return (
        cq.Workplane("XY")
        .rect(width, length)
        .extrude(min(part_t, clip_t))
        .translate((0, (top + bot) / 2.0, 0))
    )


def _clip():
    """The C-clip: a rounded block with a tab pocket and a narrower mouth into it.

    The pocket lies flat — its long dimension (X) takes the tab's width, its short one (Y)
    the tab's thickness. The tab is pushed in SIDEWAYS from -X, past a throat whose Y height
    is `mouth`, deliberately less than the tab thickness: the arms spring apart, the tab
    passes, and they close behind it. Pulling the ring loads the clip along +Y, across the
    mouth rather than out of it, so the grip tightens under load instead of releasing.
    """
    block = (
        cq.Workplane("XY")
        .rect(clip_l, clip_h)
        .extrude(clip_t)
        .translate((0, y_clip_c, 0))
    )
    try:
        block = block.edges("|Z").fillet(min(clip_arm * 0.6, clip_l * 0.2, 2.5))
    except Exception:
        pass
    # Tab slot: a through pocket in Z, open on the far side (away from the ring).
    slot = (
        cq.Workplane("XY")
        .rect(slot_l, slot_w)
        .extrude(clip_t + 8.0)
        .translate((0, y_clip_c, -4.0))
    )
    try:
        slot = slot.edges("|Z").fillet(min(slot_w * 0.45, 0.9))
    except Exception:
        pass
    body = block.cut(slot)
    # Throat: the run from the block's -X edge into the pocket. Its Y height IS the mouth,
    # so the arm tips pinch the tab as it is pushed past them. One rectangle, overshooting
    # the -X edge so nothing coincident is left behind.
    x_edge = -clip_l / 2.0
    x_pocket = -slot_l / 2.0
    throat_len = (x_pocket - x_edge) + 3.0
    throat = (
        cq.Workplane("XY")
        .rect(throat_len, mouth)
        .extrude(clip_t + 8.0)
        .translate((x_pocket - throat_len / 2.0 + 0.3, y_clip_c, -4.0))
    )
    return body.cut(throat)


def build_aid():
    """One zipper loop aid: finger ring, neck, C-clip — a single flat-printing solid."""
    return _ring().union(_neck()).union(_clip())


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pair":
    one = build_aid()
    bb = one.val().BoundingBox()
    gap = max(5.0, ring_id * 0.15)
    off = (bb.xlen + gap) / 2.0
    asm = cq.Assembly()
    asm.add(one.translate((-off, 0, 0)), name="aid_a", color=cq.Color("#c86f4f"))
    asm.add(one.rotate((0, 0, 0), (0, 0, 1), 180).translate((off, 0, 0)),
            name="aid_b", color=cq.Color("#b85f3f"))
    result = asm
else:
    result = build_aid()
