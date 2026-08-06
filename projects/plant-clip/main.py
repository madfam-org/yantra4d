"""
Trellis / Plant Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A gentle clip that ties a plant stem to a stake, a trellis wire, or itself. Three
styles: a stake clip (a figure-of-eight — one C-loop for the stem, one for the
stake), a wire clip (a C-loop for the stem plus a slot that snaps over a trellis
wire), and a soft spiral wrap that coils loosely around a stem. Openings are sized a
little smaller than the stem so the clip holds, but the C is a compliant open ring
that springs on without crushing the plant.

Design idiom (compliant C-loops):
  A C-loop is a tube ring (outer circle minus inner bore) with a mouth slot cut on
  one side; the mouth is narrower than the stem so it grips but flexes open. Loops
  are unioned volumetrically (they overlap at the web) so the mesh is one watertight
  solid. Everything is a real solid — no zero-thickness surfaces.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `stem_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(  PARAM(lambda: target_part, "stake_clip"))  # stake_clip | wire_clip | spiral_clip
clip_type   = str(  PARAM(lambda: clip_type,   "stem_to_stake"))  # legacy selector (mirrors part)
stem_dia    = float(PARAM(lambda: stem_dia,    10.0))          # plant stem diameter (mm)
stake_dia   = float(PARAM(lambda: stake_dia,   11.0))          # stake diameter (stake clip, mm)
wire_dia    = float(PARAM(lambda: wire_dia,     3.0))          # trellis wire diameter (wire clip, mm)
wall        = float(PARAM(lambda: wall,         2.4))          # clip wall thickness (mm)
width       = float(PARAM(lambda: width,       10.0))          # clip width along the stem axis (mm)
mouth       = float(PARAM(lambda: mouth,        0.7))          # mouth opening as fraction of stem_dia

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
stem_dia = max(3.0, min(stem_dia, 40.0))
stake_dia = max(3.0, min(stake_dia, 40.0))
wire_dia = max(1.5, min(wire_dia, 12.0))
wall = max(1.2, min(wall, 5.0))
width = max(4.0, min(width, 30.0))
mouth = max(0.4, min(mouth, 0.95))


# ── C-loop helper ──────────────────────────────────────────────────────────────
def c_loop(inner_d, cx, mouth_dir_deg, extra_gap=0.4):
    """A compliant C-ring gripping a `inner_d` cylinder, centered at (cx, 0), width
    `width` along Z. `mouth_dir_deg` points the opening slot outward. Returns solid.

    The bore is inner_d + extra_gap (a touch loose so it isn't a press-crush); the
    mouth slot width is `mouth * inner_d`, cut through the ring wall on the chosen
    side, leaving a compliant open C that springs onto the stem."""
    bore_r = (inner_d + extra_gap) / 2.0
    outer_r = bore_r + wall
    ring = cq.Workplane("XY").circle(outer_r).circle(bore_r).extrude(width)
    # Mouth slot: a rectangular cut from the bore outward, pointing mouth_dir_deg.
    slot_w = max(1.2, mouth * inner_d)
    slot = (
        cq.Workplane("XY")
        .center(outer_r * 0.6, 0.0)          # start beyond the bore, extend outward
        .rect(outer_r * 1.6, slot_w)
        .extrude(width + 2.0)
        .translate((0, 0, -1.0))
        .rotate((0, 0, 0), (0, 0, 1), mouth_dir_deg)
    )
    ring = ring.cut(slot)
    return ring.translate((cx, 0, 0))


def solid_disc(dia, cx):
    """A small solid connector disc (for webs), radius dia/2, at (cx,0), height width."""
    return cq.Workplane("XY").circle(dia / 2.0).extrude(width).translate((cx, 0, 0))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_stake_clip():
    """Figure-of-eight: a C-loop for the stem and a C-loop for the stake, joined by a
    web. Openings face OPPOSITE ways so the whole thing threads on and holds both."""
    stem_bore = stem_dia
    stake_bore = stake_dia
    stem_outer = (stem_bore + 0.4) / 2.0 + wall
    stake_outer = (stake_bore + 0.4) / 2.0 + wall
    # Place loops side by side, centers separated so the walls just meet at a web.
    sep = stem_outer + stake_outer - wall * 0.6
    stem_cx = -sep / 2.0
    stake_cx = sep / 2.0

    stem_c = c_loop(stem_bore, stem_cx, 180.0)     # stem mouth faces -X (outward)
    stake_c = c_loop(stake_bore, stake_cx, 0.0)    # stake mouth faces +X (outward)
    # Web connecting the two loops (a bar across the middle).
    web = (
        cq.Workplane("XY")
        .box(sep + 2.0, min(width, wall * 2.5), width, centered=(True, True, False))
    )
    body = stem_c.union(stake_c).union(web)
    try:
        body = body.edges("|Z").fillet(min(wall * 0.4, 0.8))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wire_clip():
    """A C-loop for the stem plus a wire slot on the back that snaps over a trellis
    wire. The wire channel is a small C opening the opposite way from the stem."""
    stem_bore = stem_dia
    stem_outer = (stem_bore + 0.4) / 2.0 + wall
    stem_c = c_loop(stem_bore, 0.0, 90.0)          # stem mouth faces +Y

    # Wire hook: a small C behind the stem loop, opening -Y, gripping the wire.
    wire_cx = 0.0
    wire_cy = -(stem_outer + wire_dia * 0.6)
    wire_bore = wire_dia
    wire_outer = (wire_bore + 0.3) / 2.0 + wall
    wire_ring = cq.Workplane("XY").circle(wire_outer).circle(wire_bore / 2.0 + 0.15).extrude(width)
    wslot = (
        cq.Workplane("XY")
        .center(0.0, -wire_outer * 0.6)
        .rect(max(1.0, wire_dia * 0.8), wire_outer * 1.6)
        .extrude(width + 2.0)
        .translate((0, 0, -1.0))
    )
    wire_ring = wire_ring.cut(wslot).translate((wire_cx, wire_cy, 0))

    # Web tying the two.
    web = (
        cq.Workplane("XY")
        .box(min(width, wall * 2.5), abs(wire_cy) + 2.0, width, centered=(True, True, False))
        .translate((0, wire_cy / 2.0, 0))
    )
    body = stem_c.union(wire_ring).union(web)
    try:
        body = body.edges("|Z").fillet(min(wall * 0.4, 0.8))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_spiral_clip():
    """A soft spiral wrap: a helical rib coiled loosely around the stem for ~1.5
    turns, so it hugs a stem without pinching. Built as a swept round profile along a
    real-radius helix (the same non-singular sweep the thread cartridges use), so it
    is a clean watertight solid."""
    coil_r = (stem_dia + 1.5) / 2.0 + wall * 0.4   # coil mean radius (loose around stem)
    turns = 1.6
    pitch = max(width, wall * 2.0)
    height = pitch * turns
    rib_r = max(1.0, wall * 0.7)                    # round cross-section radius

    helix = cq.Wire.makeHelix(pitch=pitch, height=height, radius=coil_r)
    prof = (
        cq.Workplane("XZ")
        .center(coil_r, 0.0)
        .circle(rib_r)
    )
    coil = prof.sweep(helix, isFrenet=True, makeSolid=True)

    # A short tail tab at the bottom to hook/anchor.
    tab = (
        cq.Workplane("XY")
        .box(coil_r * 1.6, rib_r * 2.0, rib_r * 2.0, centered=(True, True, True))
        .translate((coil_r * 0.3, 0, rib_r))
    )
    body = coil.union(tab)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wire_clip" or clip_type == "wire_clip":
    result = build_wire_clip()
elif target_part == "spiral_clip" or clip_type == "spiral":
    result = build_spiral_clip()
else:
    result = build_stake_clip()
