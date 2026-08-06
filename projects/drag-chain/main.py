"""
Cable Drag Chain (e-chain) — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A single cable-carrier link that pins to identical links to form a flexible chain
for moving cables/hoses on gantries, 3D-printer axes, and CNC machines. Each link
is a rigid rectangular frame (two side plates + top & bottom cross-bars forming a
closed channel) with a peg on one end and a matching socket on the other, so
consecutive links pin together and pivot until a built-in stop limits the bend.

Interface (Drag-Chain Link Pin, `snap`, internal):
  The pin/socket geometry is defined by `pitch` (link length along travel) and
  `bend_radius` (how far a joint may pivot before the stop face contacts).
  Root radii/overlaps push mating solids a little into the frame so every boolean
  is volumetric — that is what keeps the mesh watertight instead of a fragile
  tangent kiss.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `inner_w`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


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
inner_w     = float(PARAM(lambda: inner_w,     18.0))   # cable channel width (Y, mm)
inner_h     = float(PARAM(lambda: inner_h,     16.0))   # cable channel height (Z, mm)
pitch       = float(PARAM(lambda: pitch,       30.0))   # link length along travel (X, mm)
wall        = float(PARAM(lambda: wall,         2.4))   # plate / bar thickness (mm)
bend_radius = float(PARAM(lambda: bend_radius, 40.0))   # min bend radius the joint allows (mm)
pin_dia     = float(PARAM(lambda: pin_dia,      4.0))   # pin / socket nominal diameter (mm)
clearance   = float(PARAM(lambda: clearance,    0.35))  # printed pin-in-socket slop per side (mm)

target_part = str(PARAM(lambda: target_part, "link"))   # link | link_open | end_bracket

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
inner_w = max(6.0, min(inner_w, 80.0))
inner_h = max(6.0, min(inner_h, 80.0))
wall = max(1.6, min(wall, 6.0))
pin_dia = max(2.5, min(pin_dia, 10.0))
clearance = max(0.15, min(clearance, 0.8))
# A link must be long enough to host a pin at each end plus the stop lug.
pitch = max(pin_dia * 3.5 + 6.0, min(pitch, 120.0))
bend_radius = max(pitch * 0.8, min(bend_radius, 400.0))

# ── Derived envelope ─────────────────────────────────────────────────────────
outer_w = inner_w + 2.0 * wall          # total width across side plates (Y)
outer_h = inner_h + 2.0 * wall          # total height (Z)
pin_r = pin_dia / 2.0
# Pins sit on the vertical mid-height, one radius + margin in from each X end.
pin_inset = pin_r + wall * 0.6
pin_z = outer_h / 2.0
# The pivot stop: a small lug whose flank angle sets the max articulation. A
# larger bend_radius (gentler curve) means a smaller allowed pivot angle.
stop_angle = max(6.0, min(35.0, math.degrees(math.asin(min(0.6, pitch / bend_radius)))))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(x, y, z, cx=0.0, cy=0.0, cz=0.0, center=(True, True, False)):
    """A box placed with its local origin offset to (cx, cy, cz)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, cz))
        .box(x, y, z, centered=center)
    )


def _frame(with_top):
    """Rigid channel: two side plates + a bottom bar (+ optional top bar).
    Built as one solid so front/back stay open (the cable channel) while the
    cross-section is a closed, watertight profile."""
    # Side plates: full pitch length, full height, `wall` thick, offset in Y.
    y_off = inner_w / 2.0 + wall / 2.0
    left = _box(pitch, wall, outer_h, cx=pitch / 2.0, cy=+y_off)
    right = _box(pitch, wall, outer_h, cx=pitch / 2.0, cy=-y_off)
    body = left.union(right)

    # Bottom cross-bar spans the full width, seated on the floor.
    bottom = _box(pitch, outer_w, wall, cx=pitch / 2.0, cy=0.0, cz=0.0)
    body = body.union(bottom)

    if with_top:
        top = _box(pitch, outer_w, wall, cx=pitch / 2.0, cy=0.0, cz=outer_h - wall)
        body = body.union(top)
    return body


def _pins_and_sockets(body):
    """Add a pin on the +X face of each side plate and bore a socket into the
    -X face of each side plate, so link N's +X pins enter link N+1's -X sockets."""
    y_off = inner_w / 2.0 + wall / 2.0
    pin_len = wall * 0.9  # protrudes ~one wall outward
    socket_depth = pin_len + clearance + 0.4

    for sign in (+1.0, -1.0):
        yc = sign * y_off
        # ── Pin on +X end (points +X, outboard face of the plate) ──
        pin = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(yc, pin_z, pitch))
            .circle(pin_r)
            .extrude(pin_len)
        )
        # small chamfered lead-in so it clicks in
        try:
            pin = pin.faces(">X").chamfer(min(0.6, pin_r * 0.4))
        except Exception:
            pass
        body = body.union(pin)

        # ── Socket bore on -X end (into the plate from outside) ──
        socket = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(yc, pin_z, socket_depth))
            .circle(pin_r + clearance)
            .extrude(-socket_depth - 0.2)
        )
        body = body.cut(socket)
    return body


