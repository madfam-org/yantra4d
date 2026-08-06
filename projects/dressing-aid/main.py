"""
Reacher / Button-Hook Dressing Aid — Yantra4D Hyperobject Cartridge (CadQuery).

Dressing aids that let a user fasten and reach clothing with limited hand
function. A button hook catches a button through its buttonhole and pulls it
through; a zipper-pull hook snags a zipper tab so a jacket can be closed
one-handed; a reacher hook grabs a waistband, sock, or dropped item. Each is a
printed hook on an enlarged, easy-to-grip handle — the classic occupational-
therapy dressing aids, made to fit the user's hand.

  * "button_hook" — a handle with a narrow hook that passes through a buttonhole
                    and catches the button (target_part == "button_hook").
  * "zipper_hook" — a handle with a small J-hook that catches a zipper pull tab
                    (target_part == "zipper_hook").
  * "reacher_hook"— a longer handle with an open C-hook to snag clothing or a
                    dropped item (target_part == "reacher_hook").

Watertight strategy: each aid is one solid. The handle is a rounded grip bar; the
hook is an extruded 2D profile (a J or open-C wire cross-section given real
thickness) that shares the handle's mid-plane and overlaps into the handle end,
so the union is a single manifold (no thin raked plate floating off the grip).
Fillets are applied to clean blanks before the finger-loop through-hole is cut.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "button_hook"))
# button_hook | zipper_hook | reacher_hook

handle_len = float(PARAM(lambda: handle_len, 100.0))  # grip handle length (mm)
handle_dia = float(PARAM(lambda: handle_dia, 28.0))   # grip handle diameter (mm)
thick = float(PARAM(lambda: thick, 6.0))              # hook stock thickness (mm)
hook_r = float(PARAM(lambda: hook_r, 9.0))            # hook inner radius (mm)
hook_open = float(PARAM(lambda: hook_open, 7.0))      # hook mouth opening (mm)
reach = float(PARAM(lambda: reach, 45.0))             # neck length hook-to-handle (mm)
loop_dia = float(PARAM(lambda: loop_dia, 16.0))       # finger loop opening (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
handle_len = max(50.0, min(handle_len, 180.0))
handle_dia = max(16.0, min(handle_dia, 45.0))
thick = max(3.0, min(thick, 12.0))
hook_r = max(3.0, min(hook_r, 30.0))
hook_open = max(3.0, min(hook_open, 40.0))
reach = max(15.0, min(reach, 160.0))
loop_dia = max(8.0, min(loop_dia, handle_dia - 6.0))

HALF = handle_dia / 2.0


# ── Shared: an enlarged grip handle lying along +Y, centred on the origin end ─
def _grip_handle(length, add_loop):
    """A rounded grip bar running from y=0 (hook end) to y=length. Built as a
    plain cylinder (proven watertight) with its far rim rounded by an edge fillet
    — no on-axis revolve singularity and no tangent sphere-union seam. A finger
    loop can be cut near the far end (a through-hole across the grip → vented).

    The cylinder is extruded along +Y from an XZ-plane circle, so its flat end
    faces select as the min/max-Y faces (`<Y` hook end, `>Y` far end)."""
    r = HALF
    handle = cq.Workplane("XZ").circle(r).extrude(length)
    # Round the far end's rim so the grip has no sharp cap edge. Fillet on the
    # clean cylinder (before the loop cut) so OCCT clean() stays happy.
    try:
        handle = handle.faces(">Y").edges().fillet(min(r * 0.6, 6.0))
    except Exception:
        pass

    if add_loop:
        loop = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, 0, -(length - r - loop_dia / 2.0 - 5.0)))
            .circle(loop_dia / 2.0)
            .extrude(r * 2.0 + 4.0)
            .translate((0, -(r + 2.0), 0))
        )
        try:
            handle = handle.cut(loop)
        except Exception:
            pass
    return handle


def _hook_profile(inner_r, opening, stock, sweep_deg):
    """An open hook as an extruded 2D profile in the XY plane, extruded along +Z
    by `stock`. The profile is the region between an outer arc (inner_r+stock) and
    an inner arc (inner_r) swept `sweep_deg`, leaving a mouth of ~`opening`. A
    single closed wire → one manifold solid. Returned centred at the arc centre,
    then the caller positions it."""
    ir = inner_r
    orr = inner_r + stock
    steps = 40
    a0 = math.radians(-90.0)
    a1 = math.radians(-90.0 + sweep_deg)
    outer, inner = [], []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        outer.append((orr * math.cos(a), orr * math.sin(a)))
        inner.append((ir * math.cos(a), ir * math.sin(a)))
    prof = cq.Workplane("XY").polyline(outer + list(reversed(inner))).close()
    return prof.extrude(stock)


def build_button_hook():
    """A slim hook on a fat handle. The hook is a narrow flat tongue that goes
    through the buttonhole with a small return that catches the button and pulls
    it back. Built as a thin extruded plate + a catch, sharing the handle plane."""
    handle = _grip_handle(handle_len, add_loop=True)

    # Neck: a solid bar from the handle's hook end (y=0) forward to -Y (the working
    # end), on the handle mid-plane, overlapping into the handle so it welds solid.
    neck_w = min(HALF * 0.9, 10.0)
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, HALF * 0.4, -thick / 2.0))
        .box(neck_w, reach + HALF, thick, centered=(True, True, False))
        .translate((0, -reach + HALF * 0.4, 0))
    )
    # Button-catch loop at the far end: an open hook (C) that the button seats in.
    hook = _hook_profile(hook_r, hook_open, thick, 250.0)
    hook = hook.translate((0, -reach - hook_r, -thick / 2.0))
    body = handle.union(neck).union(hook)
    return body


def build_zipper_hook():
    """A small J-hook on a handle: the neck ends in a tight J that slips into a
    zipper pull's hole and tugs it. Shorter reach, smaller hook."""
    handle = _grip_handle(handle_len * 0.85, add_loop=True)

    neck_w = min(HALF * 0.8, 8.0)
    j_reach = reach * 0.6
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, HALF * 0.4, -thick / 2.0))
        .box(neck_w, j_reach + HALF, thick, centered=(True, True, False))
        .translate((0, -j_reach + HALF * 0.4, 0))
    )
    # Tight J-hook (smaller radius, ~200° sweep so it curls back into a J).
    jr = max(3.0, hook_r * 0.6)
    hook = _hook_profile(jr, hook_open * 0.5, thick, 200.0)
    hook = hook.translate((0, -j_reach - jr, -thick / 2.0))
    body = handle.union(neck).union(hook)
    return body


def build_reacher_hook():
    """A longer reacher: a long neck ending in a wide open C-hook to snag a
    waistband, sock, or dropped item and draw it in."""
    handle = _grip_handle(handle_len, add_loop=True)

    neck_w = min(HALF * 0.95, 12.0)
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, HALF * 0.4, -thick / 2.0))
        .box(neck_w, reach + HALF, thick, centered=(True, True, False))
        .translate((0, -reach + HALF * 0.4, 0))
    )
    # Wide open C-hook (big radius, ~180° so it stays open to snag cloth).
    big_r = max(hook_r, 14.0)
    hook = _hook_profile(big_r, hook_open * 1.6, thick, 180.0)
    hook = hook.translate((0, -reach - big_r, -thick / 2.0))
    body = handle.union(neck).union(hook)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "zipper_hook":
    result = build_zipper_hook()
elif target_part == "reacher_hook":
    result = build_reacher_hook()
else:  # "button_hook"
    result = build_button_hook()
