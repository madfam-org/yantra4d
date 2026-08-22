"""Ladder Lock — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The one-piece webbing adjuster on every pack shoulder strap, sternum strap and cinch:
a rectangular frame with a fixed bar across its middle. The dead end of the tape is
sewn round the far bar, the live end threads up through the near slot, over the center
bar and back down — friction on the wrap holds the setting, and lifting the tape off the
bar releases it. This is the rigid hard good the Fashion Cabinet `ladder-lock` notion
places and bridges to here for its geometry. Nominal webbing widths 20 / 25 / 38 / 50 mm.

Modes (dispatched via `target_part`):
  * "lock" — the ladder-lock frame (the only part; the object is one piece by design).

Geometry: a rounded slab minus TWO oversized slot pockets cut clean through Z, leaving
the outer frame and the center bar between them. The bar's grip face carries shallow
transverse teeth — each a lofted flat-topped rib, never a knife edge — cut and unioned
from clean blanks, with every cutter overshooting both faces. No fillets follow the slot
cuts. Prints flat on the bed with no supports: both slots are vertical through-holes.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing_w`).
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
webbing_w = float(PARAM(lambda: webbing_w, 25.0))  # nominal webbing width (mm)
webbing_t = float(PARAM(lambda: webbing_t, 1.6))   # webbing thickness (mm)
frame_t   = float(PARAM(lambda: frame_t,   3.0))   # frame rail thickness (mm)
bar_w     = float(PARAM(lambda: bar_w,     4.5))   # center bar width along the pull (mm)
body_h    = float(PARAM(lambda: body_h,    5.0))   # frame height / print height (mm)
teeth     = int(  PARAM(lambda: teeth,     4))     # grip ribs on the center bar

target_part = str(PARAM(lambda: target_part, "lock"))  # lock

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing_w = max(15.0, min(webbing_w, 50.0))
webbing_t = max(0.8, min(webbing_t, 4.0))
frame_t   = max(2.0, min(frame_t, 6.0))
bar_w     = max(3.0, min(bar_w, 10.0))
body_h    = max(3.0, min(body_h, 10.0))
teeth     = max(0, min(teeth, 8))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Each slot must swallow the tape doubled at the wrap, plus a running allowance.
slot_x   = max(webbing_t * 2.0 + 1.0, 3.0)         # slot opening along the pull (X)
slot_y   = webbing_w + 1.0                          # slot span across the tape (Y)
inner_x  = 2.0 * slot_x + bar_w                     # interior length between end rails
outer_x  = inner_x + 2.0 * frame_t
outer_y  = slot_y + 2.0 * frame_t
corner_r = min(2.0, frame_t * 0.7)

# Teeth: shallow ribs across the bar's top face, sized so they bite the tape weave
# without cutting it. Depth is capped hard so the bar never becomes a blade.
#
# The rib base is derived from the PITCH, and the rib COUNT is first clamped to what
# the bar can actually hold. Without that clamp a narrow bar asked for many ribs gives
# a base wider than the pitch: the ribs merge into one continuous band and raising
# `teeth` silently stops changing the geometry. A minimum 1.0 mm pitch keeps every
# valley printable at a 0.4 mm nozzle, and a base of 0.55 x pitch keeps it real.
tooth_h     = max(0.25, min(0.5, body_h * 0.10))
teeth       = min(teeth, max(0, int(bar_w / 1.0) - 1))
tooth_pitch = bar_w / float(teeth + 1) if teeth > 0 else bar_w
tooth_x     = tooth_pitch * 0.55
bar_x0      = -bar_w / 2.0


def build_lock():
    """Rounded frame, two through slots, a center bar with grip ribs on both faces."""
    body = (
        cq.Workplane("XY")
        .rect(outer_x, outer_y)
        .extrude(body_h)
        .edges("|Z")
        .fillet(corner_r)
    )
    # Soften the outside top/bottom rims BEFORE any slot is cut — never after.
    try:
        body = body.edges("#Z").fillet(min(0.6, body_h * 0.15, frame_t * 0.25))
    except Exception:
        pass

    # Two slots, each an oversized box overshooting both Z faces.
    for sx in (1.0, -1.0):
        cx = sx * (bar_w / 2.0 + slot_x / 2.0)
        slot = (
            cq.Workplane("XY")
            .box(slot_x, slot_y, body_h + 6.0)
            .translate((cx, 0.0, body_h / 2.0))
        )
        body = body.cut(slot)

    # Grip ribs: shallow flat-topped lofts standing proud of the bar's top and bottom
    # faces. Each rib is its own clean blank, unioned with real overlap into the bar.
    if teeth > 0:
        for i in range(teeth):
            cx = bar_x0 + tooth_pitch * (i + 1)
            for z_top in (True, False):
                base_z = body_h if z_top else 0.0
                sign = 1.0 if z_top else -1.0
                rib = (
                    cq.Workplane("XY")
                    .workplane(offset=base_z - sign * 0.4)
                    .rect(tooth_x, outer_y - 2.0 * corner_r)
                    .workplane(offset=sign * (tooth_h + 0.4))
                    .rect(tooth_x * 0.55, outer_y - 2.0 * corner_r)
                    .loft(ruled=True)
                )
                body = body.union(rib)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
result = build_lock()
