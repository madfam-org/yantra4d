"""
Pen / Stylus Holder & Grip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A desk pen station sized around a real writing-instrument barrel diameter.
Three distinct forms are dispatched by `target_part`:

  * "pen_cup"       — an upright round cup that holds a fistful of pens/pencils,
                      with an optional single internal divider so ink and pencils
                      keep to their own side. A five-wall shell, open at the top
                      (never a sealed cavity), fillet-rounded base.
  * "pen_block"     — a rounded desk block with an evenly spaced array of blind
                      bores drilled from the top, each sized to `pen_dia` +
                      clearance. Front row optionally raked forward so pens
                      present at an angle. Bores open upward: no trapped voids.
  * "grip_enlarger" — an ergonomic sleeve that slides over a thin pen barrel to
                      fatten the grip (an assistive aid for reduced hand
                      strength). A through-tube with unioned finger ridges; open
                      at both ends, so it stays a single watertight solid.

Reference dimensions (why the defaults are what they are):
  - A common ballpoint / rollerball barrel is ~8 mm; a chunky gel or marker-style
    pen is ~10-11 mm. `pen_dia` defaults to 9 mm and clearance adds a slip fit.
  - A standard #2 pencil across the flats is ~7 mm (hex ~7.5 mm point-to-point).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pen_dia`).
  - Read them via PARAM(lambda: <name>, <default>) — never globals()/eval/getattr
    (not in the sandbox's allowed builtins).
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
pen_dia    = float(PARAM(lambda: pen_dia,     9.0))   # writing-instrument barrel Ø (mm)
clearance  = float(PARAM(lambda: clearance,   1.2))   # slip-fit gap added to each bore (mm)
wall       = float(PARAM(lambda: wall,        3.0))   # wall / floor thickness (mm)
height     = float(PARAM(lambda: height,     95.0))   # overall height of cup / block (mm)
cup_dia    = float(PARAM(lambda: cup_dia,    72.0))   # outer Ø of the pen cup (mm)
divider    = int(  PARAM(lambda: divider,       1))   # 1 = add a divider wall in the cup, 0 = none
cols       = int(  PARAM(lambda: cols,          4))   # bore columns (pen_block)
rows       = int(  PARAM(lambda: rows,          2))   # bore rows (pen_block)
rake_deg   = float(PARAM(lambda: rake_deg,   12.0))   # front-row rake angle (pen_block)
grip_len   = float(PARAM(lambda: grip_len,   85.0))   # sleeve length (grip_enlarger)
grip_dia   = float(PARAM(lambda: grip_dia,   22.0))   # sleeve outer grip Ø (grip_enlarger)

target_part = str(PARAM(lambda: target_part, "pen_cup"))  # pen_cup | pen_block | grip_enlarger

# ── Clamps / derived values ──────────────────────────────────────────────────
pen_dia   = max(4.0, min(pen_dia, 25.0))
clearance = max(0.4, min(clearance, 4.0))
wall      = max(1.6, min(wall, 8.0))
height    = max(30.0, min(height, 200.0))
bore_dia  = pen_dia + clearance                    # actual drilled hole Ø
cup_dia   = max(pen_dia * 3.0, min(cup_dia, 200.0))
cols      = max(1, min(cols, 8))
rows      = max(1, min(rows, 5))
rake_deg  = max(0.0, min(rake_deg, 30.0))
grip_len  = max(40.0, min(grip_len, 160.0))
grip_dia  = max(pen_dia + 2.0 * wall, min(grip_dia, 45.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _cyl(dia, h, x=0.0, y=0.0, z=0.0):
    """A solid cylinder, base at z, centred on (x, y)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .circle(dia / 2.0)
        .extrude(h)
    )


def _box(w, d, h, x=0.0, y=0.0, z=0.0):
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(True, True, False))
    )


