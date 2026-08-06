"""
Engine Bay / Hose Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Under-hood routing tidies vacuum hoses, fuel lines and wire looms so they don't
chafe, rattle or melt on hot parts. This cartridge snaps around a hose or loom
three ways: a screw-down clip, a push-on sheet-metal edge clip, and a routing
comb for a loom bundle.

  * "hose_clip"  — a snap C-clip that grips a hose / loom, with a flat screw tab
                   to fasten to a bracket (target_part == "hose_clip").
  * "edge_clip"  — a clip that presses onto a sheet-metal edge / flange and
                   carries a hose C-cradle, for a fender or bracket lip
                   (target_part == "edge_clip").
  * "loom_rail"  — a flat comb carrying several hose C-clips in a row to route a
                   wire-loom bundle together (target_part == "loom_rail").

Real dimensions (convoluted split-loom OD → snap targets):
  - 1/4 in loom ≈ 10 mm OD, 3/8 in ≈ 13 mm, 1/2 in ≈ 17 mm, 5/8 in ≈ 21 mm,
    3/4 in ≈ 25 mm (nominal ID 6 / 8 / 10 / 13 / 16 / 19 mm).
  - Vacuum / small hose ≈ 6-13 mm OD.
  - Under-hood sheet-metal flange thickness ≈ 1-3 mm.

Watertight strategy (the brief's snap C-section rule): every clip is a full ring
(outer circle minus bore) minus a MOUTH slot narrower than the diameter — one
manifold C-section, never a tangent kiss. The screw tab, edge-grip jaw and rail
are SOLID and OVERLAP into the clip body (volumetric union). The edge grip is a
C-slot (open one side, vented). Fillets on clean blanks BEFORE cuts. Each result
is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "hose_clip"))  # hose_clip | edge_clip | loom_rail

hose_od = float(PARAM(lambda: hose_od, 13.0))     # hose / loom outer diameter (mm)
wall = float(PARAM(lambda: wall, 2.6))            # clip wall thickness (mm)
clip_w = float(PARAM(lambda: clip_w, 10.0))       # clip width along the hose (mm)
mouth = float(PARAM(lambda: mouth, 0.8))          # mouth opening as fraction of OD (grip)
edge_th = float(PARAM(lambda: edge_th, 2.0))      # sheet-metal edge thickness (mm)
edge_reach = float(PARAM(lambda: edge_reach, 12.0))  # how far the edge grip reaches onto the panel (mm)
screw_d = float(PARAM(lambda: screw_d, 4.5))      # screw tab hole (mm)
n_clips = int(float(PARAM(lambda: n_clips, 3)))   # clips on the loom rail
clip_pitch = float(PARAM(lambda: clip_pitch, 20.0))  # spacing on the rail (mm)
clearance = float(PARAM(lambda: clearance, 0.3))  # per-side slip clearance (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
hose_od = max(4.0, min(hose_od, 40.0))
wall = max(1.6, min(wall, 6.0))
clip_w = max(5.0, min(clip_w, 30.0))
mouth = max(0.55, min(mouth, 0.92))
edge_th = max(0.8, min(edge_th, 8.0))
edge_reach = max(6.0, min(edge_reach, 30.0))
screw_d = max(2.5, min(screw_d, 8.0))
n_clips = max(1, min(n_clips, 8))
clip_pitch = max(hose_od + 2.0 * wall + 2.0, min(clip_pitch, 50.0))

BORE_R = hose_od / 2.0 + clearance
OUTER_R = BORE_R + wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def _c_clip(width, cx=0.0, cy=0.0, cz=0.0):
    """A snap C-clip: a full ring (axis along X) minus a mouth slot narrower than
    the bore so the hose snaps in and is retained. One manifold C-section, mouth
    facing +Y. Centred at (cx, cy, cz)."""
    ring = (
        cq.Workplane("YZ")
        .circle(OUTER_R)
        .circle(BORE_R)
        .extrude(width)
        .translate((-width / 2.0, 0, 0))
    )
    mouth_w = max(1.4, hose_od * mouth)
    slot = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, OUTER_R, 0))
        .rect(mouth_w, OUTER_R * 2.2)
        .extrude(width + 2.0)
        .translate((-width / 2.0 - 1.0, 0, 0))
    )
    return ring.cut(slot).translate((cx, cy, cz))


# ── Part builders ────────────────────────────────────────────────────────────
def build_hose_clip():
    """A hose C-clip with a flat screw tab hanging below, drilled for a screw.
    The tab overlaps up into the clip's outer wall (volumetric union)."""
    clip = _c_clip(clip_w)
    tab_len = OUTER_R + screw_d + 6.0
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -OUTER_R - tab_len / 2.0 + wall + 1.0, -clip_w / 2.0))
        .box(clip_w, tab_len, max(3.0, wall), centered=(True, True, False))
    )
    body = clip.union(tab)
    # Screw hole through the tab (vented).
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -OUTER_R - screw_d / 2.0 - 3.0, -clip_w / 2.0 - 0.5))
        .circle(screw_d / 2.0)
        .extrude(max(3.0, wall) + 1.0)
    )
    body = body.cut(hole)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_edge_clip():
    """A push-on sheet-metal edge clip carrying a hose C-cradle. The edge grip is
    a solid block with a C-slot (open on one side, vented) sized to the panel
    thickness; the hose cradle is fused on top through a solid neck."""
    grip_gap = edge_th + 2.0 * clearance
    jaw = max(2.0, wall)
    grip_h = max(hose_od, 14.0)
    grip_body_d = edge_reach + jaw
    # Grip block: spans X = clip_w, Y = grip_body_d (onto the panel), Z = grip_h.
    grip = (
        cq.Workplane("XY")
        .box(clip_w, grip_body_d, grip_h, centered=(True, True, False))
    )
    try:
        grip = grip.edges("|X").fillet(min(2.0, jaw * 0.6))
    except Exception:
        pass
    # Slot for the panel: a horizontal channel open on the -Y face (the mouth),
    # cut into the middle of the grip. Open one side → vented.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -grip_body_d / 2.0 - 1.0, grip_h / 2.0 - grip_gap / 2.0))
        .box(clip_w + 2.0, edge_reach + 1.0, grip_gap, centered=(True, True, False))
    )
    body = grip.cut(slot)
    # Hose cradle on top of the grip, fused through a neck (overlap union).
    cradle_z = grip_h + OUTER_R
    cradle = _c_clip(clip_w, 0.0, 0.0, cradle_z)
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, grip_h - 1.0))
        .box(clip_w, wall * 2.2, OUTER_R + 2.0, centered=(True, True, False))
    )
    body = body.union(neck).union(cradle)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_loom_rail():
    """A flat comb carrying several hose C-clips in a row, to route a loom bundle.
    The rail is a solid bar; each clip sits on it via a saddle (overlap union).
    End screw holes through the rail (vented)."""
    span = (n_clips - 1) * clip_pitch
    rail_len = span + 2.0 * (OUTER_R + 7.0)
    rail_w = clip_w + 5.0
    rail_th = max(3.0, wall + 1.0)
    rail = cq.Workplane("XY").box(rail_len, rail_w, rail_th, centered=(True, True, False))
    try:
        rail = rail.edges("|Z").fillet(min(4.0, rail_w * 0.25))
    except Exception:
        pass
    body = rail
    x0 = -span / 2.0
    for i in range(n_clips):
        cx = x0 + i * clip_pitch
        cz = rail_th + BORE_R - 0.5
        saddle = (
            cq.Workplane("XY")
            .center(cx, 0)
            .box(clip_w, wall * 2.4, rail_th + BORE_R, centered=(True, True, False))
        )
        body = body.union(saddle).union(_c_clip(clip_w, cx, 0.0, cz))
    hx = rail_len / 2.0 - (OUTER_R + 7.0) * 0.5
    holes = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .pushPoints([(-hx, 0.0), (hx, 0.0)])
        .circle(screw_d / 2.0)
        .extrude(rail_th + 1.0)
    )
    body = body.cut(holes)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "edge_clip":
    result = build_edge_clip()
elif target_part == "loom_rail":
    result = build_loom_rail()
else:  # "hose_clip"
    result = build_hose_clip()
