"""Boning Stay and Channel — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The boning of corsetry and structured garments: a flat flexible stay that holds a seam
line straight, plus the sew-in channel casing that carries it. This is the rigid hard good
the Fashion Cabinet `boning` notion places and bridges to here for its geometry. Printed in
a springy filament (PETG, TPU-95A, nylon) a thin stay flexes around the body while resisting
buckling edge-on, exactly as spiral steel or synthetic whalebone does.

Modes (dispatched via `target_part`):
  * "set"     — a stay and its channel side by side, print-ready.
  * "stay"    — one flat stay blade.
  * "channel" — one sew-in C-profile casing with sew flanges.

Geometry: the stay is an extruded rounded rectangle (rect + vertical edge fillets). The
channel is an outer rounded block minus an inner slot sized stay + clearance, the cut run
oversized past one end so the stay slides in, with thin flat sew flanges along both long
edges. All cutting tools are oversized and translated past both faces; every fillet is
guarded. Watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `stay_length`).
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
stay_length   = float(PARAM(lambda: stay_length,   150.0))  # stay length along the seam (mm)
stay_width    = float(PARAM(lambda: stay_width,    7.0))    # stay width, flat face (mm)
stay_t        = float(PARAM(lambda: stay_t,        1.5))    # stay thickness (mm)
tip_r         = float(PARAM(lambda: tip_r,         3.0))    # corner radius at the tips (mm)
channel_wall  = float(PARAM(lambda: channel_wall,  1.2))    # casing wall thickness (mm)
channel_clear = float(PARAM(lambda: channel_clear, 0.4))    # slot clearance per side (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|stay|channel

# ── Safe clamps ──────────────────────────────────────────────────────────────
stay_length   = max(40.0, min(stay_length, 400.0))
stay_width    = max(4.0, min(stay_width, 15.0))
stay_t        = max(0.8, min(stay_t, 3.0))
tip_r         = max(0.5, min(tip_r, 7.0))
# A corner radius can never exceed half the width, or the fillet degenerates.
tip_r         = min(tip_r, stay_width / 2.0 - 0.05)
tip_r         = max(0.25, tip_r)
channel_wall  = max(0.8, min(channel_wall, 2.5))
channel_clear = max(0.2, min(channel_clear, 0.8))

# ── Derived channel geometry ─────────────────────────────────────────────────
slot_w = stay_width + 2.0 * channel_clear     # inner slot width (mm)
slot_h = stay_t + 2.0 * channel_clear         # inner slot height (mm)
chan_w = slot_w + 2.0 * channel_wall          # casing outer width (mm)
chan_h = slot_h + 2.0 * channel_wall          # casing outer height (mm)
# Sew flanges: thin flat wings either side of the casing, capped so they stay printable.
flange_w = max(2.0, min(4.0, chan_w * 0.55))  # flange reach per side (mm)
flange_t = max(0.6, min(channel_wall, 1.6))   # flange thickness (mm)
# Outer casing corner radius: guarded below half the smaller outer dimension.
chan_r = max(0.25, min(channel_wall * 0.8, min(chan_w, chan_h) / 2.0 - 0.05))


def build_stay():
    """A flat blade: rounded rectangle stay_width x stay_length, extruded stay_t thick.

    Sits on z=0, centred on X, spanning Y:[0, stay_length].
    """
    blade = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, stay_length / 2.0, stay_t / 2.0))
        .box(stay_width, stay_length, stay_t)
    )
    try:
        blade = blade.edges("|Z").fillet(tip_r)
    except Exception:
        pass
    return blade


def build_channel():
    """A sew-in C-profile casing: rounded outer block, inner slot cut through, plus a
    flat sew flange along each long edge.

    Sits on z=0, centred on X, spanning Y:[0, stay_length].
    """
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, stay_length / 2.0, chan_h / 2.0))
        .box(chan_w, stay_length, chan_h)
    )
    try:
        body = body.edges("|Y").fillet(chan_r)
    except Exception:
        pass

    # Sew flanges: one thin wing each side, fused before the slot is cut so the
    # slot walls stay a single shell.
    wing_span = chan_w + 2.0 * flange_w
    flange = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, stay_length / 2.0, flange_t / 2.0))
        .box(wing_span, stay_length, flange_t)
    )
    body = body.union(flange)

    # Inner slot: oversized past BOTH ends in Y so the stay slides through and no
    # cut face is ever coincident with an outer face.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, stay_length / 2.0, chan_h / 2.0))
        .box(slot_w, stay_length + 4.0, slot_h)
    )
    body = body.cut(slot)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "stay":
    result = build_stay()
elif target_part == "channel":
    result = build_channel()
else:
    gap = max(4.0, stay_width * 0.6)
    half = (stay_width + 2.0 * flange_w + chan_w) / 4.0 + gap / 2.0
    result = build_stay().translate((-half, 0.0, 0.0)).union(
        build_channel().translate((half, 0.0, 0.0)))
