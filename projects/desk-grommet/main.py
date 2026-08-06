"""
Cable Grommet / Desk Port — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A grommet that drops into a round cable pass-through hole in a desk. A tubular
body sized to the desk bore, a flange lip that rests on the desktop, and an open
cable slot so cords route in from the side without threading through. An optional
matching lid caps the port.

Modes are dispatched via `target_part`:
  * "grommet"       — the ring with flange and an open cable slot.
  * "grommet_lid"   — a cap that sits in the flange, with a cable slot of its own.
  * "round_grommet" — the closed ring (no slot); cords must be threaded through.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bore_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
bore_dia   = float(PARAM(lambda: bore_dia,  60.0))   # desk hole diameter (fits into it)
depth      = float(PARAM(lambda: depth,     25.0))   # desk thickness (body drop below flange)
wall       = float(PARAM(lambda: wall,       2.5))   # tube wall thickness
flange     = float(PARAM(lambda: flange,     6.0))   # flange lip width beyond the bore
flange_t   = float(PARAM(lambda: flange_t,   3.0))   # flange plate thickness
fit_clear  = float(PARAM(lambda: fit_clear,  0.4))   # bore-fit clearance (per side)

slot       = bool(PARAM(lambda: slot,       True))   # open cable slot in the ring
slot_w     = float(PARAM(lambda: slot_w,    20.0))   # cable slot width
lid        = bool(PARAM(lambda: lid,        True))   # (documentation flag; lid is its own mode)
lid_slot_w = float(PARAM(lambda: lid_slot_w, 14.0))  # lid cable slot width

target_part = str(PARAM(lambda: target_part, "grommet"))  # grommet|grommet_lid|round_grommet

# ── Derived ──────────────────────────────────────────────────────────────────
bore_dia = max(10.0, bore_dia)
depth = max(3.0, depth)
wall = max(1.2, wall)
flange = max(2.0, flange)
flange_t = max(1.2, flange_t)
fit_clear = max(0.0, min(fit_clear, 1.5))

# Body outer radius drops into the bore (with a slip clearance); inner radius is
# the cord opening.
body_or = bore_dia / 2.0 - fit_clear
body_ir = max(3.0, body_or - wall)
flange_or = bore_dia / 2.0 + flange

slot_w = max(3.0, min(slot_w, bore_dia - 4.0))
lid_slot_w = max(3.0, min(lid_slot_w, bore_dia - 4.0))


# ── Helpers ──────────────────────────────────────────────────────────────────
def tube(outer_r, inner_r, height, z0=0.0):
    """A hollow cylinder from z0 upward."""
    o = cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, z0)).circle(outer_r).extrude(height)
    if inner_r > 0.05:
        i = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0 - 0.5))
            .circle(inner_r)
            .extrude(height + 1.0)
        )
        o = o.cut(i)
    return o


def cut_slot(body, width, z0, height):
    """Cut an open channel through +Y so cords route in from the side.
    The slot spans from the centre outward past the flange edge."""
    reach = flange_or + 2.0
    cutter = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, reach / 2.0, z0 + height / 2.0))
        .box(width, reach, height + 1.0, centered=(True, True, True))
    )
    return body.cut(cutter)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_grommet(open_slot):
    """Flanged tube. `open_slot` toggles the side cable channel."""
    # Flange plate sits on the desktop (z: 0..flange_t).
    flange_plate = tube(flange_or, body_ir, flange_t, z0=0.0)
    try:
        flange_plate = flange_plate.edges(">Z").chamfer(min(flange_t * 0.4, 0.8))
    except Exception:
        pass

    # Body hangs below the flange into the desk (z: -depth..0).
    barrel = tube(body_or, body_ir, depth, z0=-depth)

    grommet = flange_plate.union(barrel)

    # Optional lid seat: a shallow rebate in the flange top so the matching cap
    # sits flush instead of proud. Driven by the `lid` flag.
    if lid:
        seat_r = body_ir + 0.6
        seat_d = min(1.5, flange_t - 1.0)
        if seat_d > 0.05 and seat_r < flange_or - 1.0:
            rebate = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, flange_t - seat_d))
                .circle(seat_r)
                .extrude(seat_d + 1.0)
            )
            grommet = grommet.cut(rebate)

    if open_slot:
        grommet = cut_slot(grommet, slot_w, -depth, depth + flange_t)

    return grommet


def build_lid():
    """A cap that seats in the flange opening, with its own cable slot.
    Sized to slip inside the barrel bore with a light clearance."""
    plug_r = body_ir - 0.4
    cap_r = flange_or
    cap_t = flange_t
    plug_h = min(depth * 0.5, 8.0)

    cap = cq.Workplane("XY").circle(cap_r).extrude(cap_t)
    try:
        cap = cap.edges(">Z").chamfer(min(cap_t * 0.4, 0.8))
    except Exception:
        pass
    plug = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -plug_h)
    ).circle(plug_r).extrude(plug_h)
    # Hollow the plug so it prints light and clips.
    plug_bore = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -plug_h - 0.5)
    ).circle(max(2.0, plug_r - 2.0)).extrude(plug_h + cap_t + 1.0)
    body = cap.union(plug).cut(plug_bore)

    # Cable slot through the lid so it closes around existing cords.
    body = cut_slot(body, lid_slot_w, -plug_h, plug_h + cap_t)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "grommet_lid":
    result = build_lid()
elif target_part == "round_grommet":
    result = build_grommet(False)
else:
    result = build_grommet(True)
