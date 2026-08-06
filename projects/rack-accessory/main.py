"""
Roof-Rack / Crossbar Accessory — Yantra4D Hyperobject Cartridge (CadQuery).

Roof-rack crossbars come in a few profile families — square, round and aero
(teardrop). This cartridge builds accessory saddles that seat on each: the bar
profile is channelled into the underside so the saddle straddles the bar, and a
clamp plate (not printed) pinches it from below via side bolts. On top each
saddle carries an accessory platform with a T-slot.

  * "square_clamp" — a saddle for a square / rectangular crossbar (e.g. Thule
                     SquareBar 22.2 × 31.75 mm) (target_part == "square_clamp").
  * "round_clamp"  — a saddle for a round crossbar (e.g. Yakima RoundBar 28.6 mm
                     OD) (target_part == "round_clamp").
  * "aero_saddle"  — a saddle for a wide aero crossbar (e.g. Thule WingBar
                     ≈ 79 × 25 mm), approximated as a rounded rectangle
                     (target_part == "aero_saddle").

Real dimensions (Thule / Yakima approximations):
  - Thule SquareBar 22.2 × 31.75 mm (7/8 × 1-1/4 in) rectangular section.
  - Yakima RoundBar 28.6 mm OD (1-1/8 in).
  - Thule WingBar aero ≈ 79 mm wide × 25 mm tall (teardrop bounding box).
  - Yakima JetStream aero ≈ 43 × 28 mm.

Watertight strategy: each saddle is a SOLID block; the bar profile is cut UP from
the bottom face (open to the bottom → the bar enters from below, vented, no
trapped void). Side clamp-bolt holes pass through (vented). The accessory
platform is unioned on top (overlap) with a T-slot / bolt slot cut through
(vented). Fillets on the clean blank BEFORE cuts. Each result is one manifold
solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "square_clamp"))  # square_clamp | round_clamp | aero_saddle

bar_w = float(PARAM(lambda: bar_w, 31.75))        # crossbar width (mm)
bar_h = float(PARAM(lambda: bar_h, 22.2))         # crossbar height (mm)
saddle_w = float(PARAM(lambda: saddle_w, 50.0))   # saddle width along the bar (mm)
wall = float(PARAM(lambda: wall, 5.0))            # saddle wall / body thickness (mm)
bolt_d = float(PARAM(lambda: bolt_d, 6.4))        # clamp bolt clearance (M6 ~6.4 mm)
acc_slot_w = float(PARAM(lambda: acc_slot_w, 8.0))  # accessory T-slot width (mm)
plat_h = float(PARAM(lambda: plat_h, 8.0))        # accessory platform height above the bar (mm)
clearance = float(PARAM(lambda: clearance, 0.4))  # bar channel slip clearance (per side)

# ── Clamps ───────────────────────────────────────────────────────────────────
bar_w = max(15.0, min(bar_w, 95.0))
bar_h = max(12.0, min(bar_h, 45.0))
saddle_w = max(25.0, min(saddle_w, 90.0))
wall = max(3.0, min(wall, 12.0))
bolt_d = max(3.0, min(bolt_d, 10.0))
acc_slot_w = max(4.0, min(acc_slot_w, 14.0))
plat_h = max(4.0, min(plat_h, 20.0))
clearance = max(0.0, min(clearance, 1.2))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _saddle_blank(chan_w, chan_h):
    """A solid saddle block big enough to wrap a bar of channel size chan_w x
    chan_h, sitting with its bottom at z=0. Returns (body, block_w, block_h)."""
    block_w = chan_w + 2.0 * wall
    block_h = chan_h + wall + plat_h
    body = (
        cq.Workplane("XY")
        .box(block_w, saddle_w, block_h, centered=(True, True, False))
    )
    try:
        body = body.edges("|Y").fillet(min(4.0, wall * 0.8))
    except Exception:
        pass
    return body, block_w, block_h


def _side_bolts(block_w, chan_h):
    """Two clamp bolt bores across X (through the side walls), at the height of
    the bar channel, so a clamp plate below can pinch. Vented."""
    bolt_z = chan_h * 0.5 + wall * 0.2
    return (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, bolt_z, 0))
        .circle(bolt_d / 2.0)
        .extrude(block_w / 2.0 + 2.0, both=True)
    )


def _acc_platform(body, block_w, block_h):
    """Cut a T-slot / bolt channel down through the top platform (vented), and
    round the platform top edges."""
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, block_h - plat_h * 0.7))
        .slot2D(saddle_w * 0.7, acc_slot_w, angle=90)
        .extrude(plat_h)
    )
    body = body.cut(slot)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_square_clamp():
    """Saddle for a square / rectangular crossbar: a rectangular channel cut up
    from the bottom."""
    chan_w = bar_w + 2.0 * clearance
    chan_h = bar_h + clearance
    body, bw, bh = _saddle_blank(chan_w, chan_h)
    # Bar channel open to the bottom (cut up from z=-1 to chan_h).
    chan = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .box(chan_w, saddle_w + 2.0, chan_h + 1.0, centered=(True, True, False))
    )
    body = body.cut(chan)
    body = body.cut(_side_bolts(bw, chan_h))
    body = _acc_platform(body, bw, bh)
    return body


def build_round_clamp():
    """Saddle for a round crossbar: a circular channel (radius = bar_w/2) cut up
    from the bottom, with a bottom mouth slot so the bar enters (vented)."""
    r = max(bar_w, bar_h) / 2.0 + clearance
    chan_w = 2.0 * r
    chan_h = 2.0 * r
    body, bw, bh = _saddle_blank(chan_w, chan_h)
    # Cylindrical channel along Y at the bar centre height (= r above the bottom).
    axis_z = r
    chan = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, axis_z, 0))
        .circle(r)
        .extrude(saddle_w / 2.0 + 2.0, both=True)
    )
    body = body.cut(chan)
    # Mouth slot from the bore down to the bottom face (so the bar snaps up in).
    mouth = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .box(r * 1.3, saddle_w + 2.0, axis_z + 1.0, centered=(True, True, False))
    )
    body = body.cut(mouth)
    body = body.cut(_side_bolts(bw, chan_h))
    body = _acc_platform(body, bw, bh)
    return body


def build_aero_saddle():
    """Saddle for a wide aero crossbar, approximated as a rounded-rectangle
    channel cut up from the bottom (aero bars are teardrops; a rounded rectangle
    bounding channel seats them with foam or a shim)."""
    chan_w = bar_w + 2.0 * clearance
    chan_h = bar_h + clearance
    body, bw, bh = _saddle_blank(chan_w, chan_h)
    # Rounded-rectangle channel cut up from the bottom: a box cutter whose top
    # (interior) horizontal edges are rounded to approximate the aero teardrop.
    chan = (
        cq.Workplane("XY")
        .workplane(offset=-1.0)
        .box(chan_w, saddle_w + 2.0, chan_h + 1.0, centered=(True, True, False))
    )
    try:
        chan = chan.edges("|Y and >Z").fillet(min(chan_h * 0.3, chan_w * 0.2))
    except Exception:
        pass
    body = body.cut(chan)
    body = body.cut(_side_bolts(bw, chan_h))
    body = _acc_platform(body, bw, bh)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "round_clamp":
    result = build_round_clamp()
elif target_part == "aero_saddle":
    result = build_aero_saddle()
else:  # "square_clamp"
    result = build_square_clamp()
