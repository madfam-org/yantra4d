"""Tri-Glide Slider — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The flat three-bar webbing glide: a rectangular frame with two bars across it, giving
three openings. The tape goes over the near bar, under the middle bar and back over the
far bar; the double reversal is what holds a length setting on backpack sternum straps,
apron ties, camera slings and dog harnesses. This is the rigid hard good the Fashion
Cabinet `tri-glide-slider` notion places and bridges to here for its geometry.

Distinct from the sibling cartridges: `d-ring` is a single anchor loop, `bra-ring-slider`
is the small lingerie ring-and-slider pair, and `ladder-lock` is the one-bar quick-release
adjuster. This is the flat three-bar glide, sized for trade webbing 20 / 25 / 38 / 50 mm.

Modes (dispatched via `target_part`):
  * "glide" — the tri-glide frame (one piece by design).

Geometry: a rounded slab minus TWO oversized through-slot cutters, leaving an outer frame
and two bars. Each bar's section is rounded by filleting its long vertical edges — done
via a bounded edge selection, wrapped in try/except, never a blanket fillet after complex
cuts. The outer rim is chamfered on the clean blank before any slot is cut. Prints flat,
no supports; both slots are vertical through-holes.

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
rail_t    = float(PARAM(lambda: rail_t,    3.2))   # outer frame rail thickness (mm)
bar_w     = float(PARAM(lambda: bar_w,     4.0))   # internal bar width along pull (mm)
body_h    = float(PARAM(lambda: body_h,    4.0))   # frame height / print height (mm)
round_bar = bool( PARAM(lambda: round_bar, True))  # round the bar sections

target_part = str(PARAM(lambda: target_part, "glide"))  # glide

# ── Safe clamps ──────────────────────────────────────────────────────────────
webbing_w = max(15.0, min(webbing_w, 50.0))
webbing_t = max(0.8, min(webbing_t, 4.0))
rail_t    = max(2.0, min(rail_t, 6.0))
bar_w     = max(2.5, min(bar_w, 8.0))
body_h    = max(2.5, min(body_h, 9.0))

# ── Derived geometry ─────────────────────────────────────────────────────────
# Each of the three openings must pass one tape thickness with a running allowance;
# the middle opening sees the tape doubled where it reverses, so it runs wider.
slot_end = max(webbing_t + 1.2, 2.6)                # the two outer openings (X)
slot_mid = max(webbing_t * 2.0 + 1.4, 3.4)          # the middle opening (X)
slot_y   = webbing_w + 1.0                          # opening span across the tape (Y)
inner_x  = slot_end * 2.0 + slot_mid + bar_w * 2.0
outer_x  = inner_x + 2.0 * rail_t
outer_y  = slot_y + 2.0 * rail_t
corner_r = min(2.0, rail_t * 0.65)

# Slot centre X positions, left to right across the glide.
_x_left  = -inner_x / 2.0
x_slot_1 = _x_left + slot_end / 2.0
x_bar_1  = _x_left + slot_end + bar_w / 2.0
x_slot_2 = _x_left + slot_end + bar_w + slot_mid / 2.0
x_bar_2  = _x_left + slot_end + bar_w + slot_mid + bar_w / 2.0
x_slot_3 = _x_left + slot_end + bar_w + slot_mid + bar_w + slot_end / 2.0


def build_glide():
    """Rounded frame, three through openings, two internal bars."""
    body = (
        cq.Workplane("XY")
        .rect(outer_x, outer_y)
        .extrude(body_h)
        .edges("|Z")
        .fillet(corner_r)
    )
    # Break the outside rim on the clean blank, before any slot exists.
    try:
        body = body.edges("#Z").chamfer(min(0.5, body_h * 0.16, rail_t * 0.22))
    except Exception:
        pass

    for cx, sx in ((x_slot_1, slot_end), (x_slot_2, slot_mid), (x_slot_3, slot_end)):
        slot = (
            cq.Workplane("XY")
            .box(sx, slot_y, body_h + 6.0)
            .translate((cx, 0.0, body_h / 2.0))
        )
        body = body.cut(slot)

    if round_bar:
        # Round the bars' four long HORIZONTAL edges — the ones parallel to Y, where
        # each bar's slot flank meets its top and bottom face. Those are the corners
        # the tape actually wraps over; the bars' vertical end edges are concave
        # junctions with the rails and must be left alone (filleting them would ADD
        # material in the corner instead of softening the wrap).
        r = min(body_h * 0.30, bar_w * 0.30, 1.0)
        for cx in (x_bar_1, x_bar_2):
            try:
                sel = cq.selectors.BoxSelector(
                    (cx - bar_w / 2.0 - 0.2, -slot_y / 2.0 + 0.2, -0.5),
                    (cx + bar_w / 2.0 + 0.2, slot_y / 2.0 - 0.2, body_h + 0.5),
                )
                body = body.edges("|Y").edges(sel).fillet(r)
            except Exception:
                pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
result = build_glide()
