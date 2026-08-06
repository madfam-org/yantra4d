"""
Cutting-Board Non-Slip Feet — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Clip-on feet that lift a cutting board off the counter and stop it sliding. Each
foot is a C-clip that grips the board edge (channel sized to `board_t`) with a
textured pad underneath. Three forms:

  * "clip_foot"   — a straight edge clip + foot pad (slides onto any straight edge).
  * "corner_foot" — an L-shaped clip that wraps a corner (grips two edges) for
                    boards that need positive location.
  * "riser_set"   — a taller riser foot (for draining / airflow) on the same clip.

The board-edge clip is the shared interface: the channel spans `board_t` plus a
print clearance, and a spring lip keeps it on. The C cross-section is extruded once
(watertight), then a pad is fused below with an overlap for a clean boolean.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `board_t`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name
    (the sandbox does not expose globals()/NameError directly)."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
board_t    = float(PARAM(lambda: board_t,    18.0))  # cutting board thickness (mm)
foot_h     = float(PARAM(lambda: foot_h,      10.0))  # foot pad height below board (mm)
clip_len   = float(PARAM(lambda: clip_len,    30.0))  # length of the clip along the edge (mm)
grip_depth = float(PARAM(lambda: grip_depth,  14.0))  # how far the clip reaches onto the face (mm)
wall       = float(PARAM(lambda: wall,         3.0))  # clip wall thickness (mm)
clearance  = float(PARAM(lambda: clearance,    0.3))  # channel fit clearance (per side, mm)
pad_grip   = bool( PARAM(lambda: pad_grip,    True))  # anti-slip texture on the pad base
riser_h    = float(PARAM(lambda: riser_h,     22.0))  # riser foot height (riser_set)

target_part = str(PARAM(lambda: target_part, "clip_foot"))  # clip_foot|corner_foot|riser_set

# ── Clamps ───────────────────────────────────────────────────────────────────
board_t = max(4.0, min(board_t, 60.0))
foot_h = max(4.0, min(foot_h, 40.0))
clip_len = max(12.0, min(clip_len, 120.0))
grip_depth = max(6.0, min(grip_depth, 60.0))
wall = max(1.6, min(wall, 6.0))
clearance = max(0.0, min(clearance, 1.0))
riser_h = max(foot_h + 4.0, min(riser_h, 80.0))

# Channel geometry (cross-section in XZ, extruded along +Y = along the edge):
#   The clip opens downward-facing? No — it opens toward the board (in +X). The
#   board edge slides into a channel of height `chan = board_t + 2*clearance`.
CHAN = board_t + 2.0 * clearance
# Overall clip height = channel + top and bottom wall.
CLIP_H = CHAN + 2.0 * wall
REACH = wall + grip_depth   # x-extent of the top/bottom lips


# ── Geometry ─────────────────────────────────────────────────────────────────
def clip_profile(length, bevel=True):
    """C cross-section (opening toward +X) extruded `length` along +Y.

    Trace (XZ): back wall on the left (x:[0,wall]), top lip and bottom lip reach
    out to REACH, channel gap `CHAN` between them. The board slides in from +X.
    Lip tips are beveled HERE (before any pad union) so the chamfer only sees the
    clean lip edges — a post-union `>X` chamfer over the pad edges crashes OCCT."""
    back_x = 0.0
    inner_x = wall
    ch_low = wall
    ch_high = wall + CHAN
    pts = [
        (back_x, 0.0),          # bottom-outer of back wall
        (back_x, CLIP_H),       # top-outer of back wall
        (REACH, CLIP_H),        # top lip tip (top face)
        (REACH, ch_high),       # top lip underside
        (inner_x, ch_high),     # channel top at back inner face
        (inner_x, ch_low),      # channel bottom at back inner face
        (REACH, ch_low),        # bottom lip upper face
        (REACH, 0.0),           # bottom lip tip (bottom face)
    ]
    body = cq.Workplane("XZ").polyline(pts).close().extrude(length)
    body = body.translate((0, -length / 2.0, 0))
    if bevel:
        try:
            body = body.edges(">X").edges("|Y").chamfer(min(1.0, wall * 0.4))
        except Exception:
            pass  # lip bevel is an ease-of-use aid — never fatal
    return body


def foot_pad(length, pad_h):
    """A pad fused UNDER the clip (below z=0), overlapping the bottom lip so the
    union is a clean volumetric boolean. Slightly wider footprint for stability."""
    ov = 0.8
    pad_w = REACH + 2.0
    pad = (
        cq.Workplane("XY")
        .box(pad_w, length + 2.0, pad_h + ov, centered=(False, True, False))
        .translate((-1.0, 0, -pad_h))
    )
    # Round the pad's vertical edges a touch for comfort (non-fatal).
    try:
        pad = pad.edges("|Z").fillet(min(2.0, pad_h * 0.3))
    except Exception:
        pass
    if pad_grip:
        pad = _texture_base(pad, pad_w, length, pad_h)
    return pad


def _texture_base(pad, pad_w, length, pad_h):
    """Cut shallow anti-slip grooves into the bottom face of the pad."""
    try:
        n = max(2, int(pad_w / 3.0))
        for i in range(n):
            x = -1.0 + 1.5 + i * 3.0
            if x > pad_w - 1.5:
                break
            groove = (
                cq.Workplane("XY")
                .box(1.0, length + 3.0, 1.0, centered=(True, True, False))
                .translate((x, 0, -pad_h - 0.3))
            )
            pad = pad.cut(groove)
    except Exception:
        pass  # texture is cosmetic — never fatal
    return pad


def build_clip_foot():
    body = clip_profile(clip_len)
    body = body.union(foot_pad(clip_len, foot_h))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_corner_foot():
    """Two clip runs meeting at a right angle so the foot wraps a board corner."""
    leg = clip_profile(clip_len)
    leg = leg.union(foot_pad(clip_len, foot_h))
    # Second leg: rotate 90° about Z and shift so the two channels share a corner.
    leg_b = leg.rotate((0, 0, 0), (0, 0, 1), 90)
    # Position both legs so their back-wall inner faces form an L at the origin.
    leg_a = leg.translate((0, clip_len / 2.0, 0))
    leg_b = leg_b.translate((clip_len / 2.0, 0, 0))
    body = leg_a.union(leg_b)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_riser_set():
    """A taller riser foot (for airflow / draining) on the same edge clip."""
    body = clip_profile(clip_len)
    body = body.union(foot_pad(clip_len, riser_h))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "corner_foot":
    result = build_corner_foot()
elif target_part == "riser_set":
    result = build_riser_set()
else:
    result = build_clip_foot()
