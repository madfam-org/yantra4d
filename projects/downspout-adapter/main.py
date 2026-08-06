"""
Rain-Barrel / Downspout Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Adapts a rectangular house downspout to a round pipe or rain-barrel inlet — the
missing piece for rainwater harvesting. The core is a hollow transition that lofts a
rectangular mouth (the downspout, e.g. 2×3" or 3×4") into a round outlet (a barrel
bulkhead or a length of round pipe). Variants add a mounting flange for a barrel lid
and a coarse debris screen so leaves and grit stay out of the barrel.

Design idiom (hollow transition shell):
  The transition is OUTER loft minus INNER loft. The outer loft goes from a rounded
  rectangle (downspout OD) to a circle (outlet OD); the inner loft is the same two
  profiles inset by `wall`. Subtracting inner from outer yields a constant-wall
  hollow duct — a closed shell with a rectangular opening at the top and a round
  opening at the bottom, which exports watertight. Short straight collars at each end
  give clean sealing/slip faces.

  Lofts use explicit wires + `cq.Solid.makeLoft` because a rounded-rectangle wire
  can't be lofted through the fluent `.rect().workplane().circle().loft()` chain
  (the mid-chain `.vertices().fillet()` needs a solid). The rounded-rect wire is
  built from `cq.Sketch` and collars are raised with `cq.Solid.extrudeLinear`.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `wall`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(  PARAM(lambda: target_part, "rect_to_round"))  # rect_to_round | barrel_inlet | screen_box
spout_w     = float(PARAM(lambda: spout_w,    76.0))    # downspout width  (mm); 3" ≈ 76
spout_d     = float(PARAM(lambda: spout_d,    51.0))    # downspout depth  (mm); 2" ≈ 51
outlet_dia  = float(PARAM(lambda: outlet_dia, 60.0))    # round outlet diameter (mm)
trans_len   = float(PARAM(lambda: trans_len,  70.0))    # transition length (mm)
wall        = float(PARAM(lambda: wall,        3.0))    # shell wall thickness (mm)
collar_len  = float(PARAM(lambda: collar_len, 12.0))   # straight collar at each end (mm)
screen      = bool( PARAM(lambda: screen,     False))  # debris screen grid across the round outlet
flange_w    = float(PARAM(lambda: flange_w,   30.0))   # barrel-lid mounting flange width (mm)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
spout_w = max(20.0, min(spout_w, 200.0))
spout_d = max(20.0, min(spout_d, 200.0))
outlet_dia = max(15.0, min(outlet_dia, 200.0))
trans_len = max(20.0, min(trans_len, 200.0))
wall = max(1.6, min(wall, 8.0))
collar_len = max(4.0, min(collar_len, 40.0))
flange_w = max(10.0, min(flange_w, 80.0))

rect_r = min(spout_w, spout_d) * 0.15   # gentle corner radius on the rectangle mouth
out_r = outlet_dia / 2.0


# ── Wire / shell primitives ───────────────────────────────────────────────────
def rrect_wire(w, d, r, z=0.0):
    """A rounded-rectangle wire (from a Sketch) at height z, centered on XY."""
    s = cq.Sketch().rect(w, d)
    r = max(0.0, min(r, min(w, d) / 2.0 - 0.01))
    if r > 0.1:
        s = s.vertices().fillet(r)
    wire = s._faces.Wires()[0]
    if abs(z) > 1e-9:
        wire = wire.translate((0, 0, z))
    return wire


def circ_wire(dia, z):
    """A circular wire at height z."""
    return cq.Workplane("XY").workplane(offset=z).circle(dia / 2.0).wires().val()


def extrude_wire(wire, dz):
    """Extrude a closed wire linearly by dz into a solid Workplane."""
    sol = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, dz))
    return cq.Workplane("XY").add(sol)


def loft_wires(w_bottom, w_top):
    """Loft two wires into a solid Workplane."""
    sol = cq.Solid.makeLoft([w_bottom, w_top])
    return cq.Workplane("XY").add(sol)


def hollow_transition():
    """Constant-wall hollow duct with straight collars top and bottom.

    The outer envelope is unioned into ONE solid; the interior is then removed as
    THREE sequential cuts (bottom rect prism, tapered inner loft, top round bore).
    Sequential cuts are used instead of unioning the void pieces first because the
    near-coincident inner faces where the loft meets the collars make an OCC union
    collapse into a non-manifold void (leaving the shell open). Each cut piece
    over-runs its opening so the bore is fully through and the mesh stays watertight."""
    inner_w = spout_w - 2.0 * wall
    inner_d = spout_d - 2.0 * wall
    inner_r = max(0.0, rect_r - wall)
    inner_out_r = max(1.0, out_r - wall)

    # ── Outer envelope (single solid) ──
    outer = loft_wires(rrect_wire(spout_w, spout_d, rect_r, 0.0), circ_wire(outlet_dia, trans_len))
    coll_b_out = extrude_wire(rrect_wire(spout_w, spout_d, rect_r, 0.0), -collar_len)
    coll_t_out = cq.Workplane("XY").workplane(offset=trans_len).circle(out_r).extrude(collar_len)
    body = outer.union(coll_b_out).union(coll_t_out)

    # ── Interior removed as sequential cuts ──
    # (1) Bottom rectangular bore: from below the bottom collar up to just past z=0
    #     into the tapered region, so it fuses with the loft cut.
    bot_prism = extrude_wire(rrect_wire(inner_w, inner_d, inner_r, -collar_len - 1.0), collar_len + 1.0 + 2.0)
    body = body.cut(bot_prism)
    # (2) Tapered inner loft across the transition, extended a hair beyond both ends.
    inner_loft = loft_wires(
        rrect_wire(inner_w, inner_d, inner_r, -0.5), circ_wire(inner_out_r, trans_len + 0.5)
    )
    body = body.cut(inner_loft)
    # (3) Top round bore: from just below the top of the loft up past the top collar.
    top_bore = (
        cq.Workplane("XY")
        .workplane(offset=trans_len - 1.0)
        .circle(inner_out_r)
        .extrude(collar_len + 2.0)
    )
    body = body.cut(top_bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def add_screen(body, z):
    """A coarse debris grid across the round outlet at height z: a thin disk unioned
    then drilled with a ring of holes (volumetric, stays watertight)."""
    disk_t = max(1.4, wall * 0.7)
    grid = cq.Workplane("XY").workplane(offset=z).circle(out_r - wall * 0.5).extrude(disk_t)
    body = body.union(grid)
    hole_r = max(1.2, out_r * 0.12)
    rings = [(out_r * 0.45, 6), (out_r * 0.75, 10)]
    for rad, count in rings:
        for k in range(count):
            ang = math.radians(360.0 / count * k)
            hx = rad * math.cos(ang)
            hy = rad * math.sin(ang)
            hole = cq.Workplane("XY").workplane(offset=z - 1.0).center(hx, hy).circle(hole_r).extrude(disk_t + 2.0)
            try:
                body = body.cut(hole)
            except Exception:
                pass
    body = body.cut(cq.Workplane("XY").workplane(offset=z - 1.0).circle(hole_r).extrude(disk_t + 2.0))
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ─────────────────────────────────────────────────────────────
def build_rect_to_round():
    """The bare hollow transition, optionally with a debris screen across the outlet."""
    body = hollow_transition()
    if screen:
        body = add_screen(body, trans_len + collar_len - max(1.4, wall * 0.7) - 0.5)
    return body


def build_barrel_inlet():
    """Transition + a flat mounting flange around the round outlet, so it seats on a
    rain-barrel lid, with 4 bolt holes."""
    body = hollow_transition()
    z = trans_len + collar_len
    flange_outer = out_r + flange_w
    flange_t = max(3.0, wall)
    ring = (
        cq.Workplane("XY")
        .workplane(offset=z - flange_t)
        .circle(flange_outer)
        .circle(max(1.0, out_r - wall))
        .extrude(flange_t)
    )
    body = body.union(ring)
    bhc = out_r + flange_w * 0.55
    for k in range(4):
        ang = math.radians(90.0 * k + 45.0)
        hx = bhc * math.cos(ang)
        hy = bhc * math.sin(ang)
        hole = cq.Workplane("XY").workplane(offset=z - flange_t - 1.0).center(hx, hy).circle(2.6).extrude(flange_t + 2.0)
        try:
            body = body.cut(hole)
        except Exception:
            pass
    if screen:
        body = add_screen(body, z - max(1.4, wall * 0.7) - 0.5)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_screen_box():
    """A standalone debris-filter tray that hangs in the downspout mouth: a shallow
    rectangular box (open top) with a perforated floor and a lip flange. Catches
    leaves before they reach the transition."""
    box_h = max(18.0, spout_d * 0.5)
    floor_t = max(1.6, wall)
    outer = extrude_wire(rrect_wire(spout_w, spout_d, rect_r, 0.0), box_h)
    cavity = extrude_wire(
        rrect_wire(spout_w - 2.0 * wall, spout_d - 2.0 * wall, max(0.0, rect_r - wall), floor_t), box_h
    )
    body = outer.cut(cavity)

    # Perforate the floor.
    nx = max(2, int(spout_w / 12.0))
    ny = max(2, int(spout_d / 12.0))
    hole_r = 2.4
    for ix in range(nx):
        for iy in range(ny):
            hx = -spout_w / 2.0 + (ix + 0.5) * spout_w / nx
            hy = -spout_d / 2.0 + (iy + 0.5) * spout_d / ny
            if abs(hx) > spout_w / 2.0 - wall - hole_r or abs(hy) > spout_d / 2.0 - wall - hole_r:
                continue
            hole = cq.Workplane("XY").center(hx, hy).circle(hole_r).extrude(floor_t + 2.0).translate((0, 0, -1.0))
            try:
                body = body.cut(hole)
            except Exception:
                pass

    # Lip flange around the top so the tray hangs in the downspout.
    lip_h = max(2.5, wall)
    lip_out = extrude_wire(rrect_wire(spout_w + 2.0 * wall + 8.0, spout_d + 2.0 * wall + 8.0, rect_r, 0.0), lip_h)
    lip_out = lip_out.translate((0, 0, box_h - lip_h))
    lip_void = extrude_wire(rrect_wire(spout_w, spout_d, rect_r, 0.0), lip_h + 2.0)
    lip_void = lip_void.translate((0, 0, box_h - lip_h - 1.0))
    lip = lip_out.cut(lip_void)
    body = body.union(lip)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "barrel_inlet":
    result = build_barrel_inlet()
elif target_part == "screen_box":
    result = build_screen_box()
else:
    result = build_rect_to_round()
