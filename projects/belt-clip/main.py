"""
Belt Clip / Holster — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Belt-worn carry hardware sized to a real belt width. A sprung belt clip that
snaps over the belt, a pocket holster with an integral belt loop, and a bare
belt loop you can graft onto anything. Everything is a single watertight solid
built by cutting cavities and a webbing slot from a rounded block; the clip's
spring is a printed compliant arm freed by a U-slot (no separate parts).

Modes (dispatched via `target_part`):
  * "clip"      — a spring belt clip: a back plate with a curved sprung tongue
                  that hooks over the belt's top edge and grips it.
  * "holster"   — a device pocket with an integral belt loop on the back.
  * "belt_loop" — just the belt loop (the shared webbing-slot interface).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `belt_w`).
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
belt_w      = float(PARAM(lambda: belt_w,      38.0))   # belt WIDTH the clip/loop rides (mm)
belt_t      = float(PARAM(lambda: belt_t,       4.0))   # belt THICKNESS (leather ~3-5mm)
wall        = float(PARAM(lambda: wall,         3.0))   # structural wall thickness (mm)
pocket_w    = float(PARAM(lambda: pocket_w,    62.0))   # holster pocket interior width (mm)
pocket_d    = float(PARAM(lambda: pocket_d,    16.0))   # holster pocket interior depth (mm)
pocket_h    = float(PARAM(lambda: pocket_h,    90.0))   # holster pocket interior height (mm)
clip_reach  = float(PARAM(lambda: clip_reach,  46.0))   # how far the clip tongue reaches down (mm)
clip_clear  = float(PARAM(lambda: clip_clear,   0.6))   # tongue-to-plate gap = belt bite clearance
loop_clear  = float(PARAM(lambda: loop_clear,   1.5))   # belt clearance inside the loop (mm)

target_part = str(  PARAM(lambda: target_part, "clip"))  # clip | holster | belt_loop

# ── Safe clamps ──────────────────────────────────────────────────────────────
belt_w     = max(15.0, min(belt_w, 75.0))
belt_t     = max(1.5, min(belt_t, 8.0))
wall       = max(2.0, min(wall, 6.0))
pocket_w   = max(20.0, min(pocket_w, 140.0))
pocket_d   = max(6.0, min(pocket_d, 60.0))
pocket_h   = max(25.0, min(pocket_h, 200.0))
clip_reach = max(20.0, min(clip_reach, 80.0))


# ── Shared webbing/belt-slot helper ──────────────────────────────────────────
def webbing_slot(width, thickness, length, clearance):
    """A rounded-rectangle prism sized to a strap/belt cross-section, oriented so
    its long dimension (the strap WIDTH) runs along Y and its through-length runs
    along Z. Cut this from a block to form a belt loop / webbing pass-through.

    Returns a cq.Workplane solid centred on the origin. `clearance` is added to
    both cross-section dimensions so the belt slides through. Reused across the
    belt-clip, strap-buckle and other slotted parts so every pass-through shares
    one geometry definition."""
    w = width + clearance          # strap width span (Y)
    t = thickness + clearance      # strap thickness span (X)
    r = min(t / 2.0 - 0.01, 2.0)
    slot = cq.Workplane("XY").box(t, w, length, centered=(True, True, True))
    if r > 0.05:
        try:
            slot = slot.edges("|Z").fillet(r)
        except Exception:
            pass
    return slot


def rounded_block(w, d, h, r):
    """Axis-aligned block on XY (base at z=0), optional rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass
    return wp


