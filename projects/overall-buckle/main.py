"""Overall Buckle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The sliding buckle-and-button set of dungarees/overalls — the rigid hard good the Fashion
Cabinet `overall-buckle` notion places and bridges to here for its geometry. The buckle is
a slide frame with a centre bar (the strap threads it) and a hooked catch that drops over
the fixed button on the bib. Printed rigid it stands in for the metal overall hardware.

Modes (dispatched via `target_part`):
  * "set"    — buckle frame + button.
  * "buckle" — the slide frame + catch only.
  * "button" — the fixed bib button (a domed disc on a post).

Geometry: the frame is a rounded-rect ring with a centre bar (two hole cuts); the catch a
hooked tab; the button a chamfered cylinder on a post. Small boolean count → watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `strap_w`).
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
strap_w   = float(PARAM(lambda: strap_w,   30.0))    # overall-strap width (mm)
frame_h   = float(PARAM(lambda: frame_h,   40.0))    # frame height (mm)
wire_t    = float(PARAM(lambda: wire_t,    4.0))     # frame section thickness (mm)
depth     = float(PARAM(lambda: depth,     5.0))     # part thickness in Z (mm)
button_dia = float(PARAM(lambda: button_dia, 17.0))  # bib button diameter (mm)

target_part = str(PARAM(lambda: target_part, "set"))  # set|buckle|button

# ── Safe clamps ──────────────────────────────────────────────────────────────
strap_w    = max(15.0, min(strap_w, 60.0))
frame_h    = max(20.0, min(frame_h, 90.0))
wire_t     = max(2.5, min(wire_t, 8.0))
depth      = max(3.0, min(depth, 10.0))
button_dia = max(10.0, min(button_dia, 28.0))

frame_w = strap_w + 2.0 * wire_t


def build_buckle():
    """A slide frame (rounded-rect ring) with a centre bar, plus a hooked catch below."""
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, depth / 2.0))
        .rect(frame_w, frame_h)
        .extrude(depth)
    )
    try:
        outer = outer.edges("|Z").fillet(wire_t * 0.8)
    except Exception:
        pass
    # Two slots (above and below the centre bar) the strap threads through.
    bar_h = wire_t
    slot_h = (frame_h - 2.0 * wire_t - bar_h) / 2.0
    for sy in (+(bar_h / 2.0 + slot_h / 2.0), -(bar_h / 2.0 + slot_h / 2.0)):
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, sy, depth / 2.0))
            .box(strap_w, slot_h, depth + 2.0)
        )
        outer = outer.cut(slot)
    # Hooked catch: a small tab extending below with a keyhole for the button.
    catch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(frame_h / 2.0 + frame_h * 0.22), depth / 2.0))
        .box(button_dia + 2.0 * wire_t, frame_h * 0.44, depth)
    )
    keyhole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(frame_h / 2.0 + frame_h * 0.16), depth / 2.0))
        .circle(button_dia / 2.0 + 0.4)
        .extrude(depth + 2.0)
        .translate((0, 0, -1.0))
    )
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(frame_h / 2.0 + frame_h * 0.30), depth / 2.0))
        .box(button_dia * 0.5, frame_h * 0.30, depth + 2.0)
    )
    catch = catch.cut(keyhole).cut(slot)
    return outer.union(catch)


def build_button():
    """The fixed bib button: a chamfered disc on a short post."""
    post = (
        cq.Workplane("XY")
        .circle(button_dia * 0.28)
        .extrude(3.0)
    )
    disc = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, 3.0 + depth / 2.0))
        .circle(button_dia / 2.0)
        .extrude(depth)
    )
    try:
        disc = disc.edges(">Z").fillet(depth * 0.4)
    except Exception:
        pass
    return post.union(disc)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "buckle":
    result = build_buckle()
elif target_part == "button":
    result = build_button()
else:
    result = build_buckle().union(build_button().translate((frame_w, 0, 0)))
