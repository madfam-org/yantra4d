"""
Under-Shelf / Under-Desk Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Reclaims the dead space under a shelf, desk, or cabinet. A shelf-edge clamp (an
open C that grips over the surface edge of thickness `surface_t`) OR an
underside screw plate carries a payload that hangs below: a small bin, a router
cradle, a hook, or a power-strip cradle. Three families, each its own studio
mode:

  * "clamp_bin"    — a C-clamp that hooks over the shelf edge (no tools, no
                     drilling) with an open bin hanging beneath it.
  * "screw_cradle" — a flat plate that screws up into the underside of the
                     surface, with a cradle hanging beneath — for a permanent,
                     load-bearing fix.
  * "edge_hook"    — the C-clamp with a simple downward hook instead of a bin,
                     for cables, headphones, or bags.

A `payload` select picks what hangs below (bin / cradle / hook / strip). Shared
across the batch: a plate helper and a bin/cradle builder are reused so the
hanging payload is identical whichever attachment holds it.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `surface_t`).
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
# Read every injected global once at module scope (reference-cartridge pattern)
# so ruff sees the self-referential binding and does not flag F821.
payload     = str(PARAM(lambda: payload, "bin"))     # bin|router_cradle|hook|strip
target_part = str(PARAM(lambda: target_part, ""))    # studio dispatch (part id)

surface_t   = float(PARAM(lambda: surface_t, 25.0))  # shelf / desk thickness gripped (mm)
width       = float(PARAM(lambda: width,     70.0))  # mount width along the edge X (mm)
wall_t      = float(PARAM(lambda: wall_t,     4.0))  # material thickness (mm)

grip_len    = float(PARAM(lambda: grip_len,  35.0))  # how far the clamp reaches over the top (mm)
clamp_clear = float(PARAM(lambda: clamp_clear, 0.4)) # clamp-to-surface fit gap (mm)

payload_depth  = float(PARAM(lambda: payload_depth,  60.0))  # forward/out reach of payload Y (mm)
payload_height = float(PARAM(lambda: payload_height, 45.0))  # drop height of payload Z (mm)

screw_dia   = float(PARAM(lambda: screw_dia, 4.2))   # underside screw clearance dia (mm)


# ── Safe clamps ──────────────────────────────────────────────────────────────
surface_t = max(6.0, min(surface_t, 60.0))
width = max(30.0, min(width, 250.0))
wall_t = max(2.5, min(wall_t, 8.0))
grip_len = max(15.0, min(grip_len, 120.0))
clamp_clear = max(0.0, min(clamp_clear, 1.5))
payload_depth = max(20.0, min(payload_depth, 200.0))
payload_height = max(15.0, min(payload_height, 150.0))
screw_dia = max(2.5, min(screw_dia, 8.0))

_part_ids = ("clamp_bin", "screw_cradle", "edge_hook")
active_part = target_part if target_part in _part_ids else "clamp_bin"


# ── Shared plate + payload helpers (reused across the batch) ──────────────────
def slab_xy(cx, cy, cz, sx, sy, sz):
    """Axis-aligned block centred at (cx,cy,cz) with sizes (sx,sy,sz)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, cz))
        .box(sx, sy, sz)
    )


def edge_clamp():
    """An open C that grips over a shelf edge. Coordinate frame:
      - The shelf occupies Y:[0, +∞) (into the shelf) and Z:[0, surface_t].
      - The clamp's back web sits at the edge (Y ≈ 0), the top jaw reaches back
        over the shelf top (grip_len in +Y at z≈surface_t), and the bottom jaw
        reaches under the shelf, forming the fixing face the payload hangs from.
    Built as a solid C = a filled outer block minus the shelf slot."""
    gap = surface_t + clamp_clear                 # vertical opening of the C
    back = wall_t                                 # back web thickness (in Y)
    top_jaw = wall_t                              # jaw thickness (in Z)
    reach = grip_len

    # Outer solid envelope of the C (Y:[-back, reach], Z:[-wall_t, gap+wall_t]).
    y0, y1 = -back, reach
    z0, z1 = -wall_t, gap + top_jaw
    outer = slab_xy(0, (y0 + y1) / 2.0, (z0 + z1) / 2.0, width, (y1 - y0), (z1 - z0))

    # Cut the shelf slot so its bottom is at z=0 spanning up to z=gap, its mouth
    # open toward +Y and closed at the back web. Slightly wider than the shelf so
    # the shelf slides in with `clamp_clear` of play.
    slot = slab_xy(0, reach / 2.0 + 1.0, gap / 2.0, width + 2.0, reach + 2.0, gap)
    return outer.cut(slot)


