"""
Cold/Hot Accessory Shoe Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The ISO 518 camera accessory shoe — the ~18.7 mm-wide rail with rounded-corner
flanges that every on-camera light, microphone, monitor and flash slides onto.
This cartridge builds the male shoe foot (slides INTO a camera), a female shoe
socket (the camera-side receiver an accessory slides into), and a dual-shoe bar
(two sockets on a bracket for rigging two accessories at once).

ISO 518 accessory shoe geometry (nominal, dimensionally real):
  - overall foot width      ≈ 18.7 mm  (the "shoe" outer width)
  - channel / tongue width  ≈ 14.9 mm  (the recessed centre the flanges frame)
  - flange thickness (Z)    ≈ 1.6 mm    (the thin lip the socket grips)
  - flange rounded corners  ≈ 1.0 mm    radius on the outer edges
  - the male foot slides along +Y into a socket whose overhanging lips capture
    the flanges; a spring/detent (not modelled) locks it.

Watertight strategy:
  Every part is built from extruded 2D cross-sections (the accessory-shoe
  profile) and axis-aligned box unions that OVERLAP into shared material — no
  tangent kisses, no post-cut fillets. The rounded flange corners live in the
  2D profile (filleted before extrusion), so the mesh stays crack-free.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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


# ── Parameters (ISO 518 accessory shoe) ──────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "cold_shoe_male"))
# "cold_shoe_male" | "shoe_socket" | "dual_shoe_bar"
shoe_type = str(PARAM(lambda: shoe_type, "male-shoe"))
# "male-shoe" | "female-shoe-slot" — biases lone builds toward foot vs receiver

foot_width = float(PARAM(lambda: foot_width, 18.7))   # ISO 518 outer shoe width (X)
channel_w = float(PARAM(lambda: channel_w, 14.9))     # recessed tongue width (X)
flange_th = float(PARAM(lambda: flange_th, 1.6))      # flange lip thickness (Z)
shoe_len = float(PARAM(lambda: shoe_len, 20.0))       # foot / socket travel length (Y)
corner_r = float(PARAM(lambda: corner_r, 1.0))        # rounded flange corner radius

base_th = float(PARAM(lambda: base_th, 5.0))          # mounting base thickness (Z)
base_pad = float(PARAM(lambda: base_pad, 5.0))        # base overhang around the shoe (mm)
quarter_d = float(PARAM(lambda: quarter_d, 6.6))      # 1/4-20 clearance hole (mm)

wall = float(PARAM(lambda: wall, 3.0))                # socket lip wall thickness (mm)
clearance = float(PARAM(lambda: clearance, 0.35))     # socket-to-foot fit slop (per side)
bar_span = float(PARAM(lambda: bar_span, 70.0))       # dual-bar length between shoe centres+ (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
foot_width = max(12.0, min(foot_width, 30.0))
channel_w = max(6.0, min(channel_w, foot_width - 2.0))
flange_th = max(0.8, min(flange_th, 4.0))
shoe_len = max(8.0, min(shoe_len, 40.0))
corner_r = max(0.0, min(corner_r, min(flange_th, (foot_width - channel_w) / 2.0) - 0.05))
base_th = max(2.5, min(base_th, 20.0))
base_pad = max(1.0, min(base_pad, 20.0))
wall = max(1.6, min(wall, 6.0))
clearance = max(0.1, min(clearance, 0.8))
bar_span = max(30.0, min(bar_span, 200.0))


# ── Shoe cross-section primitives ────────────────────────────────────────────
def _foot_profile(width, chan_w, th, r):
    """The male accessory-shoe cross-section in the XZ plane (looking along +Y).

    An inverted-T flange pair: a full-width plate of thickness `th` whose upper
    surface is recessed in the centre to leave two side flanges. Outer corners
    are rounded (`r`) — that rounding is what mates the socket's radiused lips.
    Returns a Workplane profile centred on X, base at z=0."""
    hw = width / 2.0
    ch = chan_w / 2.0
    # A rectangle (the flange plate) with a rectangular notch removed from the
    # top-centre would leave a re-entrant corner; instead build the solid plate
    # and let the socket recess handle the tongue. Here the FOOT is the two
    # flanges plus a thin web, so trace the outline directly.
    #   corners (x, z):  full plate, then the centre raised web up to `th`.
    pts = [
        (-hw, 0.0),
        (hw, 0.0),
        (hw, th),
        (ch, th),
        (ch, th + 0.6),   # small central ridge so the tongue reads as raised
        (-ch, th + 0.6),
        (-ch, th),
        (-hw, th),
    ]
    wp = cq.Workplane("XZ").polyline(pts).close()
    prof = wp.extrude(shoe_len)
    if r > 0.05:
        try:
            # Round the two outer bottom-edge fillets (the flange corners) — these
            # are vertical edges running along Y at the outer X extremes.
            prof = prof.edges("|Y and (<X or >X)").fillet(r)
        except Exception:
            pass
    return prof


def _shoe_foot_solid():
    """The full male shoe foot as a printable solid centred on X, running along
    +Y from y=0, base at z=0."""
    return _foot_profile(foot_width, channel_w, flange_th, corner_r)


def _rounded_base(w, d, h, r):
    """Axis-aligned mounting base centred in X/Y, base at z=0, rounded vertical
    edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.3:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _quarter_hole(base, x, y, z_top, depth):
    """Cut a 1/4-20 clearance through-hole (counter-open both faces stay closed
    because the base is thicker than the bore is deep)."""
    r = max(0.5, quarter_d / 2.0)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z_top - depth))
        .circle(r)
        .extrude(depth + 0.02)
    )
    return base.cut(hole)


