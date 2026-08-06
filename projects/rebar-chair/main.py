"""
Rebar Chair / Spacer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Concrete reinforcement spacers that hold rebar at a set concrete-cover depth so
the pour flows underneath and the steel ends up correctly embedded. Sized to US
bar designations — #3 = 9.5 mm (3/8 in), #4 = 12.7 mm (1/2 in), #5 = 15.9 mm
(5/8 in) — with cover depths from ~20 mm up to footing values. The bar snaps
into a C-saddle whose mouth is narrower than the bar so it retains.

Three distinct modes (dispatch on target_part):
  - chair_saddle   : the classic bar chair — a snap C-saddle at cover height on
                     splayed legs standing on a base pad on the form.
  - chair_wheel    : a wheel / donut spacer — a disc the bar threads through the
                     centre; the disc radius sets the cover on a vertical face
                     and lets the spacer roll along the bar.
  - chair_crossbar : a chair carrying a crossing pair — two snap saddles at 90
                     degrees on one leg stack, holding a mesh intersection.

Watertight strategy (per the Yantra4D authoring canon):
  - The snap saddle is an EXTRUDED annulus (outer disc minus inner bore) with a
    mouth slot cut from the top — a single clean solid, never a revolve of a cut
    profile.
  - Legs, base and saddle union with real material overlap (no tangent seams).
  - The wheel's bar bore is a straight through-hole (vents both ends), never a
    trapped cavity; fillet the clean disc before boring.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as bare globals.
  - Read every param via PARAM(lambda: <name>, <default>).
  - No cross-file imports; assign the final solid to top-level `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "chair_saddle"))
# "chair_saddle" | "chair_wheel" | "chair_crossbar"

bar_dia = float(PARAM(lambda: bar_dia, 12.7))      # #4 rebar (1/2 in)
cover = float(PARAM(lambda: cover, 40.0))          # concrete cover depth
clip_wall = float(PARAM(lambda: clip_wall, 3.5))   # saddle wall thickness
leg_t = float(PARAM(lambda: leg_t, 6.0))           # leg thickness
base_w = float(PARAM(lambda: base_w, 38.0))        # base pad width (footprint)
snap_grip = float(PARAM(lambda: snap_grip, 0.82))  # mouth width / bar (snap)
wheel_od = float(PARAM(lambda: wheel_od, 80.0))    # wheel spacer outer diameter

# Clamp to sane ranges so extreme UI values never crash the kernel.
bar_dia = max(8.0, min(bar_dia, 20.0))
cover = max(20.0, min(cover, 90.0))
clip_wall = max(2.5, min(clip_wall, 6.0))
leg_t = max(4.0, min(leg_t, 12.0))
base_w = max(28.0, min(base_w, 70.0))
snap_grip = max(0.7, min(snap_grip, 0.95))
wheel_od = max(40.0, min(wheel_od, 140.0))

_clip_ir = bar_dia / 2.0 + 0.4          # saddle inner radius (slip fit + clip)
_clip_or = _clip_ir + clip_wall          # saddle outer radius


# ── Helpers ──────────────────────────────────────────────────────────────────
def _snap_saddle(width, mouth_up=True):
    """A snap C-saddle: an extruded annulus (thickness = `width`, along its
    axis) with a mouth slot cut so a bar snaps in. Built centred at origin with
    its axis along Y (so the bar runs along Y). Returns a solid."""
    outer = cq.Workplane("XZ").circle(_clip_or).extrude(width / 2.0, both=True)
    inner = cq.Workplane("XZ").circle(_clip_ir).extrude(width / 2.0 + 1.0, both=True)
    ring = outer.cut(inner)
    # Mouth slot from the +Z top (or -Z if mouth_up False), narrower than the bar.
    mouth_w = bar_dia * snap_grip
    z_off = (_clip_or) if mouth_up else -(_clip_or)
    mouth = (cq.Workplane("XZ").transformed(offset=cq.Vector(0, z_off, 0))
             .rect(mouth_w, (clip_wall + 2.0) * 2.0)
             .extrude(width / 2.0 + 2.0, both=True))
    return ring.cut(mouth)


# ── Part builders ────────────────────────────────────────────────────────────
def build_chair_saddle():
    """Classic bar chair: a snap saddle held at `cover` height by two splayed
    legs standing on a base pad. Bar runs along Y and snaps down into the top."""
    saddle_w = max(bar_dia + 8.0, 18.0)
    saddle = _snap_saddle(saddle_w).translate((0, 0, cover))

    # Base pad on the form (z=0), square-ish footprint.
    base = (cq.Workplane("XY").box(base_w, saddle_w, leg_t,
                                   centered=(True, True, False)))
    try:
        base = base.edges("|Z").fillet(min(4.0, leg_t))
    except Exception:
        pass

    # Two splayed legs (in the XZ plane) from base corners up to the saddle.
    top_half = _clip_or * 0.7
    legs = None
    for sx in (+1.0, -1.0):
        x_bot = sx * (base_w / 2.0 - leg_t * 0.7)
        x_top = sx * top_half
        leg = (cq.Workplane("XZ")
               .polyline([
                   (x_bot - leg_t / 2.0, leg_t * 0.5),
                   (x_bot + leg_t / 2.0, leg_t * 0.5),
                   (x_top + leg_t / 2.0, cover),
                   (x_top - leg_t / 2.0, cover),
               ])
               .close()
               .extrude(saddle_w / 2.0, both=True))
        legs = leg if legs is None else legs.union(leg)

    body = base.union(legs).union(saddle)
    return body


def build_chair_wheel():
    """Wheel / donut spacer: a disc with a central bar bore. The disc radius sets
    the cover from a vertical form face; the spacer rolls along the bar. A ring
    of lightening holes reduces mass (each a through-hole → vents)."""
    thick = max(bar_dia + 6.0, 16.0)
    disc = cq.Workplane("XY").circle(wheel_od / 2.0).extrude(thick)
    # Fillet the clean disc rim BEFORE boring.
    try:
        disc = disc.edges("%CIRCLE").fillet(min(3.0, thick * 0.25))
    except Exception:
        pass

    # Central bar bore straight through (vents both faces).
    bore = (cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, -1.0))
            .circle(bar_dia / 2.0 + 0.4).extrude(thick + 2.0))
    body = disc.cut(bore)

    # A ring of lightening holes (through-holes, so no trapped void).
    n = 6
    ring_r = (bar_dia / 2.0 + wheel_od / 2.0) / 2.0
    hole_r = min((wheel_od / 2.0 - bar_dia / 2.0) * 0.22, wheel_od * 0.09)
    if hole_r > 2.0:
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            hx, hy = ring_r * math.cos(ang), ring_r * math.sin(ang)
            body = body.cut(
                cq.Workplane("XY").transformed(offset=cq.Vector(hx, hy, -1.0))
                .circle(hole_r).extrude(thick + 2.0)
            )
    return body


def build_chair_crossbar():
    """Crossbar chair: two snap saddles at 90 degrees on one leg stack, holding a
    mesh intersection. The lower saddle carries the bar along X, the upper carries
    the crossing bar along Y, one bar_dia higher."""
    saddle_w = max(bar_dia + 8.0, 18.0)

    # Lower saddle: axis along X (rotate the Y-axis saddle 90 deg about Z).
    low = _snap_saddle(saddle_w).rotate((0, 0, 0), (0, 0, 1), 90.0)
    low = low.translate((0, 0, cover))
    # Upper saddle: axis along Y, one bar diameter + clearance higher, so the
    # crossing bar sits on top of the lower one.
    up = _snap_saddle(saddle_w).translate((0, 0, cover + bar_dia + 2.0))

    # Base pad.
    base = (cq.Workplane("XY").box(base_w, base_w, leg_t,
                                   centered=(True, True, False)))
    try:
        base = base.edges("|Z").fillet(min(4.0, leg_t))
    except Exception:
        pass

    # Central column tying base to both saddles (solid, no trapped void).
    col_w = _clip_or * 1.4
    column = (cq.Workplane("XY").rect(col_w, col_w)
              .extrude(cover + bar_dia + 2.0))
    body = base.union(column).union(low).union(up)

    # Re-open the two bar channels THROUGH the column so both bars actually seat
    # (the column is wider than the saddle bore, so it fills it — carve it back).
    # These are through-channels open at both ends (vent), so still watertight.
    bore_r = bar_dia / 2.0 + 0.4
    reach = base_w + _clip_or + 4.0
    low_bore = (cq.Workplane("YZ").transformed(offset=cq.Vector(0, cover, 0))
                .circle(bore_r).extrude(reach, both=True))
    up_bore = (cq.Workplane("XZ")
               .transformed(offset=cq.Vector(0, cover + bar_dia + 2.0, 0))
               .circle(bore_r).extrude(reach, both=True))
    body = body.cut(low_bore).cut(up_bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "chair_wheel":
    result = build_chair_wheel()
elif target_part == "chair_crossbar":
    result = build_chair_crossbar()
else:
    result = build_chair_saddle()
