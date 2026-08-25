"""
PneuNet Bending Finger — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The canonical soft bending actuator. A PneuNet ("pneumatic network") finger is
a row of thin-walled chambers sharing one supply channel, sitting on a thick,
inextensible strain-limiting layer. Pressurise the network and the chamber
walls balloon and push against each other; because the bottom layer cannot
stretch, the whole finger curls into a hook. No joints, no tendons.

Chamber PITCH is the published bend parameter: more chambers over the same
length curl tighter for the same pressure, because each chamber contributes a
fixed wall-to-wall rotation. It is exposed as a CDG profile interface so a
gripper assembly can state the bend radius it needs.

The root flange carries the bolt pattern shared with `soft-gripper-pad` and
`tool-gripper`, and the inlet is the shared barb series from
`pneumatic-barb-port` (same `tube_id`) fed by `vacuum-manifold-block`.

Modes:
  - finger      : the full PneuNet finger — chamber network + strain layer +
                  root flange + barb inlet.
  - finger_pair : two opposed fingers on a common root bar, the minimum gripper.
  - root_flange : just the bolt-through root, printable in rigid material and
                  glued to a TPU finger.

Watertight strategy: the finger is ONE extruded prism (strain layer + chamber
block). Chambers are rectangular pockets cut from the top with a floor and side
walls left everywhere; the supply channel is one long cut through the strain
layer that intersects every chamber. Every cut is a full-depth boolean on a
solid — no shelling, no lofted membranes. Chamber count is derived from length
and pitch and floored at 1, so extremes never produce a zero-chamber or
wall-eating result.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Print in TPU (Shore 85–95A). LOW-PRESSURE only.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "finger"))
# "finger" | "finger_pair" | "root_flange"

finger_len   = float(PARAM(lambda: finger_len,   90.0))  # active length (X)
finger_w     = float(PARAM(lambda: finger_w,     20.0))  # finger width (Y)
chamber_h    = float(PARAM(lambda: chamber_h,    14.0))  # chamber block height (Z)
chamber_pitch = float(PARAM(lambda: chamber_pitch, 8.0)) # chamber centre spacing
chamber_gap  = float(PARAM(lambda: chamber_gap,   1.4))  # wall between chambers
wall         = float(PARAM(lambda: wall,          1.4))  # chamber side/roof wall
strain_th    = float(PARAM(lambda: strain_th,     3.0))  # inextensible bottom layer
channel_w    = float(PARAM(lambda: channel_w,     3.0))  # supply channel width
tube_id      = float(PARAM(lambda: tube_id,       3.0))  # inlet tubing inner dia
bore         = float(PARAM(lambda: bore,          1.8))  # inlet passage diameter
root_len     = float(PARAM(lambda: root_len,     16.0))  # solid root length (X)
bolt_dia     = float(PARAM(lambda: bolt_dia,      3.4))  # M3 clearance

# ── Clamps ───────────────────────────────────────────────────────────────────
finger_len    = max(25.0, min(finger_len, 220.0))
finger_w      = max(8.0,  min(finger_w, 60.0))
chamber_h     = max(5.0,  min(chamber_h, 40.0))
chamber_pitch = max(3.0,  min(chamber_pitch, 25.0))
chamber_gap   = max(0.6,  min(chamber_gap, 8.0))
wall          = max(0.6,  min(wall, 5.0))
strain_th     = max(1.2,  min(strain_th, 10.0))
channel_w     = max(1.0,  min(channel_w, 12.0))
tube_id       = max(1.5,  min(tube_id, 10.0))
bore          = max(0.8,  min(bore, 8.0))
root_len      = max(6.0,  min(root_len, 60.0))
bolt_dia      = max(1.5,  min(bolt_dia, 8.0))

# ── Derived, clamped so no cut can ever break the shell ──────────────────────
TOTAL_H = strain_th + chamber_h
# Side walls must leave a real chamber cavity in Y.
CAV_W = finger_w - 2.0 * wall
CAV_W = max(1.0, min(CAV_W, finger_w - 0.8))
# Chamber cavity height must leave a roof AND a channel floor over the strain layer.
CAV_H = chamber_h - wall
CAV_H = max(0.8, min(CAV_H, chamber_h - 0.4))
# Effective chamber slot width along X (pitch minus the dividing wall).
SLOT_X = chamber_pitch - chamber_gap
SLOT_X = max(0.8, min(SLOT_X, chamber_pitch - 0.4))
# How many chambers fit in the active length; always at least one.
N_CHAM = max(1, int(finger_len // chamber_pitch))
ACTIVE = N_CHAM * chamber_pitch
# Supply channel sits in the TOP of the strain layer, under the chambers.
CHAN_W = min(channel_w, CAV_W - 0.6)
CHAN_W = max(0.6, CHAN_W)
CHAN_H = min(max(0.8, strain_th * 0.45), strain_th - 0.8)
CHAN_H = max(0.5, CHAN_H)
# Inlet barb, shared series.
STEM_R = max(tube_id / 2.0, bore / 2.0 + 0.8)
BORE_R = min(bore / 2.0, STEM_R - 0.6, CHAN_W / 2.0 - 0.1, CHAN_H / 2.0 + 0.2)
BORE_R = max(0.35, BORE_R)
BARB_R = STEM_R + 0.7
STEM_L = 9.0
# Root bolts must fit inside the root block.
BOLT_R = min(bolt_dia / 2.0, root_len / 4.0 - 0.4, finger_w / 4.0 - 0.6)
BOLT_R = max(0.5, BOLT_R)

TOTAL_X = root_len + ACTIVE


# ── Helpers ──────────────────────────────────────────────────────────────────
def finger_blank():
    """Solid prism: strain layer + chamber block, root at X=0."""
    return (
        cq.Workplane("XY")
        .box(TOTAL_X, finger_w, TOTAL_H, centered=(False, True, False))
    )


def chamber_cuts():
    """One fused tool of all chamber pockets, cut from the top face down to the
    channel roof. Each pocket leaves `wall` of roof, `wall` of side, and
    `chamber_gap` of divider material."""
    tool = None
    z0 = strain_th  # pockets start at the top of the strain layer
    for i in range(N_CHAM):
        x0 = root_len + i * chamber_pitch + chamber_gap / 2.0
        pocket = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x0, 0, z0))
            .box(SLOT_X, CAV_W, CAV_H, centered=(False, True, False))
        )
        tool = pocket if tool is None else tool.union(pocket)
    return tool


def channel_cut():
    """The single supply channel: a slot in the top of the strain layer running
    the whole active length, intersecting every chamber pocket."""
    z0 = strain_th - CHAN_H
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(root_len * 0.35, 0, z0))
        .box(TOTAL_X - root_len * 0.35 + 0.5, CHAN_W, CHAN_H + 0.2,
             centered=(False, True, False))
    )


def inlet_barb():
    """Barb stem on the root end face, feeding the supply channel.

    Built entirely along +Z (stem AND ridges on the same workplane, so the
    union always overlaps), then rotated so +Z becomes -X and translated so
    its tip sits at x = -STEM_L, on the channel centreline in Z. Building the
    ridges on a different workplane than the stem is exactly how you get
    floating rings — don't."""
    zc = strain_th - CHAN_H / 2.0
    body = cq.Workplane("XY").circle(STEM_R).extrude(STEM_L)
    for i in range(2):
        zb = 1.2 + i * 3.2
        zb = min(zb, STEM_L - 2.4)
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(BARB_R)
            .workplane(offset=2.0)
            .circle(STEM_R)
            .loft(ruled=True)
        )
        body = body.union(ridge)
    # +Z → -X is a -90° rotation about Y.
    body = body.rotate((0, 0, 0), (0, 1, 0), -90.0)
    # After the rotation the stem occupies x in [-STEM_L, 0]; place it on the
    # channel centreline.
    return body.translate((0, 0, zc))


