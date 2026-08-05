"""
Tube Squeezer Key — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A winding key that squeezes the last of a toothpaste / cosmetic / paint tube. You
feed the flattened (crimped) end of the tube through a lengthwise slot in a bar,
then turn the bar so the tube winds around it, driving the contents forward. A
turn handle at one end lets you crank it: either winged tabs to grip with your
fingers, or a cross-hole to pass a rod / pencil through for leverage.

Modes (dispatched via `target_part`):
  * "squeezer"        — the standard slotted winding key.
  * "roller_squeezer" — a wider bar (rounded into a roller-like barrel) that
                        winds wide tubes flat in fewer turns. Same slot interface.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `tube_width`).
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
tube_width  = float(PARAM(lambda: tube_width,   35.0))   # tube crimp width -> slot length (mm)
bar_thick   = float(PARAM(lambda: bar_thick,     6.0))   # bar thickness (mm)
bar_height  = float(PARAM(lambda: bar_height,   14.0))   # bar height / how far the tube winds (mm)
slot_width  = float(PARAM(lambda: slot_width,    1.6))   # slot width for the crimped end (mm)
wall_margin = float(PARAM(lambda: wall_margin,   6.0))   # material each side of the slot (mm)
handle      = bool( PARAM(lambda: handle,       True))   # True = winged tabs, False = rod hole
rod_dia     = float(PARAM(lambda: rod_dia,       6.5))   # cross-hole diameter for a rod (mm)

target_part = str(  PARAM(lambda: target_part, "squeezer"))  # "squeezer" | "roller_squeezer"


# ── Derived / clamped geometry ───────────────────────────────────────────────
tube_width = max(10.0, tube_width)
bar_thick = max(3.0, bar_thick)
bar_height = max(6.0, bar_height)
# Slot must fit inside the bar thickness with wall on both sides.
slot_width = max(0.8, min(slot_width, bar_thick - 2.0))
wall_margin = max(3.0, wall_margin)

is_roller = (target_part == "roller_squeezer")
if is_roller:
    bar_thick = max(bar_thick, 9.0)        # a chunkier barrel
    bar_height = max(bar_height, 18.0)

# Bar footprint: length runs along X (the slot length + end margins), the bar is
# `bar_thick` deep in Y and `bar_height` tall in Z.
slot_len = tube_width + 2.0                 # a little longer than the crimp
bar_len = slot_len + 2.0 * wall_margin
handle_len = 22.0 if handle else 16.0       # extra length at the +X end for the grip


# ── Helpers ──────────────────────────────────────────────────────────────────
def base_bar(length):
    """The winding bar: a block centered in Y, base at z=0, starting at x=0."""
    bar = cq.Workplane("XY").box(length, bar_thick, bar_height,
                                 centered=(False, True, False))
    if is_roller:
        # Round the two vertical long edges into a barrel-ish roller.
        try:
            bar = bar.edges("|Z and (>Y or <Y)").fillet(min(bar_thick * 0.45, 3.0))
        except Exception:
            pass
    else:
        # Soften the long top/bottom edges of the winding face for the tube.
        try:
            bar = bar.edges("|X").fillet(min(bar_thick * 0.25, 1.2))
        except Exception:
            pass
    return bar


def cut_slot(body):
    """Cut the lengthwise through-slot (a rounded rectangle) that the crimped
    tube end feeds through. The slot runs along X, centered in the bar, and goes
    all the way through the bar in Z so the tube can be threaded."""
    x0 = wall_margin
    # Rounded-rectangle slot: a stadium made of a box + two end fillets.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x0 + slot_len / 2.0, 0.0, -1.0))
        .box(slot_len, slot_width, bar_height + 2.0, centered=(True, True, False))
    )
    try:
        slot = slot.edges("|Z").fillet(slot_width / 2.0 - 0.05)
    except Exception:
        pass
    return body.cut(slot)


def add_winged_handle(body):
    """Two finger wings at the +X end to grip and turn the bar."""
    x_end = bar_len
    wing_out = max(bar_thick * 1.6, 12.0)  # how far the wings stick out in Y
    for sign in (1.0, -1.0):
        wing = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x_end - handle_len * 0.5,
                                          sign * (bar_thick / 2.0 + wing_out / 2.0 - 0.5),
                                          0.0))
            .box(handle_len, wing_out, bar_height, centered=(True, True, False))
        )
        try:
            wing = wing.edges("|Z and >X").fillet(min(wing_out * 0.4, 5.0))
        except Exception:
            pass
        body = body.union(wing)
    return body


def add_rod_hole(body):
    """A cross-hole through the +X end for a rod / pencil to lever the key."""
    d = max(2.0, min(rod_dia, bar_height - 3.0, bar_thick + 6.0))
    x = bar_len - handle_len * 0.5
    z = bar_height / 2.0
    hole = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(x, z, 0.0))
        .circle(d / 2.0)
        .extrude(bar_thick * 2.0 + 8.0)
        .translate((0, bar_thick + 4.0, 0))  # span fully through Y
    )
    return body.cut(hole)


# ── Assemble ─────────────────────────────────────────────────────────────────
def build():
    total_len = bar_len + handle_len
    body = base_bar(total_len)
    body = cut_slot(body)
    if handle:
        body = add_winged_handle(body)
    else:
        body = add_rod_hole(body)
    return body


result = build()
