"""
Opener Aid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Grip aids that give leverage and a non-slip hold to hands with limited strength
(arthritis, weak grip). A stepped cone drops over round jar/bottle lids across a
range of diameters; a lever pries bottle caps; a small tool lifts stubborn can
tabs.

  * "jar_opener"    — an inverted stepped cone whose internal steps grip several
                      lid diameters, with a fluted outer wall for the hand
                      (target_part == "jar_opener").
  * "bottle_opener" — a flat lever with a crown-cap catch and a big finger hole
                      (target_part == "bottle_opener").
  * "tab_opener"    — a small hooked lever that slips under a ring-pull can tab
                      (target_part == "tab_opener").

Watertight strategy: the jar cone is a solid stepped frustum with one stepped
bore removed; the lever and tab tools are single extruded profiles with holes
cut straight through. Every result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

These are printable everyday-living AIDS, not certified medical devices.
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
target_part = str(PARAM(lambda: target_part, "jar_opener"))  # jar_opener | bottle_opener | tab_opener

lid_min   = float(PARAM(lambda: lid_min,   40.0))   # smallest lid diameter gripped (mm)
lid_max   = float(PARAM(lambda: lid_max,   85.0))   # largest lid diameter gripped (mm)
steps     = int(  PARAM(lambda: steps,        4))   # number of grip steps in the cone
wall      = float(PARAM(lambda: wall,       4.0))   # cone / tool wall thickness
grip_h    = float(PARAM(lambda: grip_h,    16.0))   # height per step (grip depth)
flutes    = int(  PARAM(lambda: flutes,      12))   # outer hand-grip flutes (0 = smooth)
lever_len = float(PARAM(lambda: lever_len, 95.0))   # bottle-opener / tab lever length

# ── Clamps ───────────────────────────────────────────────────────────────────
lid_min   = max(20.0, min(lid_min, 120.0))
lid_max   = max(lid_min + 10.0, min(lid_max, 160.0))
steps     = max(2, min(steps, 6))
wall      = max(2.5, min(wall, 8.0))
grip_h    = max(8.0, min(grip_h, 30.0))
flutes    = max(0, min(flutes, 40))
lever_len = max(50.0, min(lever_len, 160.0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_jar_opener():
    """A stepped inverted cone. Outer wall is a smooth frustum (widest at the
    open bottom); the inside is a stack of cylindrical steps from lid_max at the
    bottom up to lid_min at the top so it seats on whatever lid it meets. The
    inner step wall grips the lid rim; the fluted outer wall is the handhold."""
    total_h = steps * grip_h
    r_bot = lid_max / 2.0 + wall
    r_top = lid_min / 2.0 + wall
    # Outer frustum (a clean loft, watertight, no axis pole).
    outer = (
        cq.Workplane("XY")
        .circle(r_bot)
        .workplane(offset=total_h)
        .circle(r_top)
        .loft(combine=True)
    )
    # Closed top web so the tool caps the lid and applies downward pressure.
    body = outer

    # Interior stepped bore: cut cylinders of decreasing diameter, bottom→top.
    for i in range(steps):
        # step i spans z in [i*grip_h, (i+1)*grip_h]; diameter decreases upward.
        t = i / max(1, steps - 1)
        d = lid_max + (lid_min - lid_max) * t
        cutter = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, i * grip_h))
            .circle(d / 2.0)
            .extrude(grip_h + (0.0 if i == steps - 1 else 0.1))
        )
        body = body.cut(cutter)

    # Fluted grip on the outside for the hand.
    if flutes > 0:
        try:
            cutter = (
                cq.Workplane("XY")
                .polarArray(radius=r_bot, startAngle=0, angle=360, count=flutes)
                .rect(2.4, 6.0)
                .extrude(total_h + 2.0)
                .translate((0, 0, -1.0))
            )
            body = body.cut(cutter)
        except Exception:
            pass
    return body


def build_bottle_opener():
    """A flat comfort lever: a rounded bar with a large finger hole for leverage
    and a crown-cap catch notch at the working end."""
    th = wall + 2.0
    w = 34.0
    body = (
        cq.Workplane("XY")
        .moveTo(-w / 2.0, 0)
        .threePointArc((0, w / 2.0), (w / 2.0, 0))
        .lineTo(w / 2.0, -(lever_len - w))
        .threePointArc((0, -(lever_len - w) - w / 2.0 * 0.6), (-w / 2.0, -(lever_len - w)))
        .close()
        .extrude(th)
    )
    # Big finger hole near the tail for grip/leverage.
    finger = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -(lever_len - w) + 4.0, 0))
        .circle(w * 0.32)
        .extrude(th + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(finger)
    # Crown-cap catch: a lip cut at the working head.
    catch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, w * 0.18, 0))
        .circle(15.0)
        .extrude(th + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(catch)
    # A short tooth to bite the cap edge: leave a stub by re-adding a small block.
    tooth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, w * 0.18 - 15.0 + 1.6, 0))
        .box(9.0, 3.2, th, centered=(True, True, False))
    )
    body = body.union(tooth)
    return body


def build_tab_opener():
    """A small hooked lever to lift ring-pull can tabs: a comfortable barrel
    handle with a thin angled hook at the tip that slides under the tab."""
    handle_r = 9.0
    handle_l = lever_len * 0.55
    handle = (
        cq.Workplane("YZ")
        .circle(handle_r)
        .extrude(handle_l)
    )
    # Thin blade extending from the handle end.
    blade_l = lever_len * 0.45
    blade = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, handle_l, 0))
        .box(6.0, blade_l, 3.2, centered=(True, False, True))
    )
    # Hook at the blade tip (a small up-turned lip).
    hook = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, handle_l + blade_l - 2.0, 0))
        .box(6.0, 2.5, 7.0, centered=(True, False, False))
    )
    body = handle.union(blade).union(hook)
    # Flutes on the handle for grip.
    if flutes > 0:
        try:
            cutter = (
                cq.Workplane("YZ")
                .polarArray(radius=handle_r, startAngle=0, angle=360, count=max(6, flutes))
                .rect(1.8, 4.0)
                .extrude(handle_l - 2.0)
            )
            body = body.cut(cutter)
        except Exception:
            pass
    # Round the handle butt.
    try:
        body = body.faces("<Y").edges().fillet(2.0)
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bottle_opener":
    result = build_bottle_opener()
elif target_part == "tab_opener":
    result = build_tab_opener()
else:  # "jar_opener"
    result = build_jar_opener()
