"""
Padlock Shackle Guard / Hasp — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The hardware that turns a padlock into a door/lid latch: a hinged hasp strap, the
staple loop its slot drops over, and a shrouded guard that shields the padlock
shackle from bolt-cutters. Modelled on the 4 in (100 mm) safety-pattern hasp family.

Three distinct parts:
  - safety_hasp  : the swinging hasp strap — a flat arm with a hinge barrel at one
                   end and a staple slot at the other, plus countersunk screw holes.
                   (Safety pattern: the closed strap covers its own fixing screws.)
  - staple       : the staple loop the hasp slot drops over, standing on a bolt-down
                   base with two screw holes; the padlock shackle passes through it.
  - shackle_guard: a U-shaped shroud that walls off three sides of the padlock so
                   bolt-cutters cannot reach the shackle, with a shackle-Ø slot and
                   a four-screw base.

Dimensioning (4 in / 100 mm safety-pattern hasp family; internal reference):
  - hasp strap length      ~ 100 mm, width ~ 38 mm, ~4 mm plate
  - fixing screws          ~ 4 mm shank (No.8/M4), heads countersunk
  - staple loop bar        ~ 8 mm, inner opening sized to the shackle Ø
  - shackle Ø              ~ 8-10 mm (typical 40-50 mm padlock shackle)

Watertight strategy:
  Straps and bases are filleted flat blanks; the hinge barrel and staple loop are
  built from overlapping solids UNIONED into shared material (never tangent). Every
  hole (screw bores, hinge pin bore, staple slot, shackle slot) is a through- or
  open-to-a-face cut that vents to outside — no sealed cavity. The staple loop is a
  torus-free construction: a bar bridged over the base with an obround window cut
  through it (the window opens to two faces). Fillets are applied to clean blanks
  BEFORE cutting features.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>).
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


# ── Parameters (4 in / 100 mm safety-pattern hasp family) ────────────────────
target_part = str(PARAM(lambda: target_part, "safety_hasp"))
# "safety_hasp" | "staple" | "shackle_guard"

strap_len = float(PARAM(lambda: strap_len, 100.0))  # hasp strap length (mm)
strap_w = float(PARAM(lambda: strap_w, 38.0))       # strap / base width (mm)
plate_t = float(PARAM(lambda: plate_t, 4.0))        # plate thickness (mm)

screw_d = float(PARAM(lambda: screw_d, 4.2))        # fixing-screw shank Ø (No.8/M4)
screw_head_d = float(PARAM(lambda: screw_head_d, 8.4))  # countersink head Ø
hinge_d = float(PARAM(lambda: hinge_d, 8.0))        # hinge barrel outer Ø
pin_d = float(PARAM(lambda: pin_d, 3.2))            # hinge pin bore Ø
shackle_d = float(PARAM(lambda: shackle_d, 9.0))    # padlock shackle Ø (opening)
staple_bar = float(PARAM(lambda: staple_bar, 8.0))  # staple loop bar thickness

# Clamp to sane ranges so extreme UI values never crash the kernel.
strap_len = max(50.0, min(strap_len, 200.0))
strap_w = max(20.0, min(strap_w, 80.0))
plate_t = max(2.0, min(plate_t, 10.0))
screw_d = max(2.5, min(screw_d, 8.0))
screw_head_d = max(screw_d + 2.0, min(screw_head_d, strap_w / 2.0 - 1.0))
hinge_d = max(plate_t + 2.0, min(hinge_d, strap_w / 2.0))
pin_d = max(1.5, min(pin_d, hinge_d - 2.0))
shackle_d = max(5.0, min(shackle_d, strap_w - 8.0))
staple_bar = max(4.0, min(staple_bar, 16.0))


# ── Primitives ───────────────────────────────────────────────────────────────
def _blank(w, length, t, corner=3.0):
    """A filleted flat plate, base at z=0, centred on X, spanning 0..length in Y."""
    p = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, length / 2.0, 0))
        .box(w, length, t, centered=(True, True, False))
    )
    try:
        p = p.edges("|Z").fillet(min(corner, w / 2.0 - 0.5))
    except Exception:
        pass
    return p


def _screw(cx, cy, t):
    """A counterbored screw cut (shank through + top-face countersink). Vents out."""
    shank = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, -0.5))
        .circle(screw_d / 2.0)
        .extrude(t + 1.0)
    )
    csk_depth = min(t * 0.6, (screw_head_d - screw_d) / 2.0 + 0.4)
    csk = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, t - csk_depth))
        .circle(screw_d / 2.0)
        .workplane(offset=csk_depth + 0.01)
        .circle(screw_head_d / 2.0)
        .loft(combine=True)
    )
    return shank, csk


# ── Part builders ────────────────────────────────────────────────────────────
def build_safety_hasp():
    """The swinging hasp strap: a flat arm with a hinge barrel across the Y=0 end
    and a staple slot near the far end, plus two countersunk fixing screws behind
    the hinge (covered by the leaf when closed)."""
    arm = _blank(strap_w, strap_len, plate_t)

    # Hinge barrel across X at the near (Y≈0) end. A cylinder lying along X, unioned
    # so it overlaps the strap end (solid weld). Its axis is at z = plate_t/2.
    barrel = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, plate_t / 2.0, -strap_w / 2.0))
        .circle(hinge_d / 2.0)
        .extrude(strap_w)
    )
    # Trim barrel to the strap width footprint and seat it at the Y=0 edge.
    barrel = barrel.translate((0, 0, 0))
    body = arm.union(barrel)

    # Hinge pin bore along X through the barrel (vents both X ends).
    pin = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, plate_t / 2.0, -strap_w / 2.0 - 1.0))
        .circle(pin_d / 2.0)
        .extrude(strap_w + 2.0)
    )
    body = body.cut(pin)

    # Staple slot near the far end: an obround window cut through the plate so the
    # strap drops over a staple. Opens both faces → vents.
    slot_cy = strap_len - strap_w * 0.55
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, slot_cy, -0.5))
        .slot2D(shackle_d + staple_bar + 6.0, staple_bar + 2.0, angle=0)
        .extrude(plate_t + 1.0)
    )
    body = body.cut(slot)

    # Two fixing screws just past the hinge barrel (safety pattern: hidden when the
    # leaf lies closed over them).
    scy = hinge_d + screw_head_d / 2.0 + 2.0
    sx = strap_w / 2.0 - (screw_head_d / 2.0 + 2.0)
    for cx in (sx, -sx):
        for c in _screw(cx, scy, plate_t):
            body = body.cut(c)
    return body


def build_staple():
    """The staple loop the hasp slot drops over: a raised loop bar spanning a
    bolt-down base, with an obround window (the shackle passes through it) and two
    fixing screws in the base."""
    base_len = strap_w + 10.0
    base = _blank(strap_w, base_len, plate_t)

    # Loop bar: a fat bar arching over the base along X, standing to a height that
    # clears the shackle. Built as a box unioned onto the base (overlap → weld),
    # then a window cut through it.
    loop_h = plate_t + shackle_d + staple_bar
    loop_cy = base_len * 0.5
    loop = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, loop_cy, 0))
        .box(strap_w - 6.0, staple_bar + 4.0, loop_h, centered=(True, True, False))
    )
    try:
        loop = loop.edges("|Y").fillet(min(staple_bar / 2.0, (strap_w - 6.0) / 2.0 - 0.5))
    except Exception:
        pass
    body = base.union(loop)

    # Window through the loop (along Y) so a shackle/hasp passes through. The window
    # is an obround opening to the front and back faces of the loop → vents.
    window = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, plate_t + shackle_d / 2.0 + 1.0, -loop_cy - staple_bar))
        .slot2D(shackle_d + 2.0, shackle_d, angle=0)
        .extrude(staple_bar * 4.0)
    )
    body = body.cut(window)

    # Two fixing screws in the base, fore and aft of the loop.
    sx = 0.0
    for cy in (loop_cy - (staple_bar + screw_head_d / 2.0 + 3.0),
               loop_cy + (staple_bar + screw_head_d / 2.0 + 3.0)):
        for c in _screw(sx, cy, plate_t):
            body = body.cut(c)
    return body


def build_shackle_guard():
    """A U-shaped shroud that walls three sides of the padlock so bolt-cutters
    cannot reach the shackle. A thick base with three raised walls and a shackle-Ø
    slot in the front wall, on a four-screw footprint."""
    base_len = strap_len * 0.7
    base = _blank(strap_w, base_len, plate_t + 2.0)

    wall_h = shackle_d * 2.2 + plate_t
    wall_t = max(4.0, plate_t)

    # Back wall (far Y).
    back = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, base_len - wall_t / 2.0, 0))
        .box(strap_w, wall_t, wall_h, centered=(True, True, False))
    )
    # Two side walls.
    side_off = strap_w / 2.0 - wall_t / 2.0
    sides = []
    for cx in (side_off, -side_off):
        sides.append(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, base_len / 2.0, 0))
            .box(wall_t, base_len, wall_h, centered=(True, True, False))
        )
    body = base.union(back).union(sides[0]).union(sides[1])

    # Front lip wall (partial) with a shackle slot the padlock shackle exits
    # through. The slot opens upward (to the top of the lip) → vents.
    lip_h = wall_h * 0.55
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, wall_t / 2.0, 0))
        .box(strap_w, wall_t, lip_h, centered=(True, True, False))
    )
    body = body.union(lip)

    slot = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, lip_h + shackle_d, -wall_t - 1.0))
        .slot2D(shackle_d, shackle_d * 1.4, angle=90)
        .extrude(wall_t + 2.0)
    )
    body = body.cut(slot)

    # Four corner fixing screws in the base floor (inside the shroud).
    ox = strap_w / 2.0 - (wall_t + screw_head_d / 2.0 + 1.5)
    oy0 = wall_t + screw_head_d / 2.0 + 3.0
    oy1 = base_len - wall_t - (screw_head_d / 2.0 + 3.0)
    for cx in (ox, -ox):
        for cy in (oy0, oy1):
            for c in _screw(cx, cy, plate_t + 2.0):
                body = body.cut(c)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "staple":
    result = build_staple()
elif target_part == "shackle_guard":
    result = build_shackle_guard()
else:
    result = build_safety_hasp()