def _stop_lugs(body):
    """Add articulation-stop lugs: a wedge on the +X top corner of each side
    plate that contacts the neighbour and limits the bend to `stop_angle`.
    Purely a rigid feature on the printed part (union), so it stays watertight."""
    y_off = inner_w / 2.0 + wall / 2.0
    lug_h = max(1.5, outer_h * 0.18)
    lug_x = max(2.0, pitch * 0.12)
    for sign in (+1.0, -1.0):
        yc = sign * y_off
        lug = _box(lug_x, wall, lug_h, cx=pitch - lug_x / 2.0, cy=yc,
                   cz=outer_h - lug_h)
        # Rake the outer top edge by stop_angle so the contact face is angled.
        try:
            cut_h = lug_h * math.tan(math.radians(stop_angle))
            wedge = (
                cq.Workplane("XZ")
                .transformed(offset=cq.Vector(pitch, outer_h, -yc - wall))
                .polyline([(0, 0), (-lug_x, 0), (0, -min(cut_h, lug_h))])
                .close()
                .extrude(-wall)
            )
            lug = lug.cut(wedge)
        except Exception:
            pass
        body = body.union(lug)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_link(with_top=True):
    """One closed-frame segment with peg + socket at each end and stop lugs."""
    body = _frame(with_top=with_top)
    body = _pins_and_sockets(body)
    body = _stop_lugs(body)
    return body


def build_link_open():
    """Same frame but with a separate snap-on top bar sitting in place (models an
    openable lid). The bar carries two small retention tabs that drop into
    notches in the side-plate tops. Rendered as one assembly-in-place solid."""
    base = _frame(with_top=False)
    base = _pins_and_sockets(base)
    base = _stop_lugs(base)

    # Notches in the side-plate tops to receive the lid tabs.
    y_off = inner_w / 2.0 + wall / 2.0
    tab_x = max(3.0, pitch * 0.18)
    tab_d = min(wall * 0.7, 1.6)
    for sign in (+1.0, -1.0):
        yc = sign * y_off
        notch = _box(tab_x, tab_d + 0.4, tab_d + 0.3,
                     cx=pitch / 2.0, cy=yc, cz=outer_h - (tab_d + 0.3))
        base = base.cut(notch)

    # Removable top bar spanning the width, seated in place, with two tabs.
    lid = _box(pitch * 0.92, outer_w, wall, cx=pitch / 2.0, cy=0.0,
               cz=outer_h - wall)
    for sign in (+1.0, -1.0):
        yc = sign * y_off
        tab = _box(tab_x, tab_d, tab_d, cx=pitch / 2.0, cy=yc,
                   cz=outer_h - wall - tab_d)
        lid = lid.union(tab)
    body = base.union(lid)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_end_bracket():
    """Mounting bracket that bolts the chain end to a frame: a flat foot with two
    countersunk bolt holes, rising into a short frame stub that presents the same
    peg/socket end so it pins to a normal link."""
    foot_len = max(14.0, pitch * 0.7)
    foot_th = max(3.0, wall * 1.5)
    foot_w = outer_w + 6.0

    # Flat mounting foot in the XY plane.
    foot = _box(foot_len, foot_w, foot_th, cx=foot_len / 2.0, cy=0.0, cz=0.0)

    # Two bolt holes through the foot.
    hole_r = 2.6  # M5 clearance-ish
    for hx in (foot_len * 0.28, foot_len * 0.72):
        bolt = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, 0, -0.5))
            .circle(hole_r)
            .extrude(foot_th + 1.0)
        )
        # shallow countersink on top
        csk = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(hx, 0, foot_th - 1.2))
            .circle(hole_r + 1.4)
            .workplane(offset=1.3)
            .circle(hole_r)
            .loft(combine=True)
        )
        foot = foot.cut(bolt)
        try:
            foot = foot.cut(csk)
        except Exception:
            pass

    # Frame stub rising at the far (+X) end, presenting a pin/socket end.
    stub_pitch = pin_dia * 3.5 + 4.0
    y_off = inner_w / 2.0 + wall / 2.0
    left = _box(stub_pitch, wall, outer_h, cx=foot_len - stub_pitch / 2.0,
                cy=+y_off, cz=foot_th)
    right = _box(stub_pitch, wall, outer_h, cx=foot_len - stub_pitch / 2.0,
                 cy=-y_off, cz=foot_th)
    stub = left.union(right)
    bottom = _box(stub_pitch, outer_w, wall, cx=foot_len - stub_pitch / 2.0,
                  cy=0.0, cz=foot_th)
    stub = stub.union(bottom)

    # Pin on the +X end of the stub (mirrors a link's +X pins).
    for sign in (+1.0, -1.0):
        yc = sign * y_off
        pin = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(yc, foot_th + outer_h / 2.0, foot_len))
            .circle(pin_r)
            .extrude(wall * 0.9)
        )
        stub = stub.union(pin)

    body = foot.union(stub)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "link_open":
    result = build_link_open()
elif target_part == "end_bracket":
    result = build_end_bracket()
else:
    result = build_link()
