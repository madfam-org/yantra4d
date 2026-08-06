"""
Busbar / DIN Bus Support — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Insulated supports and spacers for rectangular copper busbars in panels. The bar
slot lands on standard flat-bar cross-sections (e.g. 20x5, 25x5, 30x10 mm) and the
base seats on a DIN rail (TS35, EN 60715) or bolts flat to the backplate. Pick the
bar size and the support cradles it at the right centerline height.

Modes are dispatched via `target_part`:
  * "bar_support" — an insulated standoff block with a slot sized to the bar
                    cross-section; a screw hole fixes it to the backplate.
  * "bar_clamp"   — a support whose slot is bridged by a screw-down retaining lip
                    on each side so the bar is captured, not just cradled.
  * "spreader"    — a multi-slot comb that carries several parallel busbars on a
                    fixed pitch (phase spacing).

Standards encoded (mm, copper flat-bar cross-sections width x thickness):
  12x2  15x3  20x5  25x5  30x5  30x10   (common panel busbar bars)
  DIN rail TS35 (EN 60715) = 35.0 wide x 7.5 deep top-hat section.

Watertightness: the bar slot is a single box cut from a solid, filleted blank.
Stacked bodies OVERLAP (never tangent). Screw bores open to a face -> no voids.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bar_size`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Busbar flat-bar cross-sections (width x thickness, mm) ────────────────────
_BARS = {
    "12x2":  {"w": 12.0, "t": 2.0},
    "15x3":  {"w": 15.0, "t": 3.0},
    "20x5":  {"w": 20.0, "t": 5.0},
    "25x5":  {"w": 25.0, "t": 5.0},
    "30x5":  {"w": 30.0, "t": 5.0},
    "30x10": {"w": 30.0, "t": 10.0},
}
DIN_RAIL_W = 35.0      # TS35 top-hat rail width (EN 60715)


def bar_spec(name):
    k = str(name).strip().lower().replace(" ", "").replace("×", "x")
    return _BARS.get(k, _BARS["20x5"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "bar_support"))
bar_size    = str(PARAM(lambda: bar_size, "20x5"))    # 12x2..30x10
clearance   = float(PARAM(lambda: clearance, 0.4))    # slot clearance per side (mm)
stand_h     = float(PARAM(lambda: stand_h, 25.0))     # bar centerline height above base (mm)
wall        = float(PARAM(lambda: wall, 4.0))         # insulator wall around the slot (mm)
base_w      = float(PARAM(lambda: base_w, 30.0))      # base footprint width (mm)
screw_dia   = float(PARAM(lambda: screw_dia, 4.5))    # fixing screw clearance Ø (mm)
phases      = int(PARAM(lambda: phases, 3))           # parallel bars (spreader)
phase_pitch = float(PARAM(lambda: phase_pitch, 25.0)) # center distance between bars (mm)

# Clamp to sane ranges.
clearance = max(0.0, min(clearance, 1.2))
stand_h = max(6.0, min(stand_h, 80.0))
wall = max(2.0, min(wall, 10.0))
base_w = max(12.0, min(base_w, 80.0))
screw_dia = max(2.5, min(screw_dia, 8.0))
phases = max(2, min(phases, 5))
phase_pitch = max(12.0, min(phase_pitch, 60.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _bar_slot_dims(spec):
    """Slot opening (width x thickness) sized to the bar + clearance per side.
    Bar stands on-edge in the slot (thickness across, width vertical)."""
    slot_across = spec["t"] + 2.0 * clearance      # thin dimension across the slot
    slot_tall = spec["w"] + 2.0 * clearance        # bar width -> vertical depth of slot
    return slot_across, slot_tall


def _slot_floor_z(slot_tall):
    """Z of the slot floor. The bar centerline sits at `stand_h`, but the floor is
    clamped so at least `wall` of material bridges UNDER the slot connecting the
    two sides — otherwise a short standoff + tall bar severs the block in two."""
    return max(wall, stand_h - slot_tall / 2.0)


def _standoff(block_w, block_d, top_z):
    """A solid standoff block from z=0 to z=top_z, filleted. Base + pillar are one
    box so there's no tangent seam."""
    b = cq.Workplane("XY").box(block_w, block_d, top_z, centered=(True, True, False))
    try:
        b = b.edges("|Z").fillet(min(3.0, block_w * 0.3, block_d * 0.3))
    except Exception:
        pass
    return b


