"""
Rail Mount / Clamp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Clamps to a round boat/RV/bimini rail so accessories (rod holders, cup holders,
gear) ride on standard tube rails. A two-piece clamp closes around the rail with
bolts; the top face carries the chosen accessory. Sized by the rail diameter so it
fits 1 in / 25 mm and other common tube stock exactly.

Three parts (dispatched via `target_part`):
  * "clamp_base"      — a 2-part split clamp (both halves, printed side by side) that
                        bolts around the rail; the accessory bolts onto its flat top.
  * "rod_holder_mount"— a clamp half fused to an angled fishing-rod tube.
  * "cup_mount"       — a clamp half fused to a drink-holder cup ring.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rail_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(PARAM(lambda: target_part, "clamp_base"))  # clamp_base|rod_holder_mount|cup_mount

rail_dia    = float(PARAM(lambda: rail_dia,   25.0))   # rail outer diameter (mm); 1in ≈ 25.4
wall        = float(PARAM(lambda: wall,        6.0))   # clamp wall thickness around the rail
clamp_len   = float(PARAM(lambda: clamp_len,  40.0))   # clamp length along the rail (mm)
bolt_dia    = float(PARAM(lambda: bolt_dia,    5.0))   # clamp bolt clearance dia (M5 ≈ 5.0)
grip_fit    = float(PARAM(lambda: grip_fit,    0.3))   # bore oversize per side for a snug grip
rod_dia     = float(PARAM(lambda: rod_dia,    35.0))   # rod-holder tube inner diameter (mm)
rod_angle   = float(PARAM(lambda: rod_angle,  20.0))   # rod tube tilt from vertical (deg)
cup_dia     = float(PARAM(lambda: cup_dia,    75.0))   # cup-holder ring inner diameter (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
rail_dia  = max(12.0, min(rail_dia, 60.0))
wall      = max(3.0, min(wall, 14.0))
clamp_len = max(18.0, min(clamp_len, 120.0))
bolt_dia  = max(2.5, min(bolt_dia, 10.0))
grip_fit  = max(0.0, min(grip_fit, 1.2))
rod_dia   = max(12.0, min(rod_dia, 60.0))
rod_angle = max(0.0, min(rod_angle, 45.0))
cup_dia   = max(50.0, min(cup_dia, 110.0))

# Derived clamp block envelope (a rectangular block bored for the rail).
bore_r  = rail_dia / 2.0 + grip_fit
block_w = rail_dia + 2.0 * wall           # width across the rail (X)
block_h = rail_dia + 2.0 * wall           # height (Z)
bolt_x  = block_w / 2.0 - max(bolt_dia, wall * 0.5)   # bolt column offset from center


# ── Clamp half (a bored block split on the rail centre plane) ────────────────
def _clamp_block():
    """A solid clamp block centred on the rail axis (rail runs along Y), base of the
    block spanning Z in [-block_h/2, block_h/2], with a through bore for the rail and
    two bolt holes flanking it."""
    block = (
        cq.Workplane("XY")
        .box(block_w, clamp_len, block_h, centered=(True, True, True))
    )
    # Rail bore along Y.
    bore = (
        cq.Workplane("XZ")
        .circle(bore_r)
        .extrude(clamp_len + 2.0)
        .translate((0, clamp_len / 2.0 + 1.0, 0))
    )
    block = block.cut(bore)
    # Two vertical bolt holes flanking the rail (Z through).
    for sx in (-1.0, 1.0):
        bolt = (
            cq.Workplane("XY")
            .center(sx * bolt_x, 0.0)
            .circle(bolt_dia / 2.0)
            .extrude(block_h + 2.0)
            .translate((0, 0, -block_h / 2.0 - 1.0))
        )
        block = block.cut(bolt)
    return block


def _clamp_half(top):
    """Half of the clamp: the block cut on the rail centre plane (Z=0). `top`=True
    keeps the upper half (accessory side), False keeps the lower half."""
    block = _clamp_block()
    big = block_h + 4.0
    if top:
        keep = cq.Workplane("XY").box(block_w + 4.0, clamp_len + 4.0, big,
                                      centered=(True, True, False))
        keep = keep.translate((0, 0, 0.0))  # keep z >= 0
    else:
        keep = cq.Workplane("XY").box(block_w + 4.0, clamp_len + 4.0, big,
                                      centered=(True, True, False))
        keep = keep.translate((0, 0, -big))  # keep z <= 0
    return block.intersect(keep)


def build_clamp_base():
    """Both clamp halves, laid out side by side on the print bed (a 2-part clamp).
    The lower half is flipped 180° about X so both split faces print face-down."""
    top = _clamp_half(True).translate((0, clamp_len * 0.7, 0))
    bot = _clamp_half(False).rotate((0, 0, 0), (1, 0, 0), 180).translate((0, -clamp_len * 0.7, 0))
    return top.union(bot)


def _accessory_clamp_half():
    """The TOP clamp half re-seated so its flat split face lies on z=0 and the bore
    channel sits just below the accessory boss — the base every accessory grows from."""
    half = _clamp_half(True)  # occupies z in [0, block_h/2] with a bore trough at z≈0
    return half


# ── Accessories ──────────────────────────────────────────────────────────────
def build_rod_holder_mount():
    """A clamp half carrying an angled tube for a fishing rod / flag / antenna."""
    base = _accessory_clamp_half()
    top_z = block_h / 2.0
    tube_len = 90.0
    tube_or = rod_dia / 2.0 + wall
    # Build the tube upright, then tilt it, then drop its foot INTO the base so the
    # union is a volumetric fuse (not a fragile tangent kiss).
    tube = (
        cq.Workplane("XY")
        .circle(tube_or)
        .circle(rod_dia / 2.0)
        .extrude(tube_len)
    )
    tube = tube.rotate((0, 0, 0), (0, 1, 0), rod_angle)
    tube = tube.translate((0, 0, top_z - 6.0))
    # A short solid pedestal fuses tube to block for a clean weld.
    ped = (
        cq.Workplane("XY")
        .circle(tube_or)
        .extrude(8.0)
        .translate((0, 0, top_z - 6.0))
    )
    body = base.union(ped).union(tube)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_cup_mount():
    """A clamp half carrying a drink-holder ring on a short arm."""
    base = _accessory_clamp_half()
    top_z = block_h / 2.0
    ring_or = cup_dia / 2.0 + wall
    ring_h = 55.0
    floor_t = 3.0
    # Cup ring (open cylinder with a thin floor + a drain hole).
    ring = (
        cq.Workplane("XY")
        .circle(ring_or)
        .extrude(ring_h)
    )
    cav = (
        cq.Workplane("XY")
        .circle(cup_dia / 2.0)
        .extrude(ring_h)
        .translate((0, 0, floor_t))
    )
    ring = ring.cut(cav)
    drain = (
        cq.Workplane("XY")
        .circle(min(8.0, cup_dia * 0.15))
        .extrude(floor_t + 2.0)
        .translate((0, 0, -1.0))
    )
    ring = ring.cut(drain)
    # Position the ring beside the clamp and connect with a bridging arm.
    off_x = block_w / 2.0 + ring_or - 4.0
    ring = ring.translate((off_x, 0.0, top_z - 2.0))
    arm = (
        cq.Workplane("XY")
        .box(off_x + ring_or, min(clamp_len, ring_or * 1.4), 8.0, centered=(True, True, False))
        .translate(((off_x) / 2.0, 0.0, top_z - 6.0))
    )
    body = base.union(arm).union(ring)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rod_holder_mount":
    result = build_rod_holder_mount()
elif target_part == "cup_mount":
    result = build_cup_mount()
else:
    result = build_clamp_base()