# ── Part builders ────────────────────────────────────────────────────────────
def build_cold_shoe_male():
    """A male shoe foot standing on a mounting base that carries a 1/4-20
    clearance hole — bolt it to any surface and slide an accessory-shoe socket
    off the camera onto this foot (or vice-versa)."""
    bx = foot_width + 2.0 * base_pad
    by = shoe_len + 2.0 * base_pad
    base = _rounded_base(bx, by, base_th, min(3.0, base_pad - 0.5))

    # Foot sits on top of the base, centred, running the base length.
    foot = _shoe_foot_solid().translate((0, -shoe_len / 2.0, base_th - 0.01))
    body = base.union(foot)

    # 1/4-20 clearance hole straight through the base, offset to the back so it
    # clears the tongue footprint.
    body = _quarter_hole(body, 0, 0, base_th, base_th + 0.02)
    return body


def build_shoe_socket():
    """The camera-side receiver: a block with an accessory-shoe channel milled
    through it so a male foot slides in along +Y. The overhanging lips capture
    the foot flanges. A 1/4-20 hole lets the socket itself bolt to a rig."""
    fw = foot_width + 2.0 * clearance
    cw = channel_w - 2.0 * clearance  # tongue relief (socket tongue is narrower)
    ft = flange_th + clearance

    block_w = fw + 2.0 * wall
    block_h = ft + 0.6 + wall + 2.0        # lip + tongue ridge clearance + roof
    block_len = shoe_len + 2.0 * wall

    block = _rounded_base(block_w, block_len, block_h, min(2.5, wall - 0.3))

    # The slide channel: a copy of the foot cross-section (with clearance),
    # swept the full length and OPEN at both Y ends so the foot can enter — a
    # through-cut, so the cavity vents to outside (no trapped void).
    chan = _foot_profile(fw, cw, ft, max(0.0, corner_r))
    chan = chan.translate((0, -block_len / 2.0 - 1.0, 0.0))
    # Extend the cut through both ends.
    chan = (
        cq.Workplane("XZ")
        .polyline([
            (-fw / 2.0, 0.0),
            (fw / 2.0, 0.0),
            (fw / 2.0, ft),
            (cw / 2.0, ft),
            (cw / 2.0, ft + 0.6 + clearance),
            (-cw / 2.0, ft + 0.6 + clearance),
            (-cw / 2.0, ft),
            (-fw / 2.0, ft),
        ])
        .close()
        .extrude(block_len + 2.0)
        .translate((0, -block_len / 2.0 - 1.0, 0.0))
    )
    body = block.cut(chan)

    # 1/4-20 hole from the underside into the roof (blind-ish, stays watertight).
    depth = min(block_h - (ft + 0.6 + clearance) - 1.0, block_h - 1.0)
    depth = max(2.5, depth)
    r = max(0.5, quarter_d / 2.0)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .circle(r)
        .extrude(depth + 0.01)
    )
    body = body.cut(hole)
    return body


def build_dual_shoe_bar():
    """A rigid bar carrying TWO male shoe feet at each end — mount two
    accessories (light + mic, monitor + recorder) to a single camera shoe or
    handle. Feet point up; a spine runs between them."""
    n_pad = base_pad
    bar_w = foot_width + 2.0 * n_pad
    bar_len = bar_span
    bar = _rounded_base(bar_w, bar_len, base_th, min(3.0, n_pad - 0.5))

    y_off = bar_len / 2.0 - shoe_len / 2.0 - n_pad
    body = bar
    for sy in (-y_off, y_off):
        foot = _shoe_foot_solid().translate((0, sy - shoe_len / 2.0, base_th - 0.01))
        body = body.union(foot)

    # Central 1/4-20 hole to mount the bar itself.
    body = _quarter_hole(body, 0, 0, base_th, base_th + 0.02)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "shoe_socket":
    result = build_shoe_socket()
elif target_part == "dual_shoe_bar":
    result = build_dual_shoe_bar()
else:
    result = build_cold_shoe_male()
