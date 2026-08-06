"""
Bag Reseal + Pour Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A slide-on C-channel clip that reseals an open bag by trapping a folded-over edge
in a tight channel, and (optionally) adds a funnel/pour channel so you can dispense
from the sealed corner without unclipping. Distinct from a sprung chip-clip: this
is a rigid, low-profile C-section you slide along the rolled bag top — like a
freezer-bag rail — so it holds a long seal and can carry a pour spout.

The clip cross-section is a single C profile (back wall + top and bottom lips with
a channel gap) extruded once across the clip width, so the body is inherently
watertight. Optional grip ribs line the channel; the spout variant fuses a tapered
nozzle whose bore passes through the back wall into the channel.

Modes (dispatched via `target_part`):
  * "clip"       — plain reseal C-clip at `clip_width`.
  * "spout_clip" — the clip plus a pour nozzle through the back wall (style
                   `clamp_with_spout`).
  * "wide_clip"  — a wider clip (1.8x) for cereal / freezer bags; same C profile.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `clip_width`).
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
clip_width = float(PARAM(lambda: clip_width, 90.0))   # seal length (mm, along Y)
channel    = float(PARAM(lambda: channel,     3.0))   # channel gap for the folded bag (mm)
lip        = float(PARAM(lambda: lip,        10.0))   # how far the lips reach over (mm)
wall       = float(PARAM(lambda: wall,        2.4))   # back wall / lip thickness (mm)
depth      = float(PARAM(lambda: depth,      18.0))   # channel height / clip height (mm, Z)
style      = str(  PARAM(lambda: style,   "clamp"))   # clamp | clamp_with_spout
grip_ribs  = bool( PARAM(lambda: grip_ribs, True))    # ribs inside the channel
spout_dia  = float(PARAM(lambda: spout_dia,  10.0))   # pour nozzle bore (mm)
spout_len  = float(PARAM(lambda: spout_len,  16.0))   # pour nozzle length (mm)

target_part = str(PARAM(lambda: target_part, "clip"))  # clip | spout_clip | wide_clip

# ── Derived + clamps ─────────────────────────────────────────────────────────
if target_part == "wide_clip":
    clip_width = clip_width * 1.8

clip_width = max(20.0, min(clip_width, 400.0))
channel = max(0.6, min(channel, 12.0))
lip = max(4.0, min(lip, 40.0))
wall = max(1.6, min(wall, 5.0))
depth = max(8.0, min(depth, 80.0))
spout_dia = max(3.0, min(spout_dia, 24.0))
spout_len = max(6.0, min(spout_len, 50.0))

# Cross-section reference (in the XZ plane, extruded along +Y by clip_width):
#   Back wall occupies x:[0, wall], full height z:[0, depth].
#   Top lip and bottom lip reach out to x = wall + lip, each `wall` thick.
#   The channel gap between the lips is `channel` tall, centered in height.
BACK_X = 0.0
LIP_X = wall + lip
CH_LOW = (depth - channel) / 2.0    # channel bottom face z
CH_HIGH = CH_LOW + channel          # channel top face z


# ── Geometry helpers ─────────────────────────────────────────────────────────
def c_profile():
    """The C cross-section as a closed polyline in XZ, extruded across the width.
    Trace: up the back wall, out along the top lip, back to the channel top,
    return to the back inner face, out along the bottom lip, and close."""
    inner_x = wall            # inner face of the back wall
    pts = [
        (BACK_X, 0.0),            # outer-bottom of back wall
        (BACK_X, depth),          # outer-top of back wall
        (LIP_X, depth),           # top-lip outer tip (top)
        (LIP_X, CH_HIGH),         # top-lip underside tip
        (inner_x, CH_HIGH),       # channel top, at back inner face
        (inner_x, CH_LOW),        # channel bottom, at back inner face
        (LIP_X, CH_LOW),          # bottom-lip upper tip
        (LIP_X, 0.0),             # bottom-lip outer tip (bottom)
    ]
    prof = cq.Workplane("XZ").polyline(pts).close()
    body = prof.extrude(clip_width)
    # Extrude along +Y from the XZ plane; recenter in Y so it is symmetric.
    return body.translate((0, -clip_width / 2.0, 0))


def add_grip_ribs(body):
    """Add shallow ribs on the top and bottom channel faces to bite the bag.
    Each rib ROOT is embedded into the lip material (overlap) so the union is a
    clean volumetric boolean rather than a fragile tangent kiss on the face."""
    try:
        n = max(2, int(lip / 3.0))
        rib_t = 0.8
        rib_h = min(0.9, channel * 0.35)
        ov = 0.6  # push the rib base into the lip
        for i in range(n):
            x = wall + 1.5 + i * 3.0
            if x > LIP_X - 1.0:
                break
            # Top rib: base inside the top lip, protruding down into the channel.
            top_rib = (
                cq.Workplane("XY")
                .box(rib_t, clip_width, rib_h + ov, centered=(True, True, False))
                .translate((x, 0, CH_HIGH - rib_h))
            )
            # Bottom rib: base inside the bottom lip, protruding up into channel.
            bot_rib = (
                cq.Workplane("XY")
                .box(rib_t, clip_width, rib_h + ov, centered=(True, True, False))
                .translate((x, 0, CH_LOW - ov))
            )
            body = body.union(top_rib).union(bot_rib)
    except Exception:
        pass  # ribs are a grip aid — never fatal
    return body


def add_spout(body):
    """Fuse a tapered pour nozzle to the back wall; bore passes into the channel
    so contents flow from the bag, through the wall, out the nozzle."""
    zc = depth / 2.0
    base_r = spout_dia / 2.0 + wall
    tip_r = spout_dia / 2.0 + max(1.0, wall - 0.6)
    # Nozzle grows in -X from the back wall outer face.
    nozzle = (
        cq.Workplane("YZ")
        .workplane(offset=-1.0)             # start just inside the back wall
        .circle(base_r)
        .workplane(offset=spout_len + 1.0)
        .circle(tip_r)
        .loft(combine=True)
    )
    # YZ workplane extrudes along +X by default; we want -X, so mirror in X.
    nozzle = nozzle.mirror("YZ").translate((BACK_X, 0, zc))
    body = body.union(nozzle)
    # Bore: from nozzle tip through the back wall into the channel.
    bore = (
        cq.Workplane("YZ")
        .circle(spout_dia / 2.0)
        .extrude(-(spout_len + wall + 2.0))
        .translate((wall + 1.0, 0, zc))
    )
    body = body.cut(bore)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_clip():
    body = c_profile()
    if grip_ribs:
        body = add_grip_ribs(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_spout_clip():
    body = c_profile()
    if grip_ribs:
        body = add_grip_ribs(body)
    body = add_spout(body)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "spout_clip" or (target_part == "clip" and style == "clamp_with_spout"):
    result = build_spout_clip()
else:
    result = build_clip()
