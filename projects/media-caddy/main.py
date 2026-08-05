"""
USB / SD / Battery Caddy — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A desk organizer with an array of correctly-sized slots or bores for one class
of small media or battery. Pick the media form factor and how many; the caddy
sizes every pocket to the real part. Three modes (dispatched by `target_part`):

  * "tray"  — shallow pockets in a flat, wide tray (items lie / stand low).
  * "block" — deeper bores in a taller standing block (items stand upright).
  * "grid"  — an explicit rows × columns matrix of pockets.

Media form factors (nominal part size; the pocket adds a small clearance):
  usb_a   12.0 × 4.5 mm rectangular
  sd      24.0 × 2.1 mm rectangular
  microsd 11.0 × 1.0 mm rectangular
  aa      Ø14.5 mm round
  aaa     Ø10.5 mm round
  18650   Ø18.5 mm round

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `slots`).
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


# ── Media form-factor table (nominal part footprint) ─────────────────────────
# shape "rect": (x, y) mm; shape "round": diameter mm. `depth` is a sensible
# pocket depth for that media.
MEDIA = {
    "usb_a":   {"shape": "rect",  "x": 12.0, "y": 4.5,  "depth": 16.0},
    "sd":      {"shape": "rect",  "x": 24.0, "y": 2.1,  "depth": 18.0},
    "microsd": {"shape": "rect",  "x": 11.0, "y": 1.0,  "depth": 8.0},
    "aa":      {"shape": "round", "d": 14.5,            "depth": 40.0},
    "aaa":     {"shape": "round", "d": 10.5,            "depth": 34.0},
    "18650":   {"shape": "round", "d": 18.5,            "depth": 55.0},
}


def media_spec(key):
    k = str(key).strip().lower().replace("-", "").replace(" ", "")
    if k in ("usba", "usb"):
        k = "usb_a"
    elif k in ("micro_sd", "micro"):
        k = "microsd"
    return MEDIA.get(k, MEDIA["usb_a"])


# ── Parameters ───────────────────────────────────────────────────────────────
media       = str(  PARAM(lambda: media, "usb_a"))     # form factor key
slots       = int(  PARAM(lambda: slots,   8))         # total number of pockets
rows        = int(  PARAM(lambda: rows,    3))         # number of rows (grid mode)
base        = float(PARAM(lambda: base,    3.0))       # solid base under the pockets (mm)
wall        = float(PARAM(lambda: wall,    3.0))       # wall between/around pockets (mm)
clear       = float(PARAM(lambda: clear,   0.6))       # per-side pocket clearance (mm)
pocket_depth = float(PARAM(lambda: pocket_depth, 0.0)) # 0 = use the media default

target_part = str(  PARAM(lambda: target_part, "tray"))  # tray | block | grid

# ── Clamps / derived values ──────────────────────────────────────────────────
spec = media_spec(media)
slots = max(1, min(slots, 200))
rows = max(1, min(rows, 20))
base = max(1.5, min(base, 20.0))
wall = max(1.5, min(wall, 12.0))
clear = max(0.0, min(clear, 2.0))

# Mode-driven pocket depth and grid shaping.
default_depth = spec["depth"]
if target_part == "tray":
    default_depth = min(default_depth, 14.0)  # shallow, wide
depth = pocket_depth if pocket_depth > 0.5 else default_depth
depth = max(3.0, depth)

# Cell footprint (pocket + clearance + wall) in X and Y.
if spec["shape"] == "rect":
    px, py = spec["x"] + 2.0 * clear, spec["y"] + 2.0 * clear
else:
    px = py = spec["d"] + 2.0 * clear

cell_x = px + wall
cell_y = py + wall

def _near_square_rows(n):
    """Rows for a near-square grid of n cells (rows <= cols): floor(sqrt(n))."""
    r = 1
    while (r + 1) * (r + 1) <= n:
        r += 1
    return max(1, r)


# Column / row layout — made distinct per mode so the three parts never render
# identically:
#   tray  → a single wide row (shallow pockets, set above)
#   block → a compact near-square matrix (deep pockets, tall body)
#   grid  → exactly `rows` rows (user-controlled matrix)
if target_part == "tray":
    rows_eff = 1
    cols_eff = slots
elif target_part == "block":
    rows_eff = min(slots, _near_square_rows(slots))
    cols_eff = max(1, (slots + rows_eff - 1) // rows_eff)
else:  # grid
    rows_eff = max(1, min(rows, slots))
    cols_eff = max(1, (slots + rows_eff - 1) // rows_eff)

total = rows_eff * cols_eff


# ── Helpers ──────────────────────────────────────────────────────────────────
def cell_points():
    """Centres of every pocket, laid out as a rows × cols matrix centred on
    the origin."""
    pts = []
    x0 = -(cols_eff - 1) * cell_x / 2.0
    y0 = -(rows_eff - 1) * cell_y / 2.0
    placed = 0
    for r in range(rows_eff):
        for c in range(cols_eff):
            if placed >= total:
                break
            pts.append((x0 + c * cell_x, y0 + r * cell_y))
            placed += 1
    return pts


def base_block(h):
    """The solid caddy body sized to hold the full pocket matrix, base at z=0."""
    body_w = cols_eff * cell_x + wall
    body_d = rows_eff * cell_y + wall
    block = cq.Workplane("XY").box(body_w, body_d, h, centered=(True, True, False))
    try:
        block = block.edges("|Z").fillet(min(wall * 0.6, 2.5))
    except Exception:
        pass
    return block


def pocket_cutter(from_top_z, pts):
    """One cutter solid holding every pocket, cut downward from z=from_top_z to a
    depth of `depth` (leaving `base` under a blind pocket)."""
    if spec["shape"] == "rect":
        proto = (
            cq.Workplane("XY")
            .pushPoints(pts)
            .rect(px, py)
            .extrude(depth + 1.0)
        )
    else:
        proto = (
            cq.Workplane("XY")
            .pushPoints(pts)
            .circle(px / 2.0)
            .extrude(depth + 1.0)
        )
    # Position so the pocket mouth is at from_top_z and it bores downward.
    return proto.translate((0, 0, from_top_z - depth))


# ── Builders ─────────────────────────────────────────────────────────────────
def build():
    """All three modes share this body: a solid block with blind pockets bored
    from the top. `target_part` sets the height/depth via `depth` and the layout
    via rows/cols above, giving three distinct organisers."""
    h = base + depth
    body = base_block(h)
    pts = cell_points()
    body = body.cut(pocket_cutter(h, pts))
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
# The three parts differ by pocket depth (tray = shallow, block = full-depth)
# and layout (grid = explicit rows). All flow through build() with the mode
# already baked into `depth`, `rows_eff`, and `cols_eff` above.
result = build()