# ── Part builders ─────────────────────────────────────────────────────────────
def build_clip():
    """Spring belt clip: a flat back plate carrying the load, and a curved sprung
    tongue standing off the plate by (belt_t + clip_clear). The belt slides into
    that gap; the printed tongue root acts as a living hinge and pinches the belt
    against the plate. The tongue tip curls inward to hook the belt's top edge.
    One continuous watertight solid — the tongue is unioned to the plate top."""
    plate_w = belt_w + 2.0 * wall
    plate_h = clip_reach + belt_w * 0.4      # plate taller than the tongue reach
    gap = belt_t + clip_clear                # standoff = belt bite

    # Back plate: sits in the X=0 plane, spans Y (width) and Z (height).
    plate = (
        cq.Workplane("XY")
        .box(wall, plate_w, plate_h, centered=(True, True, False))
    )
    try:
        plate = plate.edges("|X").fillet(min(wall, 2.0))
    except Exception:
        pass

    # Tongue: a thin panel offset in +X by `gap`, hanging down from the top.
    tongue_t = max(1.6, wall - 1.0)
    tongue_x = gap + tongue_t / 2.0
    tongue = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(tongue_x, 0, plate_h - clip_reach))
        .box(tongue_t, belt_w, clip_reach, centered=(True, True, False))
    )
    # Curl the tongue tip toward the plate (a small inward lip that catches the
    # belt edge). Modelled as a wedge bridging from tongue tip toward the plate.
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(gap / 2.0 + tongue_t / 2.0, 0, plate_h - clip_reach))
        .box(gap, belt_w, tongue_t, centered=(True, True, False))
    )

    # Bridge the tongue to the plate across the top edge (the spring root).
    root = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(gap / 2.0, 0, plate_h - tongue_t))
        .box(gap + tongue_t, belt_w, tongue_t, centered=(True, True, False))
    )

    body = plate.union(root).union(tongue).union(lip)

    # Grip ribs on the inner face of the tongue for belt bite.
    for i in range(3):
        zc = plate_h - clip_reach + clip_reach * (0.25 + 0.22 * i)
        rib = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(gap - 0.4, 0, zc))
            .box(1.4, belt_w * 0.9, 1.6, centered=(True, True, True))
        )
        body = body.union(rib)
    return body


def build_holster():
    """A device pocket (open-top box) with an integral belt loop on the back.
    Solid outer, cavity cut from the top, belt loop formed by a back web with a
    webbing slot through it."""
    outer_w = pocket_w + 2.0 * wall
    outer_d = pocket_d + 2.0 * wall
    outer_h = pocket_h + wall
    body = rounded_block(outer_w, outer_d, outer_h, min(wall * 1.5, 6.0))

    # Pocket cavity from the top (leave a floor of `wall`).
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, wall))
        .box(pocket_w, pocket_d, pocket_h + 1.0, centered=(True, True, False))
    )
    try:
        cavity = cavity.edges("|Z").fillet(min(pocket_d * 0.25, 4.0))
    except Exception:
        pass
    body = body.cut(cavity)

    # Belt loop: a web slab on the -Y face, standing off to make a tunnel.
    tunnel = belt_t + loop_clear
    web_t = wall
    loop_span = belt_w + 2.0 * wall
    loop_y = -outer_d / 2.0 - (tunnel + web_t) / 2.0
    loop_z = outer_h * 0.62
    loop = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, loop_y, loop_z - loop_span / 2.0))
        .box(tunnel + 2.0 * web_t, loop_span, loop_span, centered=(True, False, False))
    )
    # Fuse the loop back to the body with side cheeks so the tunnel is enclosed.
    for sy in (-1.0, 1.0):
        cheek = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, loop_z - loop_span / 2.0))
            .box(outer_d + tunnel + 2.0 * web_t, web_t, loop_span, centered=(True, False, False))
            .translate((0, sy * (belt_w / 2.0 + web_t / 2.0), 0))
        )
        body = body.union(cheek)
    body = body.union(loop)

    # Belt pass-through: cut the tunnel through the loop so the belt runs
    # vertically (Z) between the loop web and the pocket back. Sized to the belt
    # cross-section with loop_clear (same sizing rule as the webbing-slot helper).
    tunnel_cut = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, loop_y, loop_z - loop_span / 2.0 - 2.0))
        .box(tunnel, belt_w + loop_clear, loop_span + 6.0, centered=(True, True, False))
    )
    body = body.cut(tunnel_cut)
    return body


def build_belt_loop():
    """The bare belt loop: a rectangular tube sized to the belt cross-section via
    the shared webbing-slot helper, with mounting screw holes on the back face so
    it can be grafted onto any carry object."""
    tunnel = belt_t + loop_clear
    span = belt_w + 2.0 * wall
    depth = tunnel + 2.0 * wall
    height = span

    body = rounded_block(depth, span, height, min(wall, 2.5))
    # Hollow the belt channel with the shared helper (belt runs along Z).
    channel = webbing_slot(belt_w, belt_t, height + 4.0, loop_clear)
    channel = channel.translate((0, 0, height / 2.0))
    body = body.cut(channel)

    # Two mounting holes through the back wall (X direction), for screws.
    for sz in (-1.0, 1.0):
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, height / 2.0 + sz * height * 0.28, 0))
            .cylinder(depth + 4.0, 2.1)
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "holster":
    result = build_holster()
elif target_part == "belt_loop":
    result = build_belt_loop()
else:
    result = build_clip()