# ── Builders ─────────────────────────────────────────────────────────────────
def build_pen_cup():
    """Round cup: solid cylinder hollowed to a five-wall shell open at the top,
    fillet-rounded at the base, with an optional single internal divider."""
    body = _cyl(cup_dia, height)
    # Round the bottom outer rim BEFORE cutting the cavity (fillet on a plain
    # solid is robust; on a feature-laden shell it can crash OCCT clean()).
    try:
        body = body.edges(cq.selectors.RadiusNearestSelector(cup_dia / 2.0)) \
                   .edges("<Z").fillet(min(wall * 0.9, 3.0))
    except Exception:
        try:
            body = body.faces("<Z").edges().fillet(min(wall * 0.9, 3.0))
        except Exception:
            pass
    # Cavity opens upward (never sealed): floor thickness = wall.
    cavity = _cyl(cup_dia - 2.0 * wall, height, z=wall)
    body = body.cut(cavity)
    # Optional divider: a solid wall across the cavity, seated on the floor and
    # overlapping both side walls so the union leaves no zero-volume seam.
    if divider:
        wall_wp = _box(wall, cup_dia, height - wall, z=wall)
        # Trim the divider to the inner cylinder so it doesn't poke past the wall.
        inner = _cyl(cup_dia - 2.0 * wall + 0.02, height, z=wall)
        try:
            wall_wp = wall_wp.intersect(inner)
            # Re-extend to bond into the side walls (add a hair on each end).
            bridge = _box(wall, cup_dia, height - wall, z=wall)
            wall_wp = wall_wp.union(
                bridge.intersect(_cyl(cup_dia, height, z=wall))
            )
            body = body.union(wall_wp)
        except Exception:
            pass
    return body


def build_pen_block():
    """Rounded desk block with an array of blind bores drilled from the top.
    Bores open upward — no trapped voids. The front row is raked forward so its
    pens lean toward the user."""
    pitch = bore_dia + max(wall, 4.0)
    block_w = cols * pitch + wall
    block_d = rows * pitch + wall
    block_h = height * 0.55
    body = _box(block_w, block_d, block_h)
    # Fillet the vertical corners BEFORE cutting bores.
    try:
        body = body.edges("|Z").fillet(min(wall * 1.5, block_w / 6.0, block_d / 6.0))
    except Exception:
        pass

    depth = block_h - wall  # blind bore leaves `wall` of floor
    x0 = -(cols - 1) * pitch / 2.0
    y0 = -(rows - 1) * pitch / 2.0
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * pitch
            y = y0 + r * pitch
            is_front = (r == 0 and rows > 1 and rake_deg > 0.1)
            if is_front:
                # Raked bore: a cylinder tilted about X, cut so its mouth is on
                # the top face. Over-long so the tilt still reaches the surface.
                bore = (
                    cq.Workplane("XY")
                    .transformed(offset=cq.Vector(x, y, block_h))
                    .transformed(rotate=cq.Vector(rake_deg, 0, 0))
                    .circle(bore_dia / 2.0)
                    .extrude(-(depth + bore_dia))
                )
            else:
                bore = _cyl(bore_dia, depth + 0.5, x=x, y=y, z=block_h - depth)
            body = body.cut(bore)
    return body


def build_grip_enlarger():
    """Ergonomic sleeve: a through-tube (open both ends → not a trapped void)
    that slips over a thin pen to fatten the grip, with unioned finger ridges."""
    body = _cyl(grip_dia, grip_len)
    # Chamfer/round the ends for comfort BEFORE boring the bore.
    try:
        body = body.faces(">Z").edges().chamfer(min(1.5, wall * 0.5))
        body = body.faces("<Z").edges().chamfer(min(1.5, wall * 0.5))
    except Exception:
        pass
    # Finger ridges: three shallow rings unioned onto the barrel (solid, so they
    # never introduce a cavity). Placed in the gripping third of the sleeve.
    ridge_dia = grip_dia + 3.0
    for frac in (0.30, 0.45, 0.60):
        zc = grip_len * frac
        ridge = _cyl(ridge_dia, 4.0, z=zc)
        # Barrel the ridge with a top/bottom chamfer for a smooth bump.
        try:
            ridge = ridge.faces(">Z").edges().chamfer(1.8)
            ridge = ridge.faces("<Z").edges().chamfer(1.8)
        except Exception:
            pass
        body = body.union(ridge)
    # Through-bore for the pen (open at both ends).
    bore = _cyl(bore_dia, grip_len + 20.0, z=-10.0)
    body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pen_block":
    result = build_pen_block()
elif target_part == "grip_enlarger":
    result = build_grip_enlarger()
else:
    result = build_pen_cup()
