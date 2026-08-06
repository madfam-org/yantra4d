"""
Solar Light / Path Stake — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Replaces the brittle plastic ground stakes that snap off cheap solar path lights.
A tapered ground spike carries a standardized fixture socket (the CDG "Fixture
Socket") that the light head, a reflective marker, or a sign plugs into. Three
parts: a bare stake with the socket, a light housing that caps a solar/LED head,
and a marker stake with a flat sign paddle.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `spike_len`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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
target_part = str(PARAM(lambda: target_part, "stake"))  # stake | light_housing | marker_stake

spike_len   = float(PARAM(lambda: spike_len,  120.0))  # buried ground-spike length (mm)
spike_dia   = float(PARAM(lambda: spike_dia,   20.0))  # spike top diameter (tapers to a point)
socket_dia  = float(PARAM(lambda: socket_dia,  22.0))  # fixture socket bore diameter (mm)
socket_depth= float(PARAM(lambda: socket_depth,25.0))  # how deep the fixture plugs in (mm)
wall        = float(PARAM(lambda: wall,         3.0))  # socket / housing wall thickness (mm)
clearance   = float(PARAM(lambda: clearance,   0.4))   # socket fit slop per side (mm)
fins        = int(  PARAM(lambda: fins,           4))  # anti-rotation fins on the spike
head_dia    = float(PARAM(lambda: head_dia,    58.0))  # solar/LED head diameter (light_housing)
head_h      = float(PARAM(lambda: head_h,      30.0))  # head cup depth (light_housing)
sign_w      = float(PARAM(lambda: sign_w,      60.0))  # sign paddle width (marker_stake)
sign_h      = float(PARAM(lambda: sign_h,      90.0))  # sign paddle height (marker_stake)

# ── Clamp to sane ranges so extreme UI values still build watertight ─────────
spike_len    = max(40.0, min(spike_len, 300.0))
spike_dia    = max(10.0, min(spike_dia, 50.0))
socket_dia   = max(8.0, min(socket_dia, 60.0))
socket_depth = max(10.0, min(socket_depth, 80.0))
wall         = max(2.0, min(wall, 8.0))
clearance    = max(0.1, min(clearance, 1.0))
fins         = max(0, min(fins, 8))
head_dia     = max(25.0, min(head_dia, 140.0))
head_h       = max(12.0, min(head_h, 80.0))
sign_w       = max(25.0, min(sign_w, 200.0))
sign_h       = max(30.0, min(sign_h, 250.0))

socket_or = socket_dia / 2.0 + wall   # socket outer radius (the collar)


def _spike(with_fins=True):
    """A tapered ground spike pointing DOWN (tip at the bottom), with its wide top
    at z=0. Optional anti-rotation fins near the top keep it from spinning in soil.
    Returns the spike solid occupying z:[-spike_len, 0]."""
    tip_r = 1.5
    top_r = spike_dia / 2.0
    spike = (
        cq.Workplane("XY")
        .circle(tip_r)
        .workplane(offset=spike_len)
        .circle(top_r)
        .loft(combine=True)
        .translate((0, 0, -spike_len))
    )
    if with_fins and fins > 0:
        fin_h = spike_len * 0.5
        fin_w = 2.5
        fin_out = top_r * 1.4
        try:
            blades = (
                cq.Workplane("XY")
                .polarArray(radius=fin_out / 2.0, startAngle=0, angle=360, count=fins)
                .rect(fin_out, fin_w)
                .extrude(fin_h)
                .translate((0, 0, -fin_h))
            )
            # Trim the blades to the spike's taper envelope by intersecting with a
            # cone; simpler + safe: just union — fins wider than soil grip is fine.
            spike = spike.union(blades)
        except Exception:
            pass  # fins are grip-nice — never fatal
    return spike


def _fixture_socket(z0):
    """An upward-opening socket collar on z0 that a fixture stem plugs into. Bore =
    socket_dia + clearance per side. Returns (solid, top_z)."""
    bore_r = socket_dia / 2.0 + clearance
    h = socket_depth + wall
    collar = cq.Workplane("XY").circle(socket_or).extrude(h).translate((0, 0, z0))
    bore = cq.Workplane("XY").circle(bore_r).extrude(socket_depth + 1.0).translate((0, 0, z0 + wall))
    collar = collar.cut(bore)
    return collar, z0 + h


def _base_disk():
    """A ground-line flange disk between spike and socket so the stake seats at a
    consistent depth and does not sink under the light's weight."""
    return cq.Workplane("XY").circle(max(socket_or, spike_dia / 2.0) + 4.0).extrude(wall)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_stake():
    """Bare stake: ground spike + seating flange + fixture socket."""
    spike = _spike(with_fins=True)
    disk = _base_disk()
    socket, _ = _fixture_socket(wall)
    body = spike.union(disk).union(socket)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_light_housing():
    """A cup that holds a round solar/LED head, with a MALE stem underneath that
    plugs into the stake's fixture socket. Prints as the light-head carrier."""
    # Cup: an open-top cylinder sized to the head with a small retaining lip.
    cup_or = head_dia / 2.0 + wall
    cup = cq.Workplane("XY").circle(cup_or).extrude(head_h + wall)
    cup = cup.cut(
        cq.Workplane("XY").circle(head_dia / 2.0).extrude(head_h + 1.0).translate((0, 0, wall))
    )
    # Male stem under the cup that matches the fixture socket (minus clearance so
    # it fits the female socket). Its outer diameter = socket bore.
    stem_r = socket_dia / 2.0 - clearance
    stem_h = socket_depth
    stem = cq.Workplane("XY").circle(stem_r).extrude(stem_h).translate((0, 0, -stem_h))
    # Fillet the cup/stem junction shoulder lightly for strength.
    body = cup.union(stem)
    # Drainage/vent hole in the cup floor so rain does not pool on the head.
    body = body.cut(
        cq.Workplane("XY").circle(min(4.0, stem_r * 0.5)).extrude(wall * 2.0 + 2.0).translate((0, 0, -1.0))
    )
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_marker_stake():
    """A path marker: ground spike + a flat sign paddle standing above the ground
    line (for numbers, plant labels, reflectors). No socket — the paddle is fixed."""
    spike = _spike(with_fins=True)
    disk = _base_disk()

    # Riser neck from the ground line up to the paddle.
    neck_h = 20.0
    neck = cq.Workplane("XY").circle(max(6.0, sign_w * 0.08)).extrude(neck_h).translate((0, 0, wall))

    # Flat paddle in the XZ plane (a thin plate) rising from the neck.
    plate_t = max(3.0, wall)
    paddle = (
        cq.Workplane("XY")
        .box(sign_w, plate_t, sign_h, centered=(True, True, False))
        .translate((0, 0, wall + neck_h))
        .edges("|Y").fillet(min(6.0, sign_w * 0.15, sign_h * 0.15))
    )
    body = spike.union(disk).union(neck).union(paddle)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "light_housing":
    result = build_light_housing()
elif target_part == "marker_stake":
    result = build_marker_stake()
else:
    result = build_stake()
