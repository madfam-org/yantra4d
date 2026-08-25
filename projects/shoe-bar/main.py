"""
Cold-Shoe Extension Bar — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Multiplies a camera's single accessory shoe into several. The ISO 518 accessory
shoe — the ~18.7 mm-wide rail with rounded-corner flanges that every on-camera
light, microphone, monitor and flash slides onto — is the standard here. This bar
carries THREE male shoe feet plus 1/4-20 holes, so a rig can host a light, a mic
and a monitor at once. Every foot is the real ISO 518 shoe, so it mates any
accessory-shoe socket (e.g. the `shoe-mount` socket and dual bar).

ISO 518 accessory shoe geometry (nominal, dimensionally real):
  - overall foot width      ≈ 18.7 mm  (the "shoe" outer width)
  - channel / tongue width  ≈ 14.9 mm  (the recessed centre the flanges frame)
  - flange thickness (Z)    ≈ 1.6 mm    (the thin lip a socket grips)
  - flange rounded corners  ≈ 1.0 mm    radius on the outer edges
  - 1/4-20 UNC accessory holes ≈ 6.6 mm clearance.

Three modes (each geometrically distinct):
  - triple_shoe_bar : a bar with THREE male shoe feet + 1/4-20 holes.
  - shoe_relocator  : a short bar with a male foot on one end and a female shoe
                      socket on the other — moves a shoe to a new spot.
  - shoe_quarter_rail : one male shoe foot on a rail with a row of 1/4-20 holes.

Watertight strategy:
  Every part is built from extruded 2D shoe cross-sections (rounded flange corners
  live in the 2D profile, filleted before extrusion) and axis-aligned box unions
  that OVERLAP into shared material — no tangent kisses, no post-cut fillets on
  complex features. The socket channel is a through-cut (vents both Y ends);
  1/4-20 holes are through / open pockets that vent to outside.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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


# ── Parameters (ISO 518 accessory shoe) ──────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "triple_shoe_bar"))
# "triple_shoe_bar" | "shoe_relocator" | "shoe_quarter_rail"

foot_width = float(PARAM(lambda: foot_width, 18.7))   # ISO 518 outer shoe width (X)
channel_w = float(PARAM(lambda: channel_w, 14.9))     # recessed tongue width (X)
flange_th = float(PARAM(lambda: flange_th, 1.6))      # flange lip thickness (Z)
shoe_len = float(PARAM(lambda: shoe_len, 20.0))       # foot / socket travel length (Y)
corner_r = float(PARAM(lambda: corner_r, 1.0))        # rounded flange corner radius

base_th = float(PARAM(lambda: base_th, 5.0))          # bar/base thickness (Z)
base_pad = float(PARAM(lambda: base_pad, 5.0))        # base overhang around the shoe (mm)
quarter_d = float(PARAM(lambda: quarter_d, 6.6))      # 1/4-20 clearance hole (mm)

wall = float(PARAM(lambda: wall, 3.0))                # socket lip wall thickness (mm)
clearance = float(PARAM(lambda: clearance, 0.35))     # socket-to-foot fit slop (per side)
bar_span = float(PARAM(lambda: bar_span, 110.0))      # bar length (Y)

# Clamp to sane ranges so extreme UI values never crash the kernel.
foot_width = max(12.0, min(foot_width, 30.0))
channel_w = max(6.0, min(channel_w, foot_width - 2.0))
flange_th = max(0.8, min(flange_th, 4.0))
shoe_len = max(8.0, min(shoe_len, 40.0))
corner_r = max(0.0, min(corner_r, min(flange_th, (foot_width - channel_w) / 2.0) - 0.05))
base_th = max(2.5, min(base_th, 20.0))
base_pad = max(1.0, min(base_pad, 20.0))
quarter_d = max(3.0, min(quarter_d, 10.0))
wall = max(1.6, min(wall, 6.0))
clearance = max(0.1, min(clearance, 0.8))
bar_span = max(50.0, min(bar_span, 240.0))


# ── Shoe cross-section primitives ────────────────────────────────────────────
def _foot_profile(width, chan_w, th, r, length):
    """The male accessory-shoe cross-section (XZ, along +Y): a full-width flange
    plate with a raised central tongue, outer corners rounded. Base at z=0."""
    hw = width / 2.0
    ch = chan_w / 2.0
    pts = [
        (-hw, 0.0),
        (hw, 0.0),
        (hw, th),
        (ch, th),
        (ch, th + 0.6),
        (-ch, th + 0.6),
        (-ch, th),
        (-hw, th),
    ]
    # Extrude symmetrically so the foot is CENTRED on Y=0 (span -length/2..+length/2),
    # independent of the XZ plane's extrude sign — callers place it by its centre.
    prof = cq.Workplane("XZ").polyline(pts).close().extrude(length / 2.0, both=True)
    if r > 0.05:
        try:
            prof = prof.edges("|Y and (<X or >X)").fillet(r)
        except Exception:
            pass
    return prof


def _shoe_foot_solid():
    """A male shoe foot centred on X AND Y (span -shoe_len/2..+shoe_len/2), base at
    z=0. Callers translate by the desired Y centre."""
    return _foot_profile(foot_width, channel_w, flange_th, corner_r, shoe_len)


def _rounded_base(w, d, h, r):
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.3:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


def _quarter_hole(base, x, y, z_top, depth):
    r = max(0.5, quarter_d / 2.0)
    hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z_top - depth))
        .circle(r)
        .extrude(depth + 0.02)
    )
    return base.cut(hole)


# ── Part builders ────────────────────────────────────────────────────────────
def build_triple_shoe_bar():
    """A bar carrying THREE male shoe feet along its length plus 1/4-20 holes
    between them — rig three accessories onto one camera shoe or handle."""
    bar_w = foot_width + 2.0 * base_pad
    bar_len = bar_span
    body = _rounded_base(bar_w, bar_len, base_th, min(3.0, base_pad - 0.5))

    y_end = bar_len / 2.0 - shoe_len / 2.0 - base_pad
    positions = [-y_end, 0.0, y_end]
    for sy in positions:
        foot = _shoe_foot_solid().translate((0, sy, base_th - 0.01))
        body = body.union(foot)

    # 1/4-20 holes in the gaps between adjacent feet (through the bar).
    for i in range(len(positions) - 1):
        hy = (positions[i] + positions[i + 1]) / 2.0
        body = _quarter_hole(body, 0.0, hy, base_th, base_th + 0.02)
    return body


def build_shoe_relocator():
    """A short bar with a MALE foot on one end (slides into the camera shoe) and
    a FEMALE shoe socket on the other (an accessory slides in) — relocates a shoe
    to a more convenient spot."""
    bar_w = foot_width + 2.0 * base_pad
    # Socket dimensions.
    fw = foot_width + 2.0 * clearance
    cw = channel_w - 2.0 * clearance
    ft = flange_th + clearance
    socket_h = ft + 0.6 + wall + 2.0
    socket_len = shoe_len + 2.0 * wall

    # Bar long enough to seat the foot and the socket with margin between them.
    bar_len = socket_len + shoe_len + 3.0 * base_pad
    body = _rounded_base(bar_w, bar_len, base_th, min(3.0, base_pad - 0.5))

    # Male foot near the -Y end, CENTRED on the bar (fully seated, real overlap).
    foot_cy = -bar_len / 2.0 + base_pad + shoe_len / 2.0
    foot = _shoe_foot_solid().translate((0, foot_cy, base_th - 0.01))
    body = body.union(foot)

    # Female socket block near the +Y end, on top of the bar.
    sock_cy = bar_len / 2.0 - socket_len / 2.0 - base_pad
    block = _rounded_base(fw + 2.0 * wall, socket_len, socket_h, min(2.5, wall - 0.3))
    block = block.translate((0, sock_cy, base_th - 0.01))
    body = body.union(block)

    # Slide channel through the socket block (through-cut both Y ends → vented).
    # Extrude SYMMETRICALLY (both=True) and centre it on the socket at sock_cy so
    # the cut is direction-independent and never severs the socket from the bar.
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
        .extrude((socket_len + 2.0) / 2.0, both=True)
        .translate((0, sock_cy, base_th - 0.01))
    )
    body = body.cut(chan)
    return body


def build_shoe_quarter_rail():
    """One male shoe foot on a rail with a row of 1/4-20 holes — mix a shoe with
    screw-mounted accessories along the rail."""
    bar_w = foot_width + 2.0 * base_pad
    bar_len = bar_span
    body = _rounded_base(bar_w, bar_len, base_th, min(3.0, base_pad - 0.5))

    # Male foot near the -Y end, CENTRED on the bar (fully seated, real overlap).
    foot_cy = -bar_len / 2.0 + base_pad + shoe_len / 2.0
    foot = _shoe_foot_solid().translate((0, foot_cy, base_th - 0.01))
    body = body.union(foot)

    # A row of 1/4-20 holes along the remaining rail (through the bar).
    first = foot_cy + shoe_len / 2.0 + 8.0
    last = bar_len / 2.0 - base_pad
    span = last - first
    n = max(2, int(span // 15.0) + 1)
    if n > 1 and span > 0:
        for i in range(n):
            hy = first + span * i / (n - 1)
            body = _quarter_hole(body, 0.0, hy, base_th, base_th + 0.02)
    else:
        body = _quarter_hole(body, 0.0, (first + last) / 2.0, base_th, base_th + 0.02)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "shoe_relocator":
    result = build_shoe_relocator()
elif target_part == "shoe_quarter_rail":
    result = build_shoe_quarter_rail()
else:  # "triple_shoe_bar"
    result = build_triple_shoe_bar()
