"""
Bellows Suction Cup — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The vacuum end-effector primitive. A bellows suction cup: a flared sealing lip
over a short convoluted (accordion) neck. The convolutions let the cup collapse
axially when vacuum is drawn — so it lifts a part off a surface without the
whole tool moving down, and tolerates a part that is not square to the tool.

Cup diameter follows the common pick-and-place series (20 / 30 / 40 mm), and
the vacuum port is the shared barb series from `pneumatic-barb-port` — a cup
generated at one `tube_id` threads onto a `vacuum-manifold-block` port
generated at the same `tube_id`.

Modes:
  - cup          : flared lip + convoluted neck + barb vacuum port, one piece.
  - cup_flat     : the same lip on a plain straight neck (no bellows) — stiffer,
                   for flat rigid parts where compliance is not wanted.
  - cup_mount    : the rigid mount only — a bolt-through plate with a socket
                   that the TPU cup's neck presses into.

Watertight strategy: the cup body is ONE revolved solid built from a single
closed 2-D profile (outer face up, inner face back down offset by the wall) —
never a shelled surface. The barb ridges are lofted collars unioned onto the
stem, and the vacuum passage is a single through-bore cut LAST, from the barb
tip out through the cup mouth. Every derived radius is clamped so the passage
can never reach the outer wall at any parameter extreme.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Print the cup in soft TPU (Shore 85A or softer) for the lip to seal.
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
target_part = str(PARAM(lambda: target_part, "cup"))
# "cup" | "cup_flat" | "cup_mount"

cup_dia      = float(PARAM(lambda: cup_dia,     30.0))  # sealing-lip outer diameter
lip_th       = float(PARAM(lambda: lip_th,       1.2))  # sealing lip thickness
lip_h        = float(PARAM(lambda: lip_h,        7.0))  # lip flare height
neck_dia     = float(PARAM(lambda: neck_dia,    13.0))  # convoluted neck diameter
convolutions = int(PARAM(lambda: convolutions,   2))    # accordion folds in the neck
conv_pitch   = float(PARAM(lambda: conv_pitch,   5.0))  # axial height per fold
conv_depth   = float(PARAM(lambda: conv_depth,   3.0))  # radial amplitude of a fold
wall         = float(PARAM(lambda: wall,         1.4))  # neck membrane thickness
tube_id      = float(PARAM(lambda: tube_id,      4.0))  # vacuum tubing inner dia
bore         = float(PARAM(lambda: bore,         2.6))  # vacuum passage diameter
bolt_dia     = float(PARAM(lambda: bolt_dia,     3.4))  # M3 clearance (mount mode)

# ── Clamps ───────────────────────────────────────────────────────────────────
cup_dia      = max(8.0,  min(cup_dia, 120.0))
lip_th       = max(0.6,  min(lip_th, 5.0))
lip_h        = max(2.0,  min(lip_h, 30.0))
neck_dia     = max(5.0,  min(neck_dia, 80.0))
convolutions = max(0,    min(convolutions, 8))
conv_pitch   = max(2.5,  min(conv_pitch, 15.0))
conv_depth   = max(0.5,  min(conv_depth, 12.0))
wall         = max(0.6,  min(wall, 4.0))
tube_id      = max(1.5,  min(tube_id, 12.0))
bore         = max(0.8,  min(bore, 10.0))
bolt_dia     = max(1.5,  min(bolt_dia, 8.0))

# ── Derived, clamped ─────────────────────────────────────────────────────────
R_CUP = cup_dia / 2.0
# Neck must always be meaningfully narrower than the cup mouth.
R_NECK = min(neck_dia / 2.0, R_CUP - lip_th - 1.2)
R_NECK = max(2.0, R_NECK)
# Fold amplitude must not eat the neck wall.
AMP = min(conv_depth, R_NECK - wall - 0.8)
AMP = max(0.0, AMP)
R_CREST = R_NECK + AMP
# Lumen inside the neck.
R_LUMEN = max(0.6, R_NECK - wall)
NECK_H = conv_pitch * max(convolutions, 1) if convolutions > 0 else conv_pitch
HP = conv_pitch / 2.0

# Barb port (shared series).
STEM_R = max(tube_id / 2.0, bore / 2.0 + 0.8)
STEM_R = max(STEM_R, R_LUMEN * 0.0 + STEM_R)   # keep explicit
BORE_R = min(bore / 2.0, STEM_R - 0.6, R_LUMEN - 0.3)
BORE_R = max(0.35, BORE_R)
BARB_R = STEM_R + 0.7
STEM_L = 10.0
# The port boss caps the neck; it must be at least as wide as the barb crest.
BOSS_R = max(R_NECK, BARB_R + 0.8)
BOSS_H = max(2.0, wall * 1.6)


# ── Helpers ──────────────────────────────────────────────────────────────────
def lip_profile(z0):
    """Closed 2-D profile of the flared sealing lip, revolved into a solid.

    Outer face runs from the neck radius at z0+lip_h out to the cup radius at
    z0 (the mouth, which faces DOWN, -Z). The inner face returns offset by
    `lip_th`. A conical annulus — always one closed loop."""
    r_top_o = R_NECK
    r_bot_o = R_CUP
    r_bot_i = max(0.5, R_CUP - lip_th)
    r_top_i = max(0.4, R_LUMEN)
    return [
        (r_top_o, z0 + lip_h),
        (r_bot_o, z0),
        (r_bot_i, z0),
        (r_top_i, z0 + lip_h),
    ]


def neck_profile(z0):
    """Closed 2-D profile of the convoluted (or straight) neck."""
    if convolutions <= 0 or AMP < 0.15:
        # Straight tube.
        return [
            (R_NECK, z0),
            (R_NECK, z0 + NECK_H),
            (R_LUMEN, z0 + NECK_H),
            (R_LUMEN, z0),
        ]
    out = [(R_NECK, z0)]
    z = z0
    for _ in range(convolutions):
        out.append((R_CREST, z + HP))
        z += conv_pitch
        out.append((R_NECK, z))
    inn = [(max(0.4, R_NECK - wall), z)]
    for _ in range(convolutions):
        inn.append((max(0.4, R_CREST - wall), z - HP))
        z -= conv_pitch
        inn.append((max(0.4, R_NECK - wall), z))
    return out + inn


def revolve(pts):
    return cq.Workplane("XZ").polyline(pts).close().revolve(360.0, (0, 0, 0), (0, 1, 0))


def barb_stem(z0):
    """Barb port pointing +Z from z0, ridges widening upward so tubing locks."""
    body = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(STEM_R)
        .extrude(STEM_L)
    )
    for i in range(2):
        zb = z0 + 1.2 + i * 3.4
        zb = min(zb, z0 + STEM_L - 2.4)
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, zb))
            .circle(BARB_R)
            .workplane(offset=2.0)
            .circle(STEM_R)
            .loft(ruled=True)
        )
        body = body.union(ridge)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_cup(bellows=True):
    """Lip at Z=0 facing -Z (the part it picks), neck rising, barb on top."""
    body = revolve(lip_profile(0.0))
    neck = revolve(neck_profile(lip_h)) if bellows else revolve(
        [
            (R_NECK, lip_h),
            (R_NECK, lip_h + NECK_H),
            (R_LUMEN, lip_h + NECK_H),
            (R_LUMEN, lip_h),
        ]
    )
    body = body.union(neck)
    # Solid boss capping the neck, then the barb on top of it.
    z_boss = lip_h + NECK_H
    boss = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_boss))
        .circle(BOSS_R)
        .extrude(BOSS_H)
    )
    body = body.union(boss).union(barb_stem(z_boss + BOSS_H))
    # ONE vacuum passage: from above the barb tip all the way out the mouth.
    top_z = z_boss + BOSS_H + STEM_L
    passage = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(BORE_R)
        .extrude(top_z + 2.0)
    )
    body = body.cut(passage)
    return body


def build_cup_mount():
    """Rigid bolt-through plate with a socket that receives the cup neck."""
    plate_r = max(R_CREST + bolt_dia + 3.0, R_CUP * 0.6)
    plate_th = max(4.0, wall * 3.0)
    body = cq.Workplane("XY").circle(plate_r).extrude(plate_th)
    # Socket for the neck (press fit, 0.25 mm per side).
    sock_r = min(R_NECK + 0.25, plate_r - 2.0)
    sock_d = min(plate_th - 1.5, max(1.0, plate_th * 0.6))
    socket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, plate_th - sock_d))
        .circle(sock_r)
        .extrude(sock_d + 0.2)
    )
    body = body.cut(socket)
    # Vacuum passage through the plate.
    body = body.cut(
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(BORE_R)
        .extrude(plate_th + 2.0)
    )
    # Bolt holes on a ring outside the socket.
    bolt_r = min(bolt_dia / 2.0, (plate_r - sock_r) / 2.0 - 0.6)
    bolt_r = max(0.5, bolt_r)
    orbit = (sock_r + plate_r) / 2.0
    tool = None
    for k in range(4):
        ang = math.pi / 4.0 + k * math.pi / 2.0
        h = (
            cq.Workplane("XY")
            .transformed(
                offset=cq.Vector(orbit * math.cos(ang), orbit * math.sin(ang), -1.0)
            )
            .circle(bolt_r)
            .extrude(plate_th + 2.0)
        )
        tool = h if tool is None else tool.union(h)
    if tool is not None:
        body = body.cut(tool)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cup_flat":
    result = build_cup(bellows=False)
elif target_part == "cup_mount":
    result = build_cup_mount()
else:  # "cup"
    result = build_cup(bellows=True)
