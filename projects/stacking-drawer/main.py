"""
Stackable Drawer System — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A small modular drawer unit in two parts:
  - "carcass" : the open shell. It has side rails (grooves) the drawer slides in
                on, and a stacking interlock — pegs on top, matching sockets on
                the bottom — so units stack and lock together.
  - "drawer"  : the sliding drawer that fits the carcass with clearance on every
                side, with a front handle / pull.

Interior dimensions describe the DRAWER's usable interior. The carcass and drawer
share those numbers plus the clearance and rail geometry, so the drawer that
prints from this file always slides into the carcass that prints from it.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.

Coordinate convention: the drawer opening faces -Y (the front). Z=0 is the base
of the carcass. Everything is centered in X.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (drawer-interior driven) ──────────────────────────────────────
inner_w   = float(PARAM(lambda: inner_w,   100.0))   # drawer interior X (mm)
inner_d   = float(PARAM(lambda: inner_d,   120.0))   # drawer interior Y depth (mm)
inner_h   = float(PARAM(lambda: inner_h,    45.0))   # drawer interior Z (mm)
wall      = float(PARAM(lambda: wall,        2.0))   # wall thickness (both parts)
clear     = float(PARAM(lambda: clear,       0.4))   # drawer-to-carcass clearance / side
rail       = float(PARAM(lambda: rail,       3.0))   # rail width / depth (mm)
interlock  = float(PARAM(lambda: interlock,  4.0))   # stack peg size (mm, 0 = none)

target_part = str(PARAM(lambda: target_part, "carcass"))  # carcass | drawer

# ── Clamp ────────────────────────────────────────────────────────────────────
wall = max(1.2, min(wall, inner_w / 4.0, inner_h / 3.0))
clear = max(0.15, min(clear, 1.0))
rail = max(1.5, min(rail, inner_h / 3.0, wall * 2.5))
interlock = max(0.0, min(interlock, wall * 3.0))

# ── Derived key dimensions (the shared contract) ─────────────────────────────
# The drawer's OUTER envelope (its own walls around the interior):
drawer_out_w = inner_w + 2.0 * wall
drawer_out_d = inner_d + 2.0 * wall
drawer_out_h = inner_h + wall                # floor = wall (open top)

# The carcass INTERIOR pocket must clear the drawer envelope on each side:
pocket_w = drawer_out_w + 2.0 * clear
pocket_d = drawer_out_d + 2.0 * clear + 1.0  # +1 so the drawer seats fully with a hair of back-slop
pocket_h = drawer_out_h + 2.0 * clear + rail  # headroom for the rails above the drawer

# The carcass OUTER envelope:
carcass_out_w = pocket_w + 2.0 * wall
carcass_out_d = pocket_d + wall               # closed back, open front
carcass_out_h = pocket_h + 2.0 * wall

FRONT_Y = -carcass_out_d / 2.0                # carcass front plane


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


# ── Carcass ──────────────────────────────────────────────────────────────────
def build_carcass():
    # Solid block, hollowed into an open-front pocket.
    body = _box(carcass_out_w, carcass_out_d, carcass_out_h)

    # Interior pocket: open at the front (-Y) and top is capped by wall.
    # Pocket sits on a floor of thickness `wall`, back wall `wall`, side walls `wall`.
    pocket = _box(
        pocket_w, pocket_d + 2.0, pocket_h,
        0.0,
        FRONT_Y + wall + (pocket_d + 2.0) / 2.0 - 1.0,   # push toward back, open the front
        wall,
    )
    body = body.cut(pocket)

    # Rails: two ledges on the side walls that the drawer's side grooves ride on.
    # They protrude into the pocket from each side wall, a little above the floor.
    rail_z = wall + clear + rail            # top of drawer floor region
    for sx in (-1.0, 1.0):
        x = sx * (pocket_w / 2.0 - rail / 2.0)
        ledge = _box(rail, pocket_d, rail, x, FRONT_Y + wall + pocket_d / 2.0, rail_z)
        body = body.union(ledge)

    # Stacking interlock: pegs up top, sockets in the base.
    if interlock > 0.05:
        body = _add_stack_pegs(body, carcass_out_w, carcass_out_d, carcass_out_h)
        body = _cut_stack_sockets(body, carcass_out_w, carcass_out_d)

    return body


def _peg_positions(w, d):
    ox = w / 2.0 - wall - interlock
    oy = d / 2.0 - wall - interlock
    return [(sx * ox, sy * oy) for sx in (-1.0, 1.0) for sy in (-1.0, 1.0)]


def _add_stack_pegs(body, w, d, h):
    for (x, y) in _peg_positions(w, d):
        peg = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, h))
            .box(interlock, interlock, interlock, centered=(True, True, False))
        )
        body = body.union(peg)
    return body


def _cut_stack_sockets(body, w, d):
    # Sockets slightly larger than the pegs so a stacked unit drops on.
    s = interlock + 2.0 * clear
    for (x, y) in _peg_positions(w, d):
        sock = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, -0.01))
            .box(s, s, interlock + clear, centered=(True, True, False))
        )
        body = body.cut(sock)
    return body


# ── Drawer ───────────────────────────────────────────────────────────────────
def build_drawer():
    # Open-top box sized to the DRAWER envelope (fits pocket with `clear`/side).
    body = _box(drawer_out_w, drawer_out_d, drawer_out_h)
    cavity = _box(inner_w, inner_d, inner_h + 1.0, 0.0, 0.0, wall)
    body = body.cut(cavity)

    # Side grooves that ride on the carcass rails: cut a slot into each side wall
    # at the same height as the rails, a touch wider/taller for clearance.
    groove_z = wall + clear + rail - clear
    for sx in (-1.0, 1.0):
        x = sx * (drawer_out_w / 2.0 - wall / 2.0)
        slot = _box(wall + 1.0, drawer_out_d + 2.0, rail + 2.0 * clear, x, 0.0, groove_z)
        body = body.cut(slot)

    # Front face plate + handle. The front is at -Y of the drawer envelope.
    front_y = -drawer_out_d / 2.0
    # A slightly oversized face so it reads as a drawer front and hides the gap.
    face_w = drawer_out_w + 2.0 * clear + 1.0
    face = _box(face_w, wall, drawer_out_h + clear, 0.0, front_y - wall / 2.0, 0.0)
    body = body.union(face)

    # Handle: a horizontal bar standing off the face.
    handle_w = min(face_w * 0.5, inner_w)
    handle = _box(handle_w, wall + 4.0, min(12.0, drawer_out_h * 0.4),
                  0.0, front_y - wall - 2.0, drawer_out_h * 0.45)
    body = body.union(handle)
    try:
        body = body.edges("|Y").edges("<Z").chamfer(min(wall * 0.3, 0.8))
    except Exception:
        pass
    return body


# ── Fit self-check (informational; printed to render log, never fatal) ────────
def _fit_report():
    slack_w = pocket_w - drawer_out_w
    slack_h = pocket_h - drawer_out_h
    print(
        "FIT drawer_out=({:.2f},{:.2f},{:.2f}) pocket=({:.2f},{:.2f},{:.2f}) "
        "slack_w={:.2f} slack_h={:.2f}".format(
            drawer_out_w, drawer_out_d, drawer_out_h,
            pocket_w, pocket_d, pocket_h, slack_w, slack_h,
        )
    )


_fit_report()

# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "drawer":
    result = build_drawer()
else:
    result = build_carcass()
