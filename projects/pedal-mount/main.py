"""
Pedalboard Pedal Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Fixes guitar effects pedals to a pedalboard. Sized by the pedal footprint so the
bracket hugs the pedal exactly. The shared interface is a pedalboard rail slot
(the standard channel/rail found on Pedaltrain-style boards) so parts index off
one rail geometry.

Three parts (dispatched by `target_part`):
  * "rail_mount"    — an L-bracket that captures a pedal edge and bolts to a
                      board rail; `mount` selects how it attaches (rail slot /
                      hook-and-loop plate / riser feet).
  * "riser"         — a wedge riser that lifts a rear pedal to a viewing angle,
                      with the rail slot underneath.
  * "power_bracket" — an under-board cradle that clips a power-supply brick and
                      hangs from the rail.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pedal_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
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
target_part = str(PARAM(lambda: target_part, "rail_mount"))  # rail|riser|power
mount       = str(PARAM(lambda: mount,        "rail"))        # rail|hookloop|riserfeet

pedal_w     = float(PARAM(lambda: pedal_w,     66.0))  # pedal footprint width (mm)
pedal_d     = float(PARAM(lambda: pedal_d,    120.0))  # pedal footprint depth (mm)
grip_h      = float(PARAM(lambda: grip_h,      10.0))  # how far the lip grips over the pedal
wall        = float(PARAM(lambda: wall,         4.0))  # bracket wall thickness (mm)
rail_w      = float(PARAM(lambda: rail_w,      18.0))  # pedalboard rail width (mm)
rail_t      = float(PARAM(lambda: rail_t,       6.0))  # pedalboard rail thickness (mm)
riser_angle = float(PARAM(lambda: riser_angle, 12.0))  # riser tilt angle (deg)
brick_w     = float(PARAM(lambda: brick_w,     60.0))  # power brick width (mm)
brick_h     = float(PARAM(lambda: brick_h,     35.0))  # power brick height (mm)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
pedal_w     = max(30.0, min(pedal_w, 200.0))
pedal_d     = max(40.0, min(pedal_d, 300.0))
grip_h      = max(4.0, min(grip_h, 25.0))
wall        = max(2.5, min(wall, 8.0))
rail_w      = max(8.0, min(rail_w, 40.0))
rail_t      = max(3.0, min(rail_t, 14.0))
riser_angle = max(4.0, min(riser_angle, 30.0))
brick_w     = max(30.0, min(brick_w, 140.0))
brick_h     = max(15.0, min(brick_h, 80.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def rail_slot(length):
    """A rail-capture slot as a subtractive cutter: an open channel `rail_w` wide
    and `rail_t` tall running along +Y for `length`, centred in X, sitting at
    z=0. Cutting this into a base leaves a hook that clips over a board rail."""
    return (
        cq.Workplane("XY")
        .box(rail_w, length, rail_t, centered=(True, False, False))
    )


def rail_hook(length):
    """A positive rail-hook block: a bar with the rail slot cut from its
    underside, so it clips onto a board rail. Returns a solid Workplane whose
    top face is at z = rail_t + wall."""
    total_h = rail_t + wall
    bar = (
        cq.Workplane("XY")
        .box(rail_w + 2.0 * wall, length, total_h, centered=(True, False, False))
    )
    # Cut the rail channel from the bottom (open downward).
    slot = rail_slot(length + 2.0).translate((0, -1.0, -0.01))
    bar = bar.cut(slot)
    return bar, total_h


# ── Part builders ────────────────────────────────────────────────────────────
def build_rail_mount():
    """An L-bracket: a base plate the width of the pedal with an up-turned front
    lip that hooks over the pedal's front edge, attached to the board by the
    method chosen in `mount`."""
    base_d = min(pedal_d * 0.4, 60.0)
    base = (
        cq.Workplane("XY")
        .box(pedal_w + 2.0 * wall, base_d, wall, centered=(True, False, False))
    )
    # Up-turned lip that grips over the pedal front edge.
    lip = (
        cq.Workplane("XY")
        .box(pedal_w + 2.0 * wall, wall, grip_h + wall, centered=(True, False, False))
        .translate((0, base_d - wall, 0))
    )
    body = base.union(lip)

    if mount == "rail":
        # Rail hook under the back of the base.
        hook, hh = rail_hook(base_d * 0.6)
        hook = hook.rotate((0, 0, 0), (0, 0, 1), 90)  # rail runs across X
        hook = hook.translate((0, base_d * 0.2, -rail_t - wall))
        # Post connecting base to hook.
        post = (
            cq.Workplane("XY")
            .box(rail_w + 2.0 * wall, base_d * 0.6, wall + 0.02, centered=(True, True, False))
            .translate((0, base_d * 0.3, -wall))
        )
        body = body.union(post).union(hook)
    elif mount == "hookloop":
        # A flat foot plate for hook-and-loop tape (thicker base, no holes).
        foot = (
            cq.Workplane("XY")
            .box(pedal_w + 2.0 * wall, base_d, wall, centered=(True, False, False))
            .translate((0, 0, -wall))
        )
        body = body.union(foot)
    else:  # riserfeet
        # Two feet lifting the bracket.
        foot_h = 12.0
        for xc in [-(pedal_w * 0.35), pedal_w * 0.35]:
            foot = (
                cq.Workplane("XY")
                .box(wall * 3.0, base_d * 0.5, foot_h, centered=(True, True, False))
                .translate((xc, base_d * 0.3, -foot_h))
            )
            body = body.union(foot)

    # Cable slot through the base so the pedal's cable can pass.
    slot = (
        cq.Workplane("XY")
        .box(pedal_w * 0.4, wall * 3.0, wall + 2.0, centered=(True, True, False))
        .translate((0, base_d * 0.5, -1.0))
    )
    body = body.cut(slot)
    return body


def build_riser():
    """A wedge riser that lifts the back of a pedal to `riser_angle`, with a rail
    hook underneath. Built as a triangular prism (solid, always watertight)."""
    length = min(pedal_d * 0.6, 90.0)
    width = pedal_w + 2.0 * wall
    back_h = max(12.0, length * math.tan(math.radians(riser_angle)))

    # Right-triangle profile in the YZ plane: low at front (y=0), tall at back.
    wedge = (
        cq.Workplane("YZ")
        .polyline([(0, 0), (length, 0), (length, back_h), (0, wall)])
        .close()
        .extrude(width)
        .translate((-width / 2.0, 0, 0))
    )
    # NOTE: the wedge is kept SOLID. An underside hollow (triangular or box pocket) on
    # a sloped-top prism reliably breaches the hypotenuse and leaves an inverted-normal
    # sliver that slices as a disconnected body — a solid wedge is always a single clean
    # watertight solid, and the extra material on a small pedal riser is negligible.

    # Rail hook under the front.
    hook, hh = rail_hook(width * 0.5)
    hook = hook.rotate((0, 0, 0), (0, 0, 1), 90)
    hook = hook.translate((0, length * 0.25, -rail_t - wall))
    post = (
        cq.Workplane("XY")
        .box(rail_w + 2.0 * wall, width * 0.5, wall + 0.02, centered=(True, True, False))
        .translate((0, length * 0.25, -wall))
    )
    body = wedge.union(post).union(hook)
    return body


def build_power_bracket():
    """An under-board cradle that clips a power-supply brick and hangs from a
    rail. A three-sided channel sized to the brick, with a rail hook on top."""
    inner_w = brick_w + 1.0
    inner_h = brick_h + 1.0
    length = min(pedal_d * 0.7, 110.0)

    outer = (
        cq.Workplane("XY")
        .box(inner_w + 2.0 * wall, length, inner_h + wall, centered=(True, False, False))
    )
    # Hollow the brick pocket, open at the bottom (brick slides up in).
    pocket = (
        cq.Workplane("XY")
        .box(inner_w, length + 2.0, inner_h, centered=(True, False, False))
        .translate((0, -1.0, 0))
    )
    body = outer.cut(pocket)
    # Retaining lips returning along the bottom edges so the brick doesn't drop
    # out (the walls already form the sides).
    lip = 3.0
    bottom_lip_l = (
        cq.Workplane("XY")
        .box(lip + wall, length, wall, centered=(False, False, False))
        .translate((-inner_w / 2.0 - wall, 0, 0))
    )
    bottom_lip_r = (
        cq.Workplane("XY")
        .box(lip + wall, length, wall, centered=(False, False, False))
        .translate((inner_w / 2.0 - lip, 0, 0))
    )
    body = body.union(bottom_lip_l).union(bottom_lip_r)

    # Rail hook on top so the whole cradle hangs under the board.
    hook, hh = rail_hook(length * 0.5)
    hook = hook.rotate((0, 0, 0), (0, 0, 1), 90)
    hook = hook.translate((0, length * 0.25, inner_h + wall))
    post = (
        cq.Workplane("XY")
        .box(rail_w + 2.0 * wall, length * 0.5, wall + 0.02, centered=(True, True, False))
        .translate((0, length * 0.25, inner_h + wall - 0.02))
    )
    body = body.union(post).union(hook)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "riser":
    result = build_riser()
elif target_part == "power_bracket":
    result = build_power_bracket()
else:
    result = build_rail_mount()
