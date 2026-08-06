"""
Battery Pad — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An anti-slip LiPo tray / pad for FPV & RC craft, with strap channels so the
battery strap seats flush and does not creep. Sized to the pack footprint. Three
modes: a flat grippy pad with strap slots, a walled tray that captures the pack,
and a wedge that tilts the pack to shift the centre of gravity.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pack_w`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
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
pack_w      = float(PARAM(lambda: pack_w,     35.0))   # battery pack width (X)
pack_l      = float(PARAM(lambda: pack_l,     70.0))   # battery pack length (Y)
strap_w     = float(PARAM(lambda: strap_w,    20.0))   # battery strap width
pad_thick   = float(PARAM(lambda: pad_thick,   3.0))   # base pad thickness
grip_depth  = float(PARAM(lambda: grip_depth,  1.2))   # anti-slip rib depth
grip_pitch  = float(PARAM(lambda: grip_pitch,  4.0))   # anti-slip rib pitch
margin      = float(PARAM(lambda: margin,      4.0))   # pad overhang beyond the pack
wall        = float(PARAM(lambda: wall,        2.5))   # tray wall thickness (tray mode)
wall_h      = float(PARAM(lambda: wall_h,     10.0))   # tray wall height (tray mode)
wedge_rise  = float(PARAM(lambda: wedge_rise, 12.0))   # rear rise of the wedge (wedge mode)

target_part = str(PARAM(lambda: target_part, "flat_pad"))
# "flat_pad" | "tray" | "wedge"


# ── Derived / clamped geometry ───────────────────────────────────────────────
pad_w = pack_w + 2.0 * margin
pad_l = pack_l + 2.0 * margin
strap_w = max(4.0, min(strap_w, pack_l - 4.0))     # strap must fit within footprint
n_straps = 2 if pack_l >= 45.0 else 1              # long packs get two straps


def _strap_channels(z_top, span_x, depth):
    """Recessed cross-channels (running in X) where the strap lies so it seats
    flush and cannot slide along the pack length. `z_top` is the surface the
    channel is cut into; the channel floor is `depth` below it."""
    cutter = None
    # Place straps at ~1/4 and ~3/4 along the length (or centre for a short pack).
    if n_straps == 1:
        ys = [0.0]
    else:
        ys = [-pack_l * 0.25, pack_l * 0.25]
    for y in ys:
        ch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, z_top - depth / 2.0))
            .box(span_x + 2.0, strap_w, depth + 0.02, centered=(True, True, True))
        )
        cutter = ch if cutter is None else cutter.union(ch)
    return cutter


def _grip_ribs(z_top, area_w, area_l):
    """Anti-slip ribs standing proud of the pad top: parallel bars in X spaced by
    `grip_pitch`, rising `grip_depth` above `z_top`. Keeps the pack from creeping
    under vibration."""
    ribs = None
    rib_w = max(0.8, grip_pitch * 0.45)
    count = max(1, int(area_l / grip_pitch))
    span = (count - 1) * grip_pitch
    y0 = -span / 2.0
    for i in range(count):
        y = y0 + i * grip_pitch
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, y, z_top + grip_depth / 2.0))
            .box(area_w, rib_w, grip_depth, centered=(True, True, True))
        )
        ribs = rib if ribs is None else ribs.union(rib)
    return ribs


def _base_pad(w, ln, t):
    """Rounded flat base slab, top at z=0, extends down to z=-t."""
    pad = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -t / 2.0))
        .box(w, ln, t, centered=(True, True, True))
    )
    try:
        pad = pad.edges("|Z").fillet(min(3.0, w / 2.0 - 0.5, ln / 2.0 - 0.5))
    except Exception:
        pass
    return pad


def build_flat_pad():
    """Grippy flat pad: base slab + anti-slip ribs on top, with strap channels
    recessed across the ribs so the strap lies flush."""
    pad = _base_pad(pad_w, pad_l, pad_thick)
    ribs = _grip_ribs(0.0, pack_w, pack_l)
    body = pad.union(ribs)
    # Cut strap channels through the rib field (down into the ribs + a little pad).
    ch = _strap_channels(grip_depth, pad_w, grip_depth + 0.8)
    body = body.cut(ch)
    return body


def build_tray():
    """Walled tray: a base pad with a raised perimeter wall capturing the pack,
    plus strap channels notched through the side walls so the strap wraps under."""
    pad = _base_pad(pad_w, pad_l, pad_thick)
    # Perimeter wall: outer box minus an inner pocket sized to the pack.
    wall_outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall_h / 2.0))
        .box(pad_w, pad_l, wall_h, centered=(True, True, True))
    )
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall_h / 2.0 + 0.5))
        .box(pack_w, pack_l, wall_h + 2.0, centered=(True, True, True))
    )
    walls = wall_outer.cut(pocket)
    body = pad.union(walls)
    # Strap notches through the side walls (X-direction slots at strap positions).
    ch = _strap_channels(wall_h, pad_w, wall_h - pad_thick + 0.5)
    # Only notch the walls, not the floor: limit channel to above the floor.
    body = body.cut(ch)
    # Grip ribs on the tray floor for extra hold.
    ribs = _grip_ribs(0.0, pack_w - 1.0, pack_l - 1.0)
    body = body.union(ribs)
    return body


def build_wedge():
    """Angled wedge: a triangular block that tilts the pack nose-down / tail-up to
    move the CG. The top surface is a ramp; strap channels follow the ramp."""
    # A wedge prism: rectangular base, rising linearly from front (y=-pad_l/2) to
    # rear (y=+pad_l/2) by `wedge_rise`. Build via a lofted/extruded profile.
    rise = max(2.0, wedge_rise)
    profile = (
        cq.Workplane("XZ")
        .polyline([
            (-pad_l / 2.0, 0.0),
            (pad_l / 2.0, 0.0),
            (pad_l / 2.0, pad_thick + rise),
            (-pad_l / 2.0, pad_thick),
        ])
        .close()
        .extrude(pad_w / 2.0, both=True)
    )
    # `profile` is built in XZ with Y = extrude direction; but we extruded along
    # normal (Y). Reorient so length runs along Y: the polyline used X for length,
    # so rotate 90 deg about Z to map that X-length onto Y.
    wedge = profile.rotate((0, 0, 0), (0, 0, 1), 90.0)
    try:
        wedge = wedge.edges("|Y").fillet(1.2)
    except Exception:
        pass
    # Strap channels across the ramp top. Cut simple X-slots near the top surface;
    # generous depth guarantees they open through the sloped face.
    ch = _strap_channels(pad_thick + rise, pad_w, rise * 0.5 + 1.5)
    wedge = wedge.cut(ch)
    return wedge


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tray":
    result = build_tray()
elif target_part == "wedge":
    result = build_wedge()
else:  # "flat_pad"
    result = build_flat_pad()
