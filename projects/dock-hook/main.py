"""
Monitor / Laptop Dock Hook — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An edge-mounted, screwless hook that snaps onto a desk or shelf edge of a chosen
thickness (a printed C-profile that springs over the edge). Three distinct forms
dispatched by `target_part`:

  * "dock_hook"       — a C-clamp over the edge with a forward arm and an
                        up-turned lip that cradles a laptop dock, tablet, or
                        phone stand dropped in from above.
  * "cable_drop"      — a C-clamp over the edge with a comb of upward-open
                        slots along the front, each an obround notch that a
                        cable drops into so it does not fall behind the desk.
  * "headset_hanger"  — a C-clamp over the edge with a broad rounded cradle arm
                        so a headset hangs by its band without a dent.

The snap fit is the C-profile: an outer block with the edge slot cut from one
face, leaving a back spine and two jaws. Its mouth is chamfered (a boolean cut,
never a fillet on the C-topology, which would go non-manifold) so it leads onto
the edge.

Reference dimensions:
  - Desk / shelf edges are commonly 15-30 mm; the default grips a 25 mm top.
  - Cable slots default to ~7 mm, clearing a fat braided USB-C or a small bundle.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `edge_t`).
  - Read them via PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default.
    `except Exception` catches the NameError raised for an unbound param name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
edge_t     = float(PARAM(lambda: edge_t,     25.0))   # desk / shelf edge thickness the clamp grips (mm)
width      = float(PARAM(lambda: width,      40.0))   # width of the hook across the edge (mm)
thick      = float(PARAM(lambda: thick,       6.0))   # jaw / arm / plate wall thickness (mm)
grip_depth = float(PARAM(lambda: grip_depth, 40.0))   # how deep the C grips onto the edge (mm)
reach      = float(PARAM(lambda: reach,      45.0))   # how far the arm reaches out from the edge (mm)
lip        = float(PARAM(lambda: lip,        18.0))   # up-turned retaining lip height (dock_hook, mm)
slot_w     = float(PARAM(lambda: slot_w,      7.0))   # cable slot width (cable_drop, mm)
slots      = int(  PARAM(lambda: slots,         4))   # number of cable slots (cable_drop)
cradle_w   = float(PARAM(lambda: cradle_w,   26.0))   # headband cradle width (headset_hanger, mm)

target_part = str(PARAM(lambda: target_part, "dock_hook"))  # dock_hook | cable_drop | headset_hanger

# ── Clamps / derived values ──────────────────────────────────────────────────
edge_t     = max(6.0, min(edge_t, 60.0))
width      = max(20.0, min(width, 120.0))
thick      = max(3.0, min(thick, 15.0))
grip_depth = max(20.0, min(grip_depth, 90.0))
reach      = max(15.0, min(reach, 120.0))
lip        = max(6.0, min(lip, 50.0))
slot_w     = max(3.0, min(slot_w, 20.0))
slots      = max(1, min(slots, 10))
cradle_w   = max(12.0, min(cradle_w, min(width, 80.0)))


# ── Helpers ──────────────────────────────────────────────────────────────────
def _box(w, d, h, x=0.0, y=0.0, z=0.0, cx=True, cy=True):
    """Box centred as requested in X/Y, base at z."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, z))
        .box(w, d, h, centered=(cx, cy, False))
    )


def c_clamp():
    """Screwless C that snaps over a desk/shelf edge.

    Coordinates: the desk edge runs along +Y (width in Y). The clamp opens in +X
    (the desk comes from +X). The back spine is at low X. Returns (body, front_x)
    where front_x is the outer X face the working arm attaches to.

    Built as a solid outer block minus the edge slot cut from the +X face, so the
    inside is open (the desk fills it) — never a trapped void."""
    total_h = edge_t + 2.0 * thick
    outer = _box(grip_depth, width, total_h, x=grip_depth / 2.0, cx=True)
    # Edge slot: open at +X, spans the full width + margin, leaves the back spine.
    slot = _box(
        grip_depth, width + 2.0, edge_t,
        x=grip_depth / 2.0 + thick, z=thick, cx=True,
    )
    body = outer.cut(slot)
    # Lead-in chamfers at the mouth (two boolean wedge cuts, top & bottom jaw).
    mouth_x = grip_depth
    lead = min(thick * 1.2, edge_t * 0.4)
    top_wedge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(mouth_x, 0, thick + edge_t))
        .transformed(rotate=cq.Vector(0, -45, 0))
        .box(lead * 2.0, width + 2.0, lead * 2.0, centered=(True, True, False))
    )
    bot_wedge = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(mouth_x, 0, thick))
        .transformed(rotate=cq.Vector(0, 45, 0))
        .box(lead * 2.0, width + 2.0, lead * 2.0, centered=(True, True, True))
    )
    try:
        body = body.cut(top_wedge).cut(bot_wedge)
    except Exception:
        pass
    return body, 0.0  # front (outer) face of the spine is at x=0