def root_bolts():
    """Two bolt holes through the solid root block (Z through)."""
    tool = None
    xs = [root_len * 0.3, root_len * 0.72]
    ys = [0.0] if finger_w < 4.0 * BOLT_R + 4.0 else [-finger_w * 0.26, finger_w * 0.26]
    for x in xs:
        for y in ys:
            h = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, y, -1.0))
                .circle(BOLT_R)
                .extrude(TOTAL_H + 2.0)
            )
            tool = h if tool is None else tool.union(h)
    return tool


# ── Part builders ────────────────────────────────────────────────────────────
def build_finger():
    body = finger_blank()
    body = body.cut(chamber_cuts())
    body = body.cut(channel_cut())
    # inlet_barb() already places itself on the -X end face at x in [-STEM_L, 0].
    body = body.union(inlet_barb())
    # Single inlet passage, drilled along +X from beyond the barb tip into the
    # supply channel. Built along +Z then rotated, same as the barb, so the
    # cut is guaranteed coaxial with the stem.
    passage = (
        cq.Workplane("XY")
        .circle(BORE_R)
        .extrude(STEM_L + root_len * 0.6 + 2.0)
        .rotate((0, 0, 0), (0, 1, 0), 90.0)
        .translate((-STEM_L - 1.0, 0, strain_th - CHAN_H / 2.0))
    )
    body = body.cut(passage)
    body = body.cut(root_bolts())
    return body


