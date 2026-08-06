"""
Pi HAT Case — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A case sized around a Raspberry Pi plus its HAT / screen stack. The base carries
the Pi on standoffs at the official 58 x 49 mm hole pattern; a raised lid clears
a HAT sitting on the GPIO header; a bezel frames a screen mounted on top. Stack
height sets how much room the lid leaves for the boards above the Pi.

Modes are dispatched via `target_part`:
  * "base"        — walled base with the Pi standoffs + a cable slot.
  * "hat_lid"     — a raised lid that clears a HAT above the Pi.
  * "screen_bezel"— a top frame with a rectangular screen window.

Standoff pattern is the Raspberry Pi HAT / Model B mounting spec (58 x 49 mm,
2.75 mm holes).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `stack`).
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


# ── Raspberry Pi mounting spec (HAT / Model B) ───────────────────────────────
PI_HOLE_DX = 58.0    # hole spacing in X
PI_HOLE_DY = 49.0    # hole spacing in Y
PI_BOARD_W = 85.0    # Pi board outline X (Model B)
PI_BOARD_D = 56.0    # Pi board outline Y
PI_HOLE_D = 2.75     # mounting-hole diameter on the board


# ── Parameters ───────────────────────────────────────────────────────────────
stack       = float(PARAM(lambda: stack,      16.0))    # clearance above the Pi for HAT/screen
wall        = float(PARAM(lambda: wall,        2.4))    # case wall thickness
floor       = float(PARAM(lambda: floor,       2.4))    # base floor / lid-plate thickness
standoff_h  = float(PARAM(lambda: standoff_h,  4.0))    # Pi standoff height above the floor
boss_d      = float(PARAM(lambda: boss_d,      6.0))    # standoff outer diameter
corner_r    = float(PARAM(lambda: corner_r,    3.0))    # outer corner radius
screen_w    = float(PARAM(lambda: screen_w,   56.0))    # screen window width (bezel)
screen_h    = float(PARAM(lambda: screen_h,   35.0))    # screen window height (bezel)

target_part = str(PARAM(lambda: target_part, "base"))

# ── Derived ──────────────────────────────────────────────────────────────────
stack = max(4.0, min(stack, 60.0))
wall = max(1.6, min(wall, 5.0))
floor = max(1.6, min(floor, 6.0))
standoff_h = max(2.0, min(standoff_h, 20.0))
boss_d = max(PI_HOLE_D + 2.5, min(boss_d, 10.0))
corner_r = max(0.0, min(corner_r, 8.0))

inner_w = PI_BOARD_W + 2.0            # a little room around the board
inner_d = PI_BOARD_D + 2.0
outer_w = inner_w + 2.0 * wall
outer_d = inner_d + 2.0 * wall
base_h = floor + standoff_h + 4.0     # base wall height (holds the Pi + a little)

peg_bore = max(1.6, PI_HOLE_D - 0.3)  # self-tapping bore for the Pi screw


# ── Helpers ──────────────────────────────────────────────────────────────────
def _hole_points():
    hx, hy = PI_HOLE_DX / 2.0, PI_HOLE_DY / 2.0
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]


def _rounded_block(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _shell(h):
    """A walled shell (open top) of outer_w x outer_d x h with a cavity."""
    body = _rounded_block(outer_w, outer_d, h, corner_r)
    cavity = (
        cq.Workplane("XY").workplane(offset=floor)
        .box(inner_w, inner_d, h, centered=(True, True, False))
    )
    ir = max(0.0, corner_r - wall)
    if ir > 0.05:
        try:
            cavity = cavity.edges("|Z").fillet(ir)
        except Exception:
            pass
    return body.cut(cavity)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_base():
    body = _shell(base_h)
    # Pi standoffs (grouped extrude + grouped bore).
    pts = _hole_points()
    pillars = (
        cq.Workplane("XY").workplane(offset=floor)
        .pushPoints(pts).circle(boss_d / 2.0).extrude(standoff_h)
    )
    body = body.union(pillars)
    bores = (
        cq.Workplane("XY").workplane(offset=floor - 0.5)
        .pushPoints(pts).circle(peg_bore / 2.0).extrude(standoff_h + 1.0)
    )
    body = body.cut(bores)

    # A cable/GPIO slot in one long wall (the -Y face) for a ribbon out.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -outer_d / 2.0, floor + standoff_h))
        .box(40.0, wall + 4.0, 8.0, centered=(True, True, False))
    )
    body = body.cut(slot)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_hat_lid():
    """A raised lid: a top plate on a skirt that nests into the base walls, tall
    enough (`stack`) to clear a HAT sitting on the GPIO header. Vent slots on top
    keep the stack cool."""
    skirt_w = inner_w - 0.5
    skirt_d = inner_d - 0.5
    lid_h = stack + floor

    # Raised box, open at the bottom.
    body = _rounded_block(outer_w, outer_d, lid_h, corner_r)
    cavity = (
        cq.Workplane("XY").workplane(offset=-0.5)
        .box(skirt_w, skirt_d, lid_h - floor + 0.5, centered=(True, True, False))
    )
    body = body.cut(cavity)
    # trim the outer skirt down to a nesting skirt on the lower portion only —
    # keep it simple: the box already nests over the base rim.

    # Vent slots on the top face.
    n = 6
    xs = [-outer_w / 2.0 + outer_w * (i + 1) / (n + 1) for i in range(n)]
    vents = (
        cq.Workplane("XY").workplane(offset=lid_h + 0.5)
        .pushPoints([(x, 0.0) for x in xs])
        .box(2.5, inner_d * 0.6, floor + 1.0, centered=(True, True, True))
    )
    body = body.cut(vents)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_screen_bezel():
    """A top frame carrying a rectangular screen window, on a short skirt that
    nests into the base. The window is sized by `screen_w` x `screen_h`."""
    lid_h = max(6.0, stack * 0.5) + floor
    body = _rounded_block(outer_w, outer_d, lid_h, corner_r)
    cavity = (
        cq.Workplane("XY").workplane(offset=-0.5)
        .box(inner_w - 0.5, inner_d - 0.5, lid_h - floor + 0.5, centered=(True, True, False))
    )
    body = body.cut(cavity)

    sw = max(10.0, min(screen_w, inner_w - 4.0))
    sh = max(8.0, min(screen_h, inner_d - 4.0))
    window = (
        cq.Workplane("XY").workplane(offset=lid_h + 0.5)
        .box(sw, sh, floor + 1.0, centered=(True, True, True))
    )
    body = body.cut(window)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "base": build_base,
    "hat_lid": build_hat_lid,
    "screen_bezel": build_screen_bezel,
}

result = _dispatch.get(target_part, build_base)()
