"""
Cup-Holder Caddy Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Turns a car cup holder into a useful caddy. A tapered stem drops into the
cup-holder well (sized by `holder_dia`, with a gentle draft so it self-centres
and wedges), and a device platform sits on top carrying one of three payloads:

  * "phone_caddy"  — a single upright phone/device slot with a cable notch.
  * "coin_tray"    — a shallow multi-compartment tray for coins / change / keys.
  * "multi_caddy"  — a phone slot PLUS side pockets and pen bores (the combo).

The stem is the Common Denominator Geometry: any well within the taper's grip
range accepts any payload, so one interface fits thousands of vehicles.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `holder_dia`).
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


# ── Parameters ───────────────────────────────────────────────────────────────
holder_dia   = float(PARAM(lambda: holder_dia,   74.0))   # cup-holder well diameter (mm)
stem_depth   = float(PARAM(lambda: stem_depth,   45.0))   # how deep the stem sits in the well
taper        = float(PARAM(lambda: taper,         2.5))   # per-side draft over the stem depth (mm)
base_dia     = float(PARAM(lambda: base_dia,      0.0))   # platform diameter (0 = auto from holder_dia)
base_thick   = float(PARAM(lambda: base_thick,    4.0))   # platform slab thickness
wall         = float(PARAM(lambda: wall,          2.4))   # generic wall thickness

phone_thick  = float(PARAM(lambda: phone_thick,  14.0))   # phone/device slot width (with case)
phone_len    = float(PARAM(lambda: phone_len,    82.0))   # phone slot length (device width)
slot_height  = float(PARAM(lambda: slot_height,  40.0))   # how tall the upright slot walls are

coin_wells   = int(  PARAM(lambda: coin_wells,      3))   # compartments in the coin tray
tray_depth   = float(PARAM(lambda: tray_depth,   22.0))   # coin/pocket well depth

pen_holes    = int(  PARAM(lambda: pen_holes,       2))   # pen/stylus bores on the multi caddy
pen_dia      = float(PARAM(lambda: pen_dia,      12.0))   # pen bore diameter

target_part  = str(  PARAM(lambda: target_part, "phone_caddy"))
# "phone_caddy" | "coin_tray" | "multi_caddy"


# ── Derived / clamped geometry ───────────────────────────────────────────────
holder_dia = max(40.0, holder_dia)
# Stem grips the well: top radius = well radius, tapering IN toward the tip so it
# drops in and wedges. Keep a small clearance so it seats without jamming.
stem_top_r = holder_dia / 2.0 - 0.4
taper = max(0.0, min(taper, stem_top_r - 6.0))
stem_tip_r = max(4.0, stem_top_r - taper)

# Platform: default a hair larger than the well so it rests on the rim.
if base_dia <= 0.0:
    base_dia = holder_dia + 16.0
base_r = base_dia / 2.0
base_thick = max(2.0, base_thick)
wall = max(1.2, wall)


# ── Shared helper: tapered stem / bore (reused across the automotive set) ─────
def tapered_stem(bottom_r, top_r, height, z0=0.0):
    """A vertical frustum (circular taper) from z0 (radius bottom_r) up to
    z0+height (radius top_r). Built with two-circle loft; falls back to a plain
    cylinder if the loft degenerates. Watertight solid."""
    b = max(0.5, bottom_r)
    t = max(0.5, top_r)
    if abs(b - t) < 0.05:
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(b)
            .extrude(height)
        )
    try:
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(b)
            .workplane(offset=height)
            .circle(t)
            .loft(combine=True)
        )
    except Exception:
        r = (b + t) / 2.0
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(r)
            .extrude(height)
        )


def build_stem():
    """The cup-holder stem: tapered frustum below z=0 (tip is deepest), with a
    couple of relief flats/ribs omitted for print-simplicity. The platform sits
    on top at z:[0, base_thick]."""
    # Tip at z=-stem_depth (radius stem_tip_r), top at z=0 (radius stem_top_r).
    stem = tapered_stem(stem_tip_r, stem_top_r, stem_depth, z0=-stem_depth)
    # Lighten the stem with a blind bore from the bottom (saves plastic, still
    # watertight because it stops short of the platform).
    bore_r = max(0.0, stem_tip_r - wall)
    if bore_r > 2.0:
        bore_h = stem_depth - wall
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -stem_depth + 0.001))
            .circle(bore_r)
            .extrude(bore_h)
        )
        stem = stem.cut(bore)
    return stem


def build_platform():
    """Round platform slab resting on the well rim, top face at z=base_thick."""
    plate = (
        cq.Workplane("XY")
        .circle(base_r)
        .extrude(base_thick)
    )
    try:
        plate = plate.edges(">Z").fillet(min(1.5, base_thick * 0.4))
    except Exception:
        pass
    return plate


def _base_assembly():
    """Stem fused to platform — the shared substrate every payload builds on."""
    return build_stem().union(build_platform())


# ── Payload: phone caddy ──────────────────────────────────────────────────────
def build_phone_caddy():
    """Upright device slot on the platform: two tall walls forming a channel of
    width `phone_thick`, length `phone_len`, with a front cable notch."""
    body = _base_assembly()

    ch_l = min(phone_len, base_dia - 2.0 * wall)
    slot_w = max(6.0, phone_thick)
    outer_w = slot_w + 2.0 * wall
    z_top = base_thick + slot_height

    # Solid block that becomes the slot walls, then carve the channel.
    block = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick))
        .box(ch_l + 2.0 * wall, outer_w, slot_height, centered=(True, True, False))
    )
    try:
        block = block.edges("|Z").fillet(min(2.0, wall))
    except Exception:
        pass
    body = body.union(block)

    channel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick + wall))
        .box(ch_l, slot_w, slot_height, centered=(True, True, False))
    )
    body = body.cut(channel)

    # Front cable notch through one long wall (−Y face).
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -outer_w / 2.0, z_top - 12.0))
        .box(20.0, 3.0 * wall, 20.0, centered=(True, True, False))
    )
    body = body.cut(notch)
    return body


# ── Payload: coin tray ─────────────────────────────────────────────────────────
def build_coin_tray():
    """Shallow round tray on the platform, split into `coin_wells` pie/strip
    compartments by thin ribs — for coins, change, keys, receipts."""
    body = _base_assembly()

    tray_r = base_r - wall
    wall_h = min(tray_depth, 40.0)

    # Tray wall: a ring standing on the platform.
    ring_outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick))
        .circle(base_r)
        .extrude(wall_h)
    )
    ring_inner = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick + wall))
        .circle(tray_r)
        .extrude(wall_h)
    )
    body = body.union(ring_outer).cut(ring_inner)

    # Divider ribs (straight strips across the interior).
    n = max(0, min(coin_wells - 1, 5))
    if n > 0:
        span = 2.0 * tray_r
        step = span / (n + 1)
        for i in range(1, n + 1):
            x = -tray_r + i * step
            rib = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, 0, base_thick + wall))
                .box(max(1.2, wall * 0.8), 2.0 * tray_r, wall_h - wall,
                     centered=(True, True, False))
            )
            # Trim rib to the tray circle by intersecting with an inner disc.
            disc = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, base_thick + wall))
                .circle(tray_r)
                .extrude(wall_h)
            )
            body = body.union(rib.intersect(disc))
    return body


# ── Payload: multi caddy ────────────────────────────────────────────────────────
def build_multi_caddy():
    """Combo: a device slot down the middle, a small pocket to one side, and a
    row of pen/stylus bores. The everyday console organiser."""
    body = _base_assembly()

    z0 = base_thick
    box_h = min(slot_height, 44.0)
    outer_l = base_dia - 2.0 * wall

    # Outer shell block (rounded), then hollow two pockets + slot.
    shell = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .box(outer_l, base_dia - 2.0 * wall, box_h, centered=(True, True, False))
    )
    try:
        shell = shell.edges("|Z").fillet(min(3.0, wall + 1.0))
    except Exception:
        pass
    # Keep shell inside the round platform footprint.
    foot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(base_r)
        .extrude(box_h)
    )
    shell = shell.intersect(foot)
    body = body.union(shell)

    # Central phone slot.
    slot_w = max(6.0, phone_thick)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, base_dia * 0.14, z0 + wall))
        .box(min(phone_len, outer_l - 2.0 * wall), slot_w, box_h,
             centered=(True, True, False))
    )
    body = body.cut(slot)

    # Side pocket (opposite the slot).
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -base_dia * 0.24, z0 + wall))
        .box(outer_l * 0.5, base_dia * 0.22, box_h - wall,
             centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Pen bores along one edge.
    n = max(0, min(pen_holes, 4))
    if n > 0:
        pr = max(2.0, pen_dia / 2.0)
        span = outer_l * 0.6
        step = span / max(1, n)
        x0 = -span / 2.0 + step / 2.0
        for i in range(n):
            px = x0 + i * step
            bore = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(px, -base_dia * 0.36, z0 + wall))
                .circle(pr)
                .extrude(box_h)
            )
            body = body.cut(bore)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "coin_tray":
    result = build_coin_tray()
elif target_part == "multi_caddy":
    result = build_multi_caddy()
else:  # "phone_caddy"
    result = build_phone_caddy()
