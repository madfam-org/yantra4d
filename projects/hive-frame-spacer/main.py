"""
Hive Frame Spacer — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Spacers that hold Langstroth frames at the correct pitch inside a hive body. This
cartridge rests on the one hard published dimension in beekeeping: BEE SPACE.

Bee space, in one paragraph:
  L. L. Langstroth's 1852 patent turned on the observation that bees treat a gap of
  roughly 6 to 9 mm as a passage and leave it open, while they fill anything SMALLER
  with propolis and build comb across anything LARGER. Hold every gap in the hive
  inside that band and the frames stay separate and liftable; miss it and the colony
  glues the box into a single mass that cannot be inspected without destroying comb.
  This is the whole reason a modern hive comes apart at all.

The consequence for spacing:
  A frame's comb face and its neighbour's must sit at a pitch of comb thickness plus
  one bee space. The conventional Langstroth pitch is 35 mm — ten frames in a
  ten-frame box — and 38 mm when nine frames are spread in the same box to draw
  fatter honey comb. The spacer's job is to make that pitch mechanical rather than
  eyeballed, because a hive spaced by eye drifts, and drifted frames get braced
  together with burr comb.

The frame hangs by its LUG: a short tab at each end of the top bar that rests on a
rebate (the "frame rest") milled into the hive body's end wall. The lug is the only
interface a spacer can grip, so lug width is a declared parameter.

Standards encoded (mm), from the published Langstroth frame geometry:
  Deep (Hoffman) frame    top bar 482.6 long (19"), depth 232 (9-1/8")
  Medium frame            same top bar, depth 168 (6-1/4")
  Shallow frame           same top bar, depth 137 (5-3/8")
  Lug: ~9.5 mm projection each end, 25.4 mm (1") nominal wide, ~9.5 mm thick
  Bee space: 6.0-9.5 mm; 8.0 mm is the usual working value
  Frame pitch: 35 mm (ten-frame) / 38 mm (nine-frame spread)

Modes are dispatched via `target_part`:
  * "rail"       — a comb rail that drops into the frame rest; its castellations set
                   the pitch for a whole wall of frames at once.
  * "clip"       — a per-frame lug clip, for retrofitting a box that already has
                   frames in it without lifting them all out.
  * "end_spacer" — a follower-board spacer that takes up the slack at the end of a
                   short row, so the last frame cannot slide and crush bees.

Watertightness strategy:
  Every part is one blank with THROUGH cuts. The rail's castellation notches are cut
  from a blank that is sized FROM the notch layout (count x pitch plus end margins),
  never sized independently and hoped to fit — that ordering is what stops a
  max-pitch, max-count layout from running its last notch off the end and severing
  the rail. Notch depth is capped as a fraction of rail height so a continuous spine
  always survives; a notch that reaches the bottom face turns one rail into N loose
  teeth. No fillet is taken on any edge that a notch or bore has touched: OCC blends
  such arcs without raising and returns a non-watertight solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Langstroth frame standards ───────────────────────────────────────────────
# Top bar length is shared across all three depths — the frames differ only in how
# far down they hang, which is why one spacer geometry serves the whole family.
FRAME_STANDARDS = {
    "deep":    {"depth": 232.0, "top_bar": 482.6, "pitch": 35.0, "label": "Langstroth deep (9-1/8 in)"},
    "medium":  {"depth": 168.0, "top_bar": 482.6, "pitch": 35.0, "label": "Langstroth medium (6-1/4 in)"},
    "shallow": {"depth": 137.0, "top_bar": 482.6, "pitch": 35.0, "label": "Langstroth shallow (5-3/8 in)"},
    # Nine frames spread across a ten-frame box: the bees draw fatter honey comb,
    # which uncaps more cleanly. Same hardware, wider pitch.
    "nine_frame": {"depth": 232.0, "top_bar": 482.6, "pitch": 38.0, "label": "Nine-frame spread (deep)"},
}


def frame_geo(name):
    """Look up nominal frame geometry, defaulting to the deep Langstroth."""
    return FRAME_STANDARDS.get(name, FRAME_STANDARDS["deep"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rail"))
frame_std = str(PARAM(lambda: frame_std, "deep"))

bee_space_mm = float(PARAM(lambda: bee_space_mm, 8.0))       # the gap bees leave open
lug_width_mm = float(PARAM(lambda: lug_width_mm, 25.4))      # frame lug width (1 in nominal)
spacer_count = float(PARAM(lambda: spacer_count, 10.0))      # frames the rail spaces
rail_thickness = float(PARAM(lambda: rail_thickness, 4.0))   # rail / clip wall
lug_thickness_mm = float(PARAM(lambda: lug_thickness_mm, 9.5))  # frame lug thickness

# Clamp so extreme UI values still build watertight.
bee_space_mm = max(4.0, min(bee_space_mm, 12.0))
lug_width_mm = max(12.0, min(lug_width_mm, 40.0))
spacer_count = max(2.0, min(round(spacer_count), 12.0))
rail_thickness = max(2.0, min(rail_thickness, 10.0))
lug_thickness_mm = max(4.0, min(lug_thickness_mm, 16.0))


# ── Derived pitch ────────────────────────────────────────────────────────────
def frame_pitch():
    """Centre-to-centre frame pitch (mm).

    The standard's own pitch is the base; bee space is then applied as a DEVIATION
    from the nominal 8 mm working value, so moving the bee-space slider moves the
    pitch the way it physically would. Clamped so a notch can never be wider than
    the pitch that has to contain it."""
    g = frame_geo(frame_std)
    pitch = g["pitch"] + (bee_space_mm - 8.0)
    return max(lug_width_mm + 2.0, min(pitch, 60.0))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_rail():
    """A castellated comb rail that drops into the hive's frame rest and sets the
    pitch for a whole wall of frames at once.

    The blank is derived FROM the notch layout — count x pitch plus a full end
    margin — not sized independently. Sizing it separately is how a maximum-pitch,
    maximum-count layout runs its last notch off the end and severs the rail."""
    n = int(spacer_count)
    pitch = frame_pitch()
    notch_w = min(lug_width_mm + 0.8, pitch - 2.0)   # lug slips in with a little slop
    notch_w = max(2.0, notch_w)

    end_margin = max(4.0, rail_thickness * 1.5)
    length = n * pitch + 2.0 * end_margin
    height = max(8.0, lug_thickness_mm * 0.9 + rail_thickness)
    width = max(6.0, rail_thickness * 2.5)

    body = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))

    # Notch depth capped so a continuous spine ALWAYS survives beneath the teeth.
    # A notch that reaches the bottom face turns one rail into N loose teeth: still
    # tessellates, but it is not a rail.
    spine = max(1.5, rail_thickness * 0.8)
    notch_d = max(1.0, min(lug_thickness_mm * 0.85, height - spine))

    for i in range(n):
        x = -length / 2.0 + end_margin + pitch * (i + 0.5)
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0.0, height - notch_d))
            .box(notch_w, width + 2.0, notch_d + 1.0, centered=(True, True, False))
        )
        body = body.cut(notch)

    # Screw/nail bores through the spine at both ends, so the rail can be fixed into
    # the frame rest. Through-cut in Z, opened past both faces.
    hole_r = min(2.0, spine * 0.35, width * 0.2)
    if hole_r >= 0.8:
        for sign in (-1.0, 1.0):
            x = sign * (length / 2.0 - end_margin * 0.5)
            bore = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0.0, -1.0))
                .circle(hole_r).extrude(height + 2.0)
            )
            try:
                body = body.cut(bore)
            except Exception:
                pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_clip():
    """A per-frame lug clip: it grips one frame's lug and stands off its neighbour by
    exactly one pitch, so a box already full of frames can be re-spaced without
    lifting every frame out.

    The jaw is a U opened UPWARD (the lug drops in from above); the mouth runs past
    the top of the blank so it is a real opening, never a sealed pocket."""
    pitch = frame_pitch()
    jaw_w = lug_width_mm + 0.6
    jaw_d = lug_thickness_mm + 0.6
    wall = rail_thickness

    # Stand-off arm carries the neighbouring lug one pitch away.
    arm_len = max(2.0, pitch - jaw_w / 2.0 - wall)

    body_w = jaw_w + 2.0 * wall
    body_d = jaw_d + 2.0 * wall
    height = jaw_d + wall            # jaw depth plus a floor

    body = cq.Workplane("XY").box(body_w, body_d, height, centered=(True, True, False))

    # The lug pocket, opened THROUGH the top face and out both Y faces, so the lug
    # can be dropped in and the clip slid along the bar.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, wall))
        .box(jaw_w, body_d + 2.0, jaw_d + 2.0, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Stand-off arm: a volumetric union overlapping the body, never a tangent kiss.
    # Its span is computed EXPLICITLY so the stop can be placed from the arm's real
    # end rather than from an independent formula.
    arm_t = max(2.0, wall * 0.9)
    arm_y = min(body_d, jaw_w * 0.6)
    arm_x0 = body_w / 2.0 - wall              # starts INSIDE the body, so the union
    arm_x1 = arm_x0 + wall + arm_len          # is volumetric, not a face-to-face kiss
    arm = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((arm_x0 + arm_x1) / 2.0, 0.0, 0.0))
        .box(arm_x1 - arm_x0, arm_y, arm_t, centered=(True, True, False))
    )
    body = body.union(arm)

    # A stop at the arm's far end that the next lug bears against.
    #
    # Positioned from `arm_x1` — the arm's ACTUAL end — and pulled back into the arm
    # by half its own width so the two overlap volumetrically. The first draft placed
    # the stop at `body_w/2 - wall*0.5 + arm_len` while the arm ended at 26.0, which
    # left the stop floating in a 5 mm air gap. It rendered watertight (both solids
    # are closed) and only `body_count == 2` caught it — a reminder that watertight
    # alone does not mean connected.
    stop_h = max(3.0, jaw_d * 0.45)
    stop_w = max(2.0, wall)
    stop_cx = arm_x1 - stop_w / 2.0
    stop = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(stop_cx, 0.0, 0.0))
        .box(stop_w, arm_y, stop_h, centered=(True, True, False))
    )
    body = body.union(stop)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_end_spacer():
    """A follower-board spacer taking up slack at the end of a short row.

    A box run with fewer frames than it holds leaves a gap the last frame slides
    across, and a sliding frame crushes bees against the wall. This wedge fills that
    slack to a stated width."""
    pitch = frame_pitch()
    g = frame_geo(frame_std)

    # Width of slack to fill: whatever a box of `spacer_count` frames leaves over a
    # nominal ten-frame interior. Clamped to something printable and never zero.
    interior = 10.0 * g["pitch"]
    slack = interior - spacer_count * pitch
    width = max(4.0, min(abs(slack), 80.0))

    # Height follows the frame family: it stands beside the frame, not above it.
    height = max(20.0, min(g["depth"] * 0.35, 90.0))
    length = max(20.0, min(g["top_bar"] * 0.12, 70.0))
    wall = rail_thickness

    body = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))

    # Hollow it so it is not a solid brick of filament, but keep a full floor and a
    # full rim: the pocket is inset by `wall` on every side and stops `wall` short of
    # the bottom, so it is a real closed cavity in a closed solid.
    pw = width - 2.0 * wall
    pl = length - 2.0 * wall
    ph = height - 2.0 * wall
    if pw > 1.5 and pl > 1.5 and ph > 1.5:
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, wall))
            .box(pl, pw, ph + 1.0, centered=(True, True, False))
        )
        try:
            body = body.cut(pocket)
        except Exception:
            pass

    # A hanging lip so it rests on the box rim instead of falling to the floor.
    lip_l = length
    lip_w = width + max(4.0, wall * 2.0)
    lip_h = max(3.0, wall)
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, height - lip_h))
        .box(lip_l, lip_w, lip_h, centered=(True, True, False))
    )
    body = body.union(lip)

    # Finger hole through the lip so it can be lifted out of a sticky box. Cut in Z
    # through the lip only, opened past both of its faces.
    fr = min(6.0, lip_l * 0.25, lip_w * 0.2)
    if fr >= 2.0:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0.0, 0.0, height - lip_h - 1.0))
            .circle(fr).extrude(lip_h + 2.0)
        )
        try:
            body = body.cut(hole)
        except Exception:
            pass

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "rail": build_rail,
    "clip": build_clip,
    "end_spacer": build_end_spacer,
}

result = _dispatch.get(target_part, build_rail)()
