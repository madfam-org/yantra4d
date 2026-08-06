"""
VESA Mount Adapter Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The canonical monitor / TV / mount interoperability object. Generates a flat
plate carrying a VESA FDMI square bolt pattern. Two modes:

  * "plate"   — a single VESA pattern (screw-clearance holes) plus optional
                extra corner mounting holes: a display-side or wall-side plate,
                spacer, or riser.
  * "adapter" — bridges two different VESA squares. The SOURCE pattern receives
                the monitor's mounting studs/screws (clearance holes on the back
                face); the DESTINATION pattern is a second, differently sized
                VESA square whose clearance holes bolt through to the wall mount.

Optional: rounded corners, plate margin beyond the bolt square, counterbore/
countersink for flush screw heads, and a center lightening/cable-passthrough
cutout.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `plate_thick`).
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


# ── VESA FDMI standard table ─────────────────────────────────────────────────
# Each standard is a square (or rectangular) bolt pattern with a nominal screw.
# spacing_x / spacing_y are the on-centre hole distances (mm); screw_clear is a
# printable clearance-hole diameter for the specified metric screw.
#   M4 clearance ≈ 4.5 mm (VESA MIS-D/C/E, 75 & 100)
#   M6 clearance ≈ 6.5 mm (VESA MIS-F, 200 & 200×100)
VESA_TABLE = {
    "75":     {"sx": 75.0,  "sy": 75.0,  "screw": "M4", "screw_clear": 4.5},
    "100":    {"sx": 100.0, "sy": 100.0, "screw": "M4", "screw_clear": 4.5},
    "200":    {"sx": 200.0, "sy": 200.0, "screw": "M6", "screw_clear": 6.5},
    "200x100": {"sx": 200.0, "sy": 100.0, "screw": "M6", "screw_clear": 6.5},
}


def vesa_spec(key):
    """Look up a VESA standard, tolerant of ints/floats and stray spacing."""
    k = str(key).strip().lower().replace(" ", "").replace("*", "x")
    # Normalise a few equivalent spellings.
    if k in ("100x100", "100.0"):
        k = "100"
    elif k in ("75x75", "75.0"):
        k = "75"
    elif k in ("200x200", "200.0"):
        k = "200"
    elif k in ("200x100", "100x200"):
        k = "200x100"
    return VESA_TABLE.get(k, VESA_TABLE["100"])


# ── Parameters ───────────────────────────────────────────────────────────────
mode         = str(  PARAM(lambda: mode,          "plate"))  # "plate" | "adapter"
target_part  = str(  PARAM(lambda: target_part,     ""   ))  # overrides `mode` if set

# The studio dispatches parts through `target_part`; fall back to `mode`.
active_mode = target_part if target_part in ("plate", "adapter") else mode
if active_mode not in ("plate", "adapter"):
    active_mode = "plate"

vesa_size      = str(PARAM(lambda: vesa_size,      "100"))   # source / plate pattern
dest_vesa_size = str(PARAM(lambda: dest_vesa_size, "200"))   # destination pattern (adapter)

plate_thick  = float(PARAM(lambda: plate_thick,     4.0))    # plate thickness (mm)
plate_margin = float(PARAM(lambda: plate_margin,   12.0))    # material beyond the bolt square
corner_r     = float(PARAM(lambda: corner_r,        6.0))    # plate corner radius (0 = sharp)

countersink  = bool( PARAM(lambda: countersink,   False))    # recess screw heads
cs_diameter  = float(PARAM(lambda: cs_diameter,     9.0))    # counterbore/head recess diameter
cs_depth     = float(PARAM(lambda: cs_depth,        2.5))    # recess depth

center_hole      = bool( PARAM(lambda: center_hole,   False))  # lightening / cable pass-through
center_hole_dia  = float(PARAM(lambda: center_hole_dia, 40.0)) # its diameter

extra_holes  = bool( PARAM(lambda: extra_holes,    False))    # extra corner mounting holes
extra_hole_dia = float(PARAM(lambda: extra_hole_dia, 5.0))    # their diameter


# ── Derived geometry ─────────────────────────────────────────────────────────
src = vesa_spec(vesa_size)
dst = vesa_spec(dest_vesa_size)

plate_thick  = max(1.5, plate_thick)
plate_margin = max(3.0, plate_margin)
cs_depth     = max(0.0, min(cs_depth, plate_thick - 0.8))

# In adapter mode the plate must clear BOTH squares; in plate mode just the one.
if active_mode == "adapter":
    span_x = max(src["sx"], dst["sx"])
    span_y = max(src["sy"], dst["sy"])
else:
    span_x = src["sx"]
    span_y = src["sy"]

plate_w = span_x + 2.0 * plate_margin
plate_d = span_y + 2.0 * plate_margin

# Corner radius can't exceed half the shortest side (leave a hair of tolerance).
corner_r = max(0.0, min(corner_r, min(plate_w, plate_d) / 2.0 - 0.01))


# ── Helpers ──────────────────────────────────────────────────────────────────
def rounded_plate(w, d, h, r):
    """Axis-aligned plate on XY, base at z=0, optional rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass  # degenerate radius — leave the corners square (non-fatal)
    return wp


