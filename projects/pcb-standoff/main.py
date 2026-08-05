"""
PCB Standoff / Mounting Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Standoffs to mount a PCB above a surface. A hole pattern (four corners of a
W×D rectangle, or a rows×cols grid) drives the standoff positions; each standoff
is a tube with a screw bore. An optional base plate connects them into a single
printable mounting plate.

Modes are dispatched via `target_part`:
  * "plate"     — standoffs standing on a connecting base plate.
  * "standoffs" — the same standoffs joined by a thin strip (loose set, no plate).
  * "spacer"    — a single tubular spacer/standoff.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `screw_size`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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


# ── Screw table ──────────────────────────────────────────────────────────────
# bore = through/tap bore in the standoff; boss = outer standoff diameter.
SCREW_TABLE = {
    "M2":   {"bore": 1.9, "boss": 4.5},
    "M2.5": {"bore": 2.3, "boss": 5.0},
    "M3":   {"bore": 2.7, "boss": 6.0},
}


def screw_spec(key):
    k = str(key).strip().upper().replace(" ", "")
    if k in ("M2", "2", "2MM"):
        return SCREW_TABLE["M2"]
    if k in ("M2.5", "M25", "2.5", "2.5MM"):
        return SCREW_TABLE["M2.5"]
    return SCREW_TABLE.get("M3", SCREW_TABLE["M3"])


# ── Parameters ───────────────────────────────────────────────────────────────
pattern    = str(PARAM(lambda: pattern, "corners"))   # "corners" | "grid"
rect_w     = float(PARAM(lambda: rect_w,  58.0))       # corners: X spacing
rect_d     = float(PARAM(lambda: rect_d,  49.0))       # corners: Y spacing
grid_rows  = int(PARAM(lambda: grid_rows,   3))        # grid: rows (Y)
grid_cols  = int(PARAM(lambda: grid_cols,   3))        # grid: cols (X)
grid_pitch = float(PARAM(lambda: grid_pitch, 20.0))    # grid: hole pitch

standoff_h = float(PARAM(lambda: standoff_h, 6.0))     # standoff height
screw_size = str(PARAM(lambda: screw_size, "M3"))      # "M2" | "M2.5" | "M3"
plate_t    = float(PARAM(lambda: plate_t,   2.0))      # base plate thickness (0 = none)

target_part = str(PARAM(lambda: target_part, "plate"))  # plate|standoffs|spacer

# ── Derived ──────────────────────────────────────────────────────────────────
spec = screw_spec(screw_size)
bore_d = spec["bore"]
boss_d = spec["boss"]

standoff_h = max(1.5, standoff_h)
plate_t = max(0.0, plate_t)
grid_rows = max(1, min(grid_rows, 12))
grid_cols = max(1, min(grid_cols, 12))
grid_pitch = max(boss_d + 1.0, grid_pitch)
rect_w = max(boss_d + 1.0, rect_w)
rect_d = max(boss_d + 1.0, rect_d)

margin = boss_d * 0.75 + 1.5      # plate/strip material around the outer bosses
strip_w = boss_d + 2.0            # width of the connecting strip in "standoffs"


# ── Pattern points (centred on origin) ───────────────────────────────────────
def pattern_points():
    if str(pattern).lower().startswith("grid"):
        pts = []
        x0 = -(grid_cols - 1) * grid_pitch / 2.0
        y0 = -(grid_rows - 1) * grid_pitch / 2.0
        for r in range(grid_rows):
            for c in range(grid_cols):
                pts.append((x0 + c * grid_pitch, y0 + r * grid_pitch))
        return pts
    hx, hy = rect_w / 2.0, rect_d / 2.0
    return [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]


def bounds_of(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), max(xs), min(ys), max(ys)


# ── Builders ─────────────────────────────────────────────────────────────────
def one_standoff(x, y, base_z, height):
    """A solid tubular standoff at (x, y) rising from base_z, then bored."""
    tube = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(x, y, base_z))
        .circle(boss_d / 2.0)
        .extrude(height)
    )
    return tube


def bore_all(body, pts, base_z, height):
    for (x, y) in pts:
        cutter = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, base_z - 0.5))
            .circle(bore_d / 2.0)
            .extrude(height + 1.0)
        )
        body = body.cut(cutter)
    return body


def build_plate():
    """Standoffs on a solid connecting plate. If plate_t == 0, fall back to a
    thin connecting slab so the set still prints as one piece."""
    pts = pattern_points()
    x0, x1, y0, y1 = bounds_of(pts)
    pw = (x1 - x0) + 2.0 * margin
    pd = (y1 - y0) + 2.0 * margin
    t = plate_t if plate_t > 0.05 else 1.6

    body = cq.Workplane("XY").box(pw, pd, t, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(margin, boss_d / 2.0))
    except Exception:
        pass

    for (x, y) in pts:
        body = body.union(one_standoff(x, y, t, standoff_h))
    body = bore_all(body, pts, 0.0, t + standoff_h)
    return body


def build_standoffs():
    """Standoffs joined only by a thin cross strip (a loose set on a runner)."""
    pts = pattern_points()
    x0, x1, y0, y1 = bounds_of(pts)

    # Thin runner strips along X at each distinct row, plus one spine in Y.
    strip_t = 1.2
    body = None
    rows = sorted(set(round(p[1], 3) for p in pts))
    for yv in rows:
        length = (x1 - x0) + strip_w
        seg = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector((x0 + x1) / 2.0, yv, 0))
            .box(length, strip_w, strip_t, centered=(True, True, False))
        )
        body = seg if body is None else body.union(seg)
    spine = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((x0 + x1) / 2.0, (y0 + y1) / 2.0, 0))
        .box(strip_w, (y1 - y0) + strip_w, strip_t, centered=(True, True, False))
    )
    body = spine if body is None else body.union(spine)

    for (x, y) in pts:
        body = body.union(one_standoff(x, y, strip_t, standoff_h))
    body = bore_all(body, pts, 0.0, strip_t + standoff_h)
    return body


def build_spacer():
    """A single tubular spacer/standoff, bored through."""
    body = (
        cq.Workplane("XY").circle(boss_d / 2.0).extrude(standoff_h)
    )
    cutter = cq.Workplane("XY").transformed(
        offset=cq.Vector(0, 0, -0.5)
    ).circle(bore_d / 2.0).extrude(standoff_h + 1.0)
    return body.cut(cutter)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "standoffs":
    result = build_standoffs()
elif target_part == "spacer":
    result = build_spacer()
else:
    result = build_plate()