def build_finger_pair():
    """Two fingers facing each other across a common root bar — the minimum
    two-jaw soft gripper. Built as one solid: the bar plus two mirrored
    fingers, all fused before any cut, so the result is a single body."""
    # Fingers are offset in +/-Y; the bar must span from one outer edge to the
    # other so it physically overlaps BOTH finger roots (never a floating bar).
    offset_y = finger_w * 0.75 + 3.0
    span = 2.0 * offset_y + finger_w
    bar = (
        cq.Workplane("XY")
        .box(root_len, span, TOTAL_H, centered=(False, True, False))
    )
    a = build_finger().translate((0, offset_y, 0))
    b = build_finger().translate((0, -offset_y, 0))
    body = bar.union(a).union(b)
    # Re-drill the shared root bolts through the bar centreline.
    tool = None
    for x in (root_len * 0.3, root_len * 0.72):
        h = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, 0, -1.0))
            .circle(BOLT_R)
            .extrude(TOTAL_H + 2.0)
        )
        tool = h if tool is None else tool.union(h)
    if tool is not None:
        body = body.cut(tool)
    return body


def build_root_flange():
    """The rigid root on its own: a bolt-through plate with a shallow pocket
    that receives the TPU finger's root for gluing."""
    plate_th = max(4.0, strain_th + 2.0)
    body = (
        cq.Workplane("XY")
        .box(root_len + 8.0, finger_w + 8.0, plate_th, centered=(True, True, False))
    )
    pocket_d = min(plate_th - 1.5, max(1.0, plate_th * 0.5))
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_th - pocket_d))
        .box(root_len, finger_w, pocket_d + 0.2, centered=(True, True, False))
    )
    body = body.cut(pocket)
    orbit_x = (root_len + 8.0) / 2.0 - BOLT_R - 1.6
    orbit_y = (finger_w + 8.0) / 2.0 - BOLT_R - 1.6
    if orbit_x > BOLT_R and orbit_y > BOLT_R:
        tool = None
        for sx in (-1, 1):
            for sy in (-1, 1):
                h = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(sx * orbit_x, sy * orbit_y, -1.0))
                    .circle(BOLT_R)
                    .extrude(plate_th + 2.0)
                )
                tool = h if tool is None else tool.union(h)
        if tool is not None:
            body = body.cut(tool)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "finger_pair":
    result = build_finger_pair()
elif target_part == "root_flange":
    result = build_root_flange()
else:  # "finger"
    result = build_finger()

_ = math
