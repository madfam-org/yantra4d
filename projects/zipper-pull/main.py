"""
Zipper Pull & Cord Ends — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Replacement zipper pulls and cord ends. A flat pull tab with a slider loop that
threads onto a zipper slider, a cord end / aglet that crimps onto paracord, and a
teardrop loop pull for cord zippers. Every part is one watertight solid built by
cutting a loop/channel from a rounded body.

Modes (dispatched via `target_part`):
  * "pull_tab"  — a flat grip tab with a small slider loop at one end.
  * "cord_end"  — a barrel aglet with a cord bore and a grip taper (paracord end).
  * "loop_pull" — a teardrop loop that a length of cord passes through, for cord
                  zippers and drawstrings.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `loop_dia`).
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
loop_dia    = float(PARAM(lambda: loop_dia,    5.0))    # slider-loop inner diameter (mm)
grip_len    = float(PARAM(lambda: grip_len,   26.0))    # grip / tab length (mm)
grip_w      = float(PARAM(lambda: grip_w,      9.0))    # grip width (mm)
thick       = float(PARAM(lambda: thick,       3.0))    # part thickness (mm)
cord_dia    = float(PARAM(lambda: cord_dia,    4.0))    # cord diameter for cord parts (mm)

target_part = str(  PARAM(lambda: target_part, "pull_tab"))  # pull_tab|cord_end|loop_pull

# ── Safe clamps ──────────────────────────────────────────────────────────────
loop_dia = max(2.0, min(loop_dia, 12.0))
grip_len = max(10.0, min(grip_len, 60.0))
grip_w   = max(5.0, min(grip_w, 20.0))
thick    = max(2.0, min(thick, 8.0))
cord_dia = max(1.5, min(cord_dia, 8.0))
loop_wall = max(1.4, thick * 0.6)   # ring wall around the slider loop


# ── Helpers ───────────────────────────────────────────────────────────────────
def rounded_bar(length, width, t, r):
    """A flat rounded-rect bar on XY (base z=0), long axis X, centred in X/Y."""
    bar = cq.Workplane("XY").box(length, width, t, centered=(True, True, False))
    r = max(0.0, min(r, width / 2.0 - 0.01))
    if r > 0.05:
        try:
            bar = bar.edges("|Z").fillet(r)
        except Exception:
            pass
    return bar


def slider_loop(inner_d, wall, t):
    """A flat ring (the zipper-slider loop): outer disc minus inner hole, extruded
    to thickness `t`. Centred on origin, base at z=0. This is the shared CDG
    interface that threads onto a zipper slider's pin."""
    outer = (inner_d + 2.0 * wall)
    ring = cq.Workplane("XY").circle(outer / 2.0).extrude(t)
    hole = cq.Workplane("XY").circle(inner_d / 2.0).extrude(t + 2.0).translate((0, 0, -1.0))
    return ring.cut(hole), outer


# ── Part builders ─────────────────────────────────────────────────────────────
def build_pull_tab():
    """A flat grip tab with a slider loop fused at the -X end. The tab widens the
    grip; the loop threads onto the zipper slider. One watertight solid."""
    ring, outer = slider_loop(loop_dia, loop_wall, thick)
    # Place the ring at the -X end; the tab body starts where the ring ends.
    ring_x = -grip_len / 2.0
    ring = ring.translate((ring_x, 0, 0))

    tab = rounded_bar(grip_len, grip_w, thick, min(grip_w * 0.35, 4.0))
    # Neck bridging tab to ring so they fuse cleanly.
    neck = rounded_bar(outer, min(grip_w * 0.7, outer), thick, 1.0)
    neck = neck.translate((ring_x + outer / 2.0, 0, 0))
    body = tab.union(neck).union(ring)

    # A grip hole / finger notch near the +X end for purchase.
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(grip_len / 2.0 - grip_w * 0.5, 0, 0))
        .slot2D(min(grip_len * 0.4, 12.0), max(2.0, grip_w * 0.3), 0)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(notch)
    return body


def build_cord_end():
    """A cord-end aglet: a tapered barrel with an axial cord bore, topped by a
    flat ear with a small hang hole. So paracord threads up the bore and the ear
    lets it clip to a slider or lanyard. One watertight solid, cord runs along Z.

    The ear is a flat plate whose base overlaps the barrel top (a solid volumetric
    fuse, not a tangent kiss) before its hang hole is cut — this keeps the union
    manifold and watertight."""
    h = grip_len * 0.7
    r_big = max(cord_dia * 0.8 + loop_wall, grip_w * 0.5)
    r_small = max(cord_dia * 0.6 + 1.2, r_big * 0.55)

    # Tapered barrel via loft between two circles.
    barrel = (
        cq.Workplane("XY")
        .circle(r_big)
        .workplane(offset=h)
        .circle(r_small)
        .loft(combine=True)
    )
    # Axial cord bore.
    bore = cq.Workplane("XY").circle(cord_dia / 2.0 + 0.3).extrude(h + 2.0).translate((0, 0, -1.0))
    body = barrel.cut(bore)

    # Flat hang ear rising from the barrel top. A rounded slab in the XZ plane,
    # its lower part sunk into the barrel so the fuse is solid.
    ear_w = max(2.0 * r_small, loop_dia + 2.0 * loop_wall)
    ear_h = loop_dia + 2.0 * loop_wall + 2.0
    ear_t = max(2.0, min(thick, 2.0 * r_small))
    ear = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h + ear_h / 2.0 - 2.0, 0))
        .box(ear_w, ear_h, ear_t)
    )
    try:
        ear = ear.edges("|Y").fillet(min(ear_w, ear_h) * 0.2)
    except Exception:
        pass
    body = body.union(ear)

    # Hang hole through the ear (along Y), above the barrel.
    hole = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h + ear_h - loop_dia / 2.0 - loop_wall, 0))
        .cylinder(ear_t + 2.0, loop_dia / 2.0)
    )
    body = body.cut(hole)
    return body


def build_loop_pull():
    """A teardrop loop pull: a flat teardrop plate with a large through-hole the
    cord passes through, and a rounded grip end. For cord zippers / drawstrings.
    One watertight solid."""
    length = grip_len
    width = grip_w * 1.6
    # Teardrop = a circle (grip end, +X) blended into a narrower tail (-X, the
    # cord loop end). Build as union of a disc and a tapered bar.
    disc_r = width / 2.0
    disc = cq.Workplane("XY").center(length / 2.0 - disc_r, 0).circle(disc_r).extrude(thick)
    tail = rounded_bar(length, width * 0.55, thick, width * 0.25)
    body = disc.union(tail)

    # Big cord through-hole near the -X (tail) end.
    hole_r = max(cord_dia * 0.7, (width * 0.55) / 2.0 - loop_wall)
    hole = (
        cq.Workplane("XY")
        .center(-length / 2.0 + hole_r + loop_wall, 0)
        .circle(hole_r)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(hole)

    # Finger hole in the grip disc.
    grip_hole = (
        cq.Workplane("XY")
        .center(length / 2.0 - disc_r, 0)
        .circle(disc_r * 0.5)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(grip_hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cord_end":
    result = build_cord_end()
elif target_part == "loop_pull":
    result = build_loop_pull()
else:
    result = build_pull_tab()