# ── Builders ─────────────────────────────────────────────────────────────────
def build_dock_hook():
    """C-clamp + a forward arm at the base with an up-turned retaining lip: a
    shelf a dock/tablet/phone rests on, the lip stopping it sliding off."""
    body, front_x = c_clamp()
    arm_z = thick  # arm shelf sits at the lower jaw's top
    # Forward arm reaching out in -X from the spine's outer face.
    arm = _box(reach, width, thick, x=front_x - reach / 2.0, z=arm_z)
    body = body.union(arm)
    # Up-turned retaining lip at the far end of the arm.
    lip_x = front_x - reach
    lip_wall = _box(thick, width, lip, x=lip_x + thick / 2.0, z=arm_z)
    body = body.union(lip_wall)
    # Soften exposed vertical corners of arm+lip (after unions, before returning).
    try:
        body = body.edges("|Z").fillet(min(thick * 0.4, 1.5))
    except Exception:
        pass
    return body


def build_cable_drop():
    """C-clamp + a short forward lip along the edge, combed with upward-open
    obround slots that cables drop into. Slots open to the top face → no void."""
    body, front_x = c_clamp()
    # A comb bar sitting on the lower jaw, standing up above the desktop so the
    # slots have material around them.
    comb_h = max(slot_w * 1.6, 16.0)
    comb_d = thick * 2.2
    comb = _box(comb_d, width, comb_h, x=front_x - comb_d / 2.0, z=thick)
    body = body.union(comb)
    # Obround slots opening upward from the top of the comb.
    n = slots
    pitch = width / n
    slot_r = slot_w / 2.0
    slot_depth = comb_h * 0.65  # leaves a floor so the comb stays continuous
    comb_top = thick + comb_h
    for i in range(n):
        yc = -width / 2.0 + (i + 0.5) * pitch
        # Obround = a rounded-end slot: a rectangle capped by a circle at the
        # bottom, opening out of the top face. Build the cutter tall so it opens.
        rect = _box(comb_d + 2.0, slot_w, slot_depth,
                    x=front_x - comb_d / 2.0, y=yc, z=comb_top - slot_depth)
        cap = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(front_x - comb_d / 2.0, yc, comb_top - slot_depth))
            .transformed(rotate=cq.Vector(90, 0, 0))
            .circle(slot_r)
            .extrude(comb_d + 2.0, both=True)
        )
        body = body.cut(rect).cut(cap)
    return body


def build_headset_hanger():
    """C-clamp + a forward arm ending in a broad rounded cradle so a headset
    hangs by its band without denting. Cradle = block with a half-round trough
    cut from the top (a cylinder lying across the width)."""
    body, front_x = c_clamp()
    arm_z = thick
    arm = _box(reach, cradle_w, thick, x=front_x - reach / 2.0, z=arm_z)
    body = body.union(arm)
    # Cradle block at the far end.
    cradle_r = cradle_w * 0.55
    block_h = cradle_r + thick
    cx = front_x - reach
    block = _box(cradle_r * 2.0 + thick, cradle_w + 2.0 * thick, block_h,
                 x=cx - (cradle_r + thick / 2.0), z=arm_z)
    body = body.union(block)
    # Half-round trough cut from the top of the cradle block (cylinder along Y).
    trough = (
        cq.Workplane("XZ")
        .circle(cradle_r)
        .extrude(cradle_w)
        .translate((cx - (cradle_r + thick / 2.0), cradle_w / 2.0, arm_z + block_h))
    )
    body = body.cut(trough)
    try:
        body = body.edges("|Z").fillet(min(thick * 0.4, 1.5))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "cable_drop":
    result = build_cable_drop()
elif target_part == "headset_hanger":
    result = build_headset_hanger()
else:
    result = build_dock_hook()