def square_pattern_points(sx, sy):
    """The four corner points of a VESA square, centred on the origin."""
    hx, hy = sx / 2.0, sy / 2.0
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]


def drill(body, points, hole_dia):
    """Cut straight through-holes at each (x, y). Bore extends past both faces
    to guarantee a clean, watertight cut."""
    r = hole_dia / 2.0
    if r <= 0.05 or not points:
        return body
    cutter = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(r)
        .extrude(plate_thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return body.cut(cutter)


def recess(body, points, head_dia, depth):
    """Counterbore each hole from the TOP face (flat-bottomed pocket for a
    flush screw head). Skipped when disabled or degenerate."""
    r = head_dia / 2.0
    if not countersink or r <= 0.05 or depth <= 0.05 or not points:
        return body
    pocket = (
        cq.Workplane("XY")
        .workplane(offset=plate_thick)
        .pushPoints(points)
        .circle(r)
        .extrude(-depth)
    )
    return body.cut(pocket)


def corner_hole_points():
    """Four mounting holes just inside the plate corners."""
    inset = max(extra_hole_dia, 4.0)
    hx = plate_w / 2.0 - inset
    hy = plate_d / 2.0 - inset
    if hx <= 0 or hy <= 0:
        return []
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]


# ── Builders ─────────────────────────────────────────────────────────────────
def build_plate():
    """Single VESA pattern plate."""
    body = rounded_plate(plate_w, plate_d, plate_thick, corner_r)

    holes = square_pattern_points(src["sx"], src["sy"])
    body = drill(body, holes, src["screw_clear"])
    body = recess(body, holes, cs_diameter, cs_depth)

    if extra_holes:
        corners = corner_hole_points()
        body = drill(body, corners, extra_hole_dia)
        body = recess(body, corners, cs_diameter, cs_depth)

    if center_hole:
        body = drill(body, [(0.0, 0.0)], _clamped_center_dia())

    return body


def build_adapter():
    """Adapter: SOURCE square (monitor side, clearance holes) + DESTINATION
    square (wall-mount side, a differently sized VESA square of clearance
    holes). Both are through-holes so a single plate bridges the two mounts."""
    body = rounded_plate(plate_w, plate_d, plate_thick, corner_r)

    src_holes = square_pattern_points(src["sx"], src["sy"])
    dst_holes = square_pattern_points(dst["sx"], dst["sy"])

    # Source pattern receives the monitor studs; countersink on the DESTINATION
    # (wall) face is the usual case, but expose recesses on both for flush heads.
    body = drill(body, src_holes, src["screw_clear"])
    body = drill(body, dst_holes, dst["screw_clear"])
    body = recess(body, src_holes, cs_diameter, cs_depth)
    body = recess(body, dst_holes, cs_diameter, cs_depth)

    if center_hole:
        body = drill(body, [(0.0, 0.0)], _clamped_center_dia())

    return body


def _clamped_center_dia():
    """Keep the centre cutout from eating into the innermost bolt ring / margin."""
    if active_mode == "adapter":
        smallest = min(src["sx"], src["sy"], dst["sx"], dst["sy"])
        clear = min(src["screw_clear"], dst["screw_clear"])
    else:
        smallest = min(src["sx"], src["sy"])
        clear = src["screw_clear"]
    # Leave ≥6 mm of web between the cutout wall and the nearest bolt hole.
    max_dia = smallest - clear - 12.0
    max_dia = max(6.0, max_dia)
    return max(6.0, min(center_hole_dia, max_dia))


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active_mode == "adapter":
    result = build_adapter()
else:
    result = build_plate()
