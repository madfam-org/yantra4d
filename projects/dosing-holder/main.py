"""
Drip / Dosing Line Holder — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Reef dosing pumps, RODI top-off and CO2/drip systems run thin silicone and vinyl
lines that flap around the tank. This cartridge clips those lines tidily: a snap
C-clip around the tube, a rim clip that hangs a line over the tank edge, and a
multi-line routing rail.

  * "line_clip"  — a C-clip that snaps over a single dosing / airline tube and
                   has a peg to press into a hole or a foam wall
                   (target_part == "line_clip").
  * "rim_clip"   — a hook over the tank rim with a tube C-cradle, so a line
                   drops into the tank from the edge (target_part == "rim_clip").
  * "multi_clip" — a flat rail carrying several tube C-clips in a row for
                   routing multiple lines together (target_part == "multi_clip").

Real dimensions (aquarium tubing nominal):
  - Standard aquarium airline OD = 6.35 mm (1/4 in); the 3/16 in is the ID.
  - 1/4 in RO/RODI tubing OD = 6.35 mm exactly (one clip fits both).
  - Rigid 3/16 in tubing OD = 4.76 mm; 3/8 in tubing OD = 9.525 mm.
  - Peristaltic dosing silicone tube OD 4-6 mm.
  - Tank rim / glass edge thickness ~5-12 mm (nano to large).

Watertight strategy (the brief's C-section rule): every clip is a full ring
(outer circle minus bore) minus a MOUTH slot narrower than the diameter, so it
snaps and retains — a single manifold C-section, never a tangent kiss. The rim
hook is an extruded closed J-profile. Rails and pegs are solid and OVERLAP into
the clip body. Each result is one manifold solid.

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
target_part = str(PARAM(lambda: target_part, "line_clip"))  # line_clip | rim_clip | multi_clip

tube_od = float(PARAM(lambda: tube_od, 6.35))     # tube outer diameter (mm)
wall = float(PARAM(lambda: wall, 2.2))            # clip wall thickness (mm)
clip_w = float(PARAM(lambda: clip_w, 8.0))        # clip width along the tube (mm)
mouth = float(PARAM(lambda: mouth, 0.78))         # mouth opening as fraction of tube OD (grip)
rim_th = float(PARAM(lambda: rim_th, 8.0))        # tank rim thickness the hook straddles (mm)
hook_drop = float(PARAM(lambda: hook_drop, 18.0))  # how far the rim hook reaches down inside (mm)
clearance = float(PARAM(lambda: clearance, 0.3))  # per-side slip clearance (mm)
n_clips = int(float(PARAM(lambda: n_clips, 3)))   # clips on the multi rail
clip_pitch = float(PARAM(lambda: clip_pitch, 14.0))  # spacing on the multi rail (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
tube_od = max(2.5, min(tube_od, 25.0))
wall = max(1.4, min(wall, 5.0))
clip_w = max(4.0, min(clip_w, 30.0))
mouth = max(0.55, min(mouth, 0.92))
rim_th = max(3.0, min(rim_th, 20.0))
hook_drop = max(8.0, min(hook_drop, 60.0))
clearance = max(0.0, min(clearance, 1.2))
n_clips = max(1, min(n_clips, 8))
clip_pitch = max(tube_od + 2.0 * wall + 2.0, min(clip_pitch, 40.0))

BORE_R = tube_od / 2.0 + clearance      # tube cradle inner radius
OUTER_R = BORE_R + wall                 # clip outer radius


# ── Helpers ──────────────────────────────────────────────────────────────────
def _c_clip(width, cx=0.0, cy=0.0, cz=0.0):
    """A snap C-clip: a full ring (axis along X) minus a mouth slot narrower than
    the bore so the tube snaps in and is retained. One manifold C-section.
    Centred at (cx, cy, cz), mouth facing +Y (up-and-open)."""
    ring = (
        cq.Workplane("YZ")
        .circle(OUTER_R)
        .circle(BORE_R)
        .extrude(width)
        .translate((-width / 2.0, 0, 0))
    )
    mouth_w = max(1.2, tube_od * mouth)
    slot = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, OUTER_R, 0))
        .rect(mouth_w, OUTER_R * 2.2)
        .extrude(width + 2.0)
        .translate((-width / 2.0 - 1.0, 0, 0))
    )
    clip = ring.cut(slot)
    return clip.translate((cx, cy, cz))


def _rim_hook(inner_drop, w):
    """A J-hook straddling the tank rim: outer leg, top bridge, inner leg dropping
    `inner_drop`. Extruded closed profile in YZ, along X by width w. Centred X."""
    t = wall
    g = rim_th + 2.0 * clearance
    outer_leg = 7.0
    prof = (
        cq.Workplane("YZ")
        .polyline([
            (0.0, 0.0),
            (0.0, outer_leg + t),
            (g + 2.0 * t, outer_leg + t),
            (g + 2.0 * t, outer_leg + t - inner_drop),
            (g + t, outer_leg + t - inner_drop),
            (g + t, outer_leg),
            (t, outer_leg),
            (t, 0.0),
        ])
        .close()
        .extrude(w)
    )
    return prof.translate((-w / 2.0, 0, 0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_line_clip():
    """A single tube C-clip with a mounting peg that presses into a hole or foam.
    The peg overlaps into the clip's outer wall (volumetric union)."""
    clip = _c_clip(clip_w)
    # Peg on the underside (-Y), pointing down, to push into a hole/foam wall.
    peg = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -OUTER_R + 0.5, 0))
        .transformed(rotate=cq.Vector(90, 0, 0))
        .circle(max(1.5, wall * 1.1))
        .extrude(max(5.0, tube_od * 0.9))
    )
    body = clip.union(peg)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_rim_clip():
    """A rim hook with a tube C-cradle on the inner face, so a dosing line drops
    into the tank from the rim. Hook + cradle fused through a solid neck."""
    hook = _rim_hook(hook_drop, clip_w)
    outer_leg = 7.0
    inner_face_y = rim_th + 2.0 * clearance + 2.0 * wall
    cradle_z = outer_leg + wall - hook_drop + OUTER_R + wall
    cradle_y = inner_face_y + OUTER_R
    cradle = _c_clip(clip_w, 0.0, cradle_y, cradle_z)
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, inner_face_y, cradle_z))
        .box(clip_w, OUTER_R + 2.0, wall * 2.0, centered=(True, False, True))
    )
    body = hook.union(neck).union(cradle)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_multi_clip():
    """A flat rail carrying several tube C-clips in a row, for routing several
    dosing lines together. The rail is a solid bar; each clip overlaps down onto
    it (volumetric union). A mounting hole at each end (through, vented)."""
    span = (n_clips - 1) * clip_pitch
    rail_len = span + 2.0 * (OUTER_R + 6.0)
    rail_w = clip_w + 4.0
    rail_th = max(3.0, wall + 1.0)
    rail = (
        cq.Workplane("XY")
        .box(rail_len, rail_w, rail_th, centered=(True, True, False))
    )
    try:
        rail = rail.edges("|Z").fillet(min(4.0, rail_w * 0.3))
    except Exception:
        pass
    body = rail
    x0 = -span / 2.0
    for i in range(n_clips):
        cx = x0 + i * clip_pitch
        # Clip axis runs along X, sitting ON the rail; lift it so its bore is
        # above the rail and its lower wall overlaps into the rail top.
        cz = rail_th + BORE_R - 0.5
        clip = _c_clip(clip_w, cx, 0.0, cz)
        # a small saddle block tying clip to rail (overlap union)
        saddle = (
            cq.Workplane("XY")
            .center(cx, 0)
            .box(clip_w, wall * 2.2, rail_th + BORE_R, centered=(True, True, False))
        )
        body = body.union(saddle).union(clip)
    # End mounting holes through the rail.
    hx = rail_len / 2.0 - (OUTER_R + 6.0) * 0.5
    holes = (
        cq.Workplane("XY")
        .workplane(offset=-0.5)
        .pushPoints([(-hx, 0.0), (hx, 0.0)])
        .circle(max(1.6, wall))
        .extrude(rail_th + 1.0)
    )
    body = body.cut(holes)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rim_clip":
    result = build_rim_clip()
elif target_part == "multi_clip":
    result = build_multi_clip()
else:  # "line_clip"
    result = build_line_clip()