def _screw(body, block_d, top_z, cx=0.0):
    """Vertical fixing screw bore through the block (open both faces)."""
    scr = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, -1.0))
        .circle(screw_dia / 2.0).extrude(top_z + 2.0)
    )
    return body.cut(scr)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_bar_support():
    """Insulated standoff with a slot sized to the bar; a screw fixes it down."""
    spec = bar_spec(bar_size)
    slot_across, slot_tall = _bar_slot_dims(spec)

    block_w = max(base_w, slot_across + 2.0 * wall)
    block_d = max(14.0, slot_across + 2.0 * wall)
    floor_z = _slot_floor_z(slot_tall)
    top_z = floor_z + slot_tall + wall

    body = _standoff(block_w, block_d, top_z)

    # Bar slot: opens from the TOP, floor clamped so a `wall` bridge stays under
    # it. A single box cut (bar sits on-edge).
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, floor_z))
        .box(slot_across, block_d + 2.0, slot_tall + top_z, centered=(True, True, False))
    )
    body = body.cut(slot)

    body = _screw(body, block_d, top_z)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bar_clamp():
    """Captured bar: the slot is bridged at the top by an inward retaining lip on
    each side (the bar is trapped). Built by cutting the slot NOT all the way to
    the top, then cutting a narrower access throat above it."""
    spec = bar_spec(bar_size)
    slot_across, slot_tall = _bar_slot_dims(spec)

    block_w = max(base_w, slot_across + 2.0 * wall)
    block_d = max(14.0, slot_across + 2.0 * wall)
    pocket_floor = _slot_floor_z(slot_tall)
    top_z = pocket_floor + slot_tall + wall

    body = _standoff(block_w, block_d, top_z)

    # Main bar pocket (does NOT reach the top face — lips remain).
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, pocket_floor))
        .box(slot_across, block_d + 2.0, slot_tall, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Access throat above the pocket, narrower than the bar width so lips retain
    # it. Opens to the top face so the pocket is not a sealed void.
    throat_w = max(1.5, slot_across - 2.0 * min(wall * 0.5, slot_across * 0.3))
    throat = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, pocket_floor + slot_tall - 0.5))
        .box(throat_w, block_d + 2.0, top_z - (pocket_floor + slot_tall) + 1.0,
             centered=(True, True, False))
    )
    body = body.cut(throat)

    body = _screw(body, block_d, top_z)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_spreader():
    """Multi-slot comb: several parallel bar slots on `phase_pitch`, one base."""
    spec = bar_spec(bar_size)
    slot_across, slot_tall = _bar_slot_dims(spec)

    span = (phases - 1) * phase_pitch + slot_across + 2.0 * wall
    block_d = max(14.0, slot_across + 2.0 * wall)
    floor_z = _slot_floor_z(slot_tall)
    top_z = floor_z + slot_tall + wall

    body = _standoff(span, block_d, top_z)

    x0 = -(phases - 1) * phase_pitch / 2.0
    for i in range(phases):
        cx = x0 + i * phase_pitch
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0.0, floor_z))
            .box(slot_across, block_d + 2.0, slot_tall + top_z, centered=(True, True, False))
        )
        body = body.cut(slot)

    # Fixing screws near both ends.
    for cx in (x0 - 0.0, x0 + (phases - 1) * phase_pitch):
        body = _screw(body, block_d, top_z, cx=cx)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "bar_support": build_bar_support,
    "bar_clamp": build_bar_clamp,
    "spreader": build_spreader,
}

result = _dispatch.get(target_part, build_bar_support)()