def bin_payload(open_front):
    """A hanging open bin beneath the mount. Its top sits just under the clamp /
    plate (at z=0) and it drops to z=-payload_height, projecting out to +Y over
    payload_depth. `open_front` cuts a lower front scallop for a parts bin."""
    top_z = 0.0
    outer = slab_xy(0, payload_depth / 2.0, top_z - payload_height / 2.0,
                    width, payload_depth, payload_height)
    cavity = slab_xy(0, payload_depth / 2.0, top_z - (payload_height - wall_t) / 2.0,
                     width - 2.0 * wall_t, payload_depth - 2.0 * wall_t, payload_height)
    body = outer.cut(cavity)
    if open_front:
        scallop = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, top_z - payload_height * 0.35, payload_depth))
            .cylinder(4.0 * wall_t, min(width * 0.3, payload_height * 0.3))
        )
        body = body.cut(scallop)
    return body


def cradle_payload():
    """A router / power-strip cradle: an open channel (U in section) hanging
    beneath the mount, holding a slab-shaped device on its side. Two end walls
    plus a floor, open top and open along most of the length for airflow."""
    top_z = 0.0
    floor = slab_xy(0, payload_depth / 2.0, top_z - payload_height + wall_t / 2.0,
                    width, payload_depth, wall_t)
    # Front and back retaining walls (low), leaving the sides open.
    front = slab_xy(0, payload_depth - wall_t / 2.0, top_z - payload_height / 2.0,
                    width, wall_t, payload_height)
    back = slab_xy(0, wall_t / 2.0, top_z - payload_height / 2.0,
                   width, wall_t, payload_height)
    body = floor.union(front).union(back)
    return body


def hook_payload():
    """A simple downward-then-up J-hook hanging beneath the mount."""
    r = wall_t * 1.2
    stem = slab_xy(0, wall_t + r, -payload_height / 2.0, wall_t * 2.2, r * 2.0, payload_height)
    # Curl: a short up-turn at the bottom front.
    curl = slab_xy(0, wall_t + r + payload_depth * 0.25, -payload_height + r,
                   wall_t * 2.2, payload_depth * 0.5, r * 2.0)
    tip = slab_xy(0, wall_t + r + payload_depth * 0.5 - r, -payload_height + r * 2.5,
                  wall_t * 2.2, r * 2.0, r * 3.0)
    return stem.union(curl).union(tip)


def make_payload():
    """Dispatch the hanging payload by the `payload` select."""
    p = payload.strip().lower()
    if p in ("router_cradle", "strip"):
        return cradle_payload()
    if p == "hook":
        return hook_payload()
    return bin_payload(open_front=True)


def underside_plate():
    """A flat plate that screws up into the underside of the surface. It lies in
    Z:[0, wall_t] at the top, spanning width × payload_depth-ish, with four screw
    holes. The payload hangs beneath it (z < 0)."""
    plate_d = max(payload_depth, 40.0)
    plate = slab_xy(0, plate_d / 2.0, wall_t / 2.0, width, plate_d, wall_t)
    inset = max(screw_dia + 4.0, 8.0)
    xs = [-width / 2.0 + inset, width / 2.0 - inset]
    ys = [inset, plate_d - inset]
    for x in xs:
        for y in ys:
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(x, y, wall_t / 2.0))
                .cylinder(wall_t + 2.0, screw_dia / 2.0)
            )
            plate = plate.cut(hole)
    return plate


# ── Builders ─────────────────────────────────────────────────────────────────
def build_clamp_bin():
    """Shelf-edge C-clamp + hanging bin (or the selected payload)."""
    body = edge_clamp().union(make_payload())
    return body.clean()


def build_screw_cradle():
    """Underside screw plate + hanging cradle (or the selected payload)."""
    body = underside_plate().union(make_payload())
    return body.clean()


def build_edge_hook():
    """Shelf-edge C-clamp + a downward hook (payload forced to hook)."""
    body = edge_clamp().union(hook_payload())
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active_part == "screw_cradle":
    result = build_screw_cradle()
elif active_part == "edge_hook":
    result = build_edge_hook()
else:
    result = build_clamp_bin()
