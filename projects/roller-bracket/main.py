"""
Conveyor / Roller Bracket — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A line-side bracket that holds a roller axle or shaft for conveyors and material
handling. An upright web carries the shaft seat (an open-top U-slot for a plain
axle, or a round pocket sized for a 608 bearing OD 22 mm) above a mounting foot.
The foot mounts three ways: bolt-down (foot with holes), extrusion (a tab for
2020 T-slot), or wall.

Three build targets are dispatched by `target_part`:
  - "bracket"         : single upright with a plain shaft slot + foot
  - "bearing_bracket" : single upright with a 608 bearing seat pocket
  - "bracket_pair"    : two brackets positioned facing each other on one base

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shaft_dia`).
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


# Standard 608 bearing outer diameter (skateboard / common idler bearing).
BEARING_608_OD = 22.0

# ── Parameters ───────────────────────────────────────────────────────────────
shaft_dia    = float(PARAM(lambda: shaft_dia,      8.0))  # roller axle / shaft diameter
mount_height = float(PARAM(lambda: mount_height,  40.0))  # shaft centre height above foot
web_thick    = float(PARAM(lambda: web_thick,      8.0))  # upright web thickness
web_width    = float(PARAM(lambda: web_width,     30.0))  # upright web width
foot_len     = float(PARAM(lambda: foot_len,      45.0))  # mounting foot length
foot_thick   = float(PARAM(lambda: foot_thick,     6.0))  # mounting foot thickness

mount        = str(  PARAM(lambda: mount,   "bolt_down"))  # bolt_down|extrusion|wall
mount_dia    = float(PARAM(lambda: mount_dia,      5.5))  # mounting hole diameter
open_slot    = bool( PARAM(lambda: open_slot,     True))  # open-top U slot vs closed bore
bearing_seat = bool( PARAM(lambda: bearing_seat, False))  # 608 bearing pocket (single modes)
pair_gap     = float(PARAM(lambda: pair_gap,     100.0))  # inner gap between the two uprights

target_part  = str(  PARAM(lambda: target_part, "bracket"))

# ── Derived / clamped ────────────────────────────────────────────────────────
shaft_dia    = max(2.0, min(shaft_dia, 40.0))
web_thick    = max(3.0, min(web_thick, 25.0))
web_width    = max(shaft_dia + 6.0, min(web_width, 120.0))
mount_height = max(shaft_dia + 8.0, min(mount_height, 200.0))
foot_thick   = max(3.0, min(foot_thick, 20.0))
mount_dia    = max(2.5, min(mount_dia, 10.0))
seat_dia     = BEARING_608_OD  # for bearing seat
seat_depth   = 7.5             # 608 bearing width is 7 mm; pocket 7.5 for fit


# ── Helpers ──────────────────────────────────────────────────────────────────
def _foot(cx=0.0):
    """Mounting foot as a flat slab centred at x=cx, base at z=0."""
    depth = max(web_width, foot_len)
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, 0.0))
        .box(foot_len, depth, foot_thick, centered=(True, True, False))
    )


def _foot_holes(solid, cx=0.0):
    """Bolt-down holes in the foot (two along X)."""
    hx = foot_len / 2.0 - max(mount_dia, 5.0)
    depth = max(web_width, foot_len)
    hy = depth / 2.0 - max(mount_dia, 5.0)
    pts = [(cx + hx, hy), (cx - hx, hy), (cx + hx, -hy), (cx - hx, -hy)]
    cutter = (
        cq.Workplane("XY")
        .pushPoints(pts)
        .circle(mount_dia / 2.0)
        .extrude(foot_thick + 2.0)
    )
    return solid.cut(cutter)


def _web(cx=0.0):
    """Upright web slab rising from the foot to above the shaft centre."""
    top = mount_height + max(shaft_dia, seat_dia) / 2.0 + 6.0
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, foot_thick))
        .box(web_thick, web_width, top - foot_thick, centered=(True, True, False))
    )


def _shaft_cut(cx=0.0, seat=False):
    """Cut the shaft seat through the web (thickness along X).
    - plain: round bore of shaft_dia, optionally opened to the top as a U-slot.
    - seat : a 608 bearing pocket (blind, from the +X face) of seat_dia."""
    z = mount_height
    if seat:
        # Blind pocket for a 608 bearing on the +X face, plus a through pilot
        # bore so the axle passes.
        pocket = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, z, cx + web_thick / 2.0 - seat_depth))
            .circle(seat_dia / 2.0)
            .extrude(seat_depth + 0.1)
        )
        pilot = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0.0, z, cx - web_thick / 2.0 - 1.0))
            .circle(shaft_dia / 2.0)
            .extrude(web_thick + 2.0)
        )
        return pocket.union(pilot)
    # Plain through bore
    bore = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0.0, z, cx - web_thick / 2.0 - 1.0))
        .circle(shaft_dia / 2.0)
        .extrude(web_thick + 2.0)
    )
    if open_slot:
        # Open the bore to the top with a vertical channel (drop-in axle). The
        # channel runs from the shaft centre up past the web top, width = shaft.
        web_top = mount_height + max(shaft_dia, seat_dia) / 2.0 + 6.0
        chan_h = (web_top + 5.0) - z
        chan = (
            cq.Workplane("XY")
            .box(web_thick + 2.0, shaft_dia, chan_h, centered=(True, True, False))
            .translate((cx, 0.0, z))
        )
        bore = bore.union(chan)
    return bore


def _extrusion_tab(cx=0.0):
    """A downward tab sized to drop into a 2020 aluminium extrusion T-slot
    (slot ~6 mm), so the bracket bolts to 2020 framing with a T-nut."""
    tab_w = 5.8      # fits a 6 mm 2020 slot opening
    tab_h = 8.0
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, 0.0, -tab_h))
        .box(tab_w, min(web_width, 18.0), tab_h, centered=(True, True, False))
    )
    return tab


# ── Single bracket builders ──────────────────────────────────────────────────
def _single(cx=0.0, seat=False):
    body = _web(cx)
    if mount == "wall":
        # Wall mount: the web itself is the mounting face; add a small back foot.
        body = body.union(_foot(cx))
        body = _wall_holes(body, cx)
    elif mount == "extrusion":
        body = body.union(_foot(cx))
        body = body.union(_extrusion_tab(cx))
        body = _foot_holes(body, cx)
    else:  # bolt_down
        body = body.union(_foot(cx))
        body = _foot_holes(body, cx)
    body = body.cut(_shaft_cut(cx, seat=seat))
    return body


def _wall_holes(solid, cx=0.0):
    """Two holes through the web for wall screws (thickness along X)."""
    z1 = mount_height + max(shaft_dia, seat_dia) / 2.0 + 2.0
    z2 = foot_thick + 6.0
    hy = web_width / 2.0 - max(mount_dia, 5.0)
    cutter = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0.0, 0.0, cx - web_thick / 2.0 - 1.0))
        .pushPoints([(hy, z1), (-hy, z1), (hy, z2), (-hy, z2)])
        .circle(mount_dia / 2.0)
        .extrude(web_thick + 2.0)
    )
    return solid.cut(cutter)


def build_bracket():
    return _single(0.0, seat=bearing_seat)


def build_bearing_bracket():
    return _single(0.0, seat=True)


# ── Paired brackets ──────────────────────────────────────────────────────────
def build_bracket_pair():
    """Two uprights facing each other, sharing one continuous base, so a roller
    spans the `pair_gap` between their shaft seats."""
    offset = pair_gap / 2.0 + web_thick / 2.0
    seat = bearing_seat

    # One continuous base slab spanning both feet.
    span = pair_gap + 2.0 * (web_thick + foot_len)
    depth = max(web_width, foot_len)
    base = cq.Workplane("XY").box(span, depth, foot_thick, centered=(True, True, False))

    left = _web(-offset).cut(_shaft_cut(-offset, seat=seat))
    right = _web(offset).cut(_shaft_cut(offset, seat=seat))

    body = base.union(left).union(right)

    # Bolt-down holes near each end of the shared base.
    hx = span / 2.0 - max(mount_dia, 5.0)
    hy = depth / 2.0 - max(mount_dia, 5.0)
    pts = [(hx, hy), (-hx, hy), (hx, -hy), (-hx, -hy)]
    cutter = (
        cq.Workplane("XY").pushPoints(pts).circle(mount_dia / 2.0).extrude(foot_thick + 2.0)
    )
    body = body.cut(cutter)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "bracket":         build_bracket,
    "bearing_bracket": build_bearing_bracket,
    "bracket_pair":    build_bracket_pair,
}

result = _dispatch.get(target_part, build_bracket)()
