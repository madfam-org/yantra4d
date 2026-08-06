"""
MOLLE / Webbing Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Attachment hardware for the MOLLE / PALS webbing grid. PALS is the open military
webbing standard (MIL-W-17337 / A-A-55301): horizontal rows of 1 in (25.4 mm)
webbing, spaced 1 in (25.4 mm) row-to-row, bartacked to the backing at 1.5 in
(38.1 mm) column intervals. This cartridge builds clips that thread that grid and
a rigid printable PALS field to attach onto.

  - molle_clip : a serpentine attachment strap that weaves through PALS rows and
                 snaps back on itself — a single folded solid the width of one row
                 (25 mm), with a snap tab. Weave count sets how many rows it spans.
  - pals_panel : a rigid PALS/MOLLE field — a backing plate with solid horizontal
                 webbing bars on a 1 in vertical pitch, bridged to the backing by
                 bartack posts on a 1.5 in horizontal pitch. The gaps between bars
                 and posts are the loops you thread a clip or strap through.
  - malice_clip: a MALICE-style single-column clip — a long stiff spine that
                 threads two rows and locks with a hooked foot; a lanyard hole and
                 a weep slot keep it manifold and vented.

Real dimensions (PALS / MOLLE standard):
  - webbing width / row height : 1 in = 25.4 mm  (default row_h)
  - row-to-row vertical pitch  : 1 in = 25.4 mm  (default row_pitch)
  - bartack column pitch       : 1.5 in = 38.1 mm (default col_pitch)

Watertight strategy:
  Every part is ONE solid built by UNIONING overlapping solids — never by cutting
  a true textile weave (which self-intersects). The clip is a serpentine profile
  extruded across the row width. The PALS field is solid bars + solid bartack
  posts unioned to a solid backing; the loops are the empty space between them, so
  no sealed cavity ever forms. Snap tabs are solid wedges. Through-slots are
  obround (slot2D). Fillets clean blanks BEFORE cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else default. `except Exception`
    catches the NameError the sandbox raises for an unbound parameter name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (PALS / MOLLE standard) ───────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "molle_clip"))
# "molle_clip" | "pals_panel" | "malice_clip"

row_h = float(PARAM(lambda: row_h, 25.4))         # 1 in webbing width / row height
row_pitch = float(PARAM(lambda: row_pitch, 25.4))  # 1 in row-to-row vertical pitch
col_pitch = float(PARAM(lambda: col_pitch, 38.1))  # 1.5 in bartack column pitch
strap_t = float(PARAM(lambda: strap_t, 2.4))      # clip/strap material thickness
weave_rows = int(round(float(PARAM(lambda: weave_rows, 2))))  # rows the clip spans
panel_rows = int(round(float(PARAM(lambda: panel_rows, 3))))  # PALS field rows
panel_cols = int(round(float(PARAM(lambda: panel_cols, 3))))  # PALS field columns
clearance = float(PARAM(lambda: clearance, 0.4))  # weave / thread clearance (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
row_h = max(18.0, min(row_h, 32.0))
row_pitch = max(18.0, min(row_pitch, 40.0))
col_pitch = max(28.0, min(col_pitch, 50.0))
strap_t = max(1.6, min(strap_t, 4.0))
weave_rows = max(1, min(weave_rows, 5))
panel_rows = max(1, min(panel_rows, 6))
panel_cols = max(1, min(panel_cols, 6))
clearance = max(0.1, min(clearance, 1.0))


# ── Shared helpers ───────────────────────────────────────────────────────────
def _fillet_z(solid, r):
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


def _obround_through(length, width, thickness, cx=0.0, cy=0.0):
    """Stadium/obround through-solid cut tool, long axis along X."""
    overall = max(width + 0.001, length)
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, -0.5))
        .slot2D(overall, width, angle=90)
        .extrude(thickness + 1.0)
    )
    return slot.rotate((cx, cy, 0), (cx, cy, 1), 90)


# ── Part builders ────────────────────────────────────────────────────────────
def build_molle_clip():
    """A serpentine MOLLE attachment strap the width of one PALS row (`row_h`). It
    weaves front-behind-front through `weave_rows` rows on `row_pitch`, then a
    snap tab catches the last row. Modeled as ONE serpentine profile (in the Y/Z
    plane) extruded across the row width in X → a single manifold solid; the fold
    depth clears the webbing thickness so it actually threads."""
    fold_gap = strap_t + clearance + 1.2       # how far the strap stands off
    span = weave_rows * row_pitch + row_pitch  # total vertical travel
    t = strap_t

    # Build a serpentine centre-line as a closed polygon band in (Y up, Z depth).
    # Front plane at z=0, back plane at z=-fold_gap; the band snakes between them
    # once per row so it passes behind each webbing bar.
    pts_front = []
    pts_back = []
    n = max(1, weave_rows)
    step = span / (2 * n)
    z_front = 0.0
    z_back = -fold_gap
    # outer (front-facing) edge of the band
    for i in range(2 * n + 1):
        yy = i * step
        zz = z_front if (i % 2 == 0) else z_back
        pts_front.append((yy, zz))
    # inner edge, offset by thickness t toward +Z (returns down)
    for i in range(2 * n, -1, -1):
        yy = i * step
        zz = (z_front if (i % 2 == 0) else z_back) + t
        pts_back.append((yy, zz))
    band_pts = pts_front + pts_back

    band = (
        cq.Workplane("YZ")
        .polyline(band_pts).close()
        .extrude(row_h)                        # across the row width in X
        .translate((-row_h / 2.0, 0, 0))
    )

    # Snap tab: a solid wedge on the top front face that catches the top row.
    tab = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, span, 0))
        .box(row_h * 0.7, row_pitch * 0.5, t + 1.6, centered=(True, True, False))
    )
    tab = _fillet_z(tab, min(3.0, row_h * 0.12))
    body = band.union(tab)
    # A grip hole in the tab (through Z, vents).
    grip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, span, -0.5))
        .circle(min(4.0, row_h * 0.16))
        .extrude(t + 2.6)
    )
    body = body.cut(grip)
    return body


def build_pals_panel():
    """A rigid PALS/MOLLE field: a backing plate with solid horizontal webbing
    bars on a 1 in vertical pitch, each bridged to the backing by bartack posts on
    a 1.5 in horizontal pitch. The empty channels between bar and backing (between
    posts) are the PALS loops you thread a clip through. Everything is unioned
    solids → manifold, and every gap opens to outside → no trapped void."""
    margin = 6.0
    bar_w = row_h * 0.7                          # webbing bar height (Y each)
    gap_behind = strap_t + clearance + 1.0       # stand-off = loop depth
    back_t = max(3.0, strap_t)
    post_w = 8.0                                 # bartack post width (X)

    width = (panel_cols) * col_pitch + 2.0 * margin
    height = (panel_rows) * row_pitch + 2.0 * margin

    # Backing plate.
    back = (
        cq.Workplane("XY")
        .box(width, height, back_t, centered=(True, True, False))
    )
    back = _fillet_z(back, min(5.0, margin * 0.6))
    body = back

    y0 = -height / 2.0 + margin + bar_w / 2.0
    # webbing bars stand off the backing on posts.
    for r in range(panel_rows):
        by = y0 + r * row_pitch
        bar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, by, back_t + gap_behind))
            .box(width - 2.0 * margin, bar_w, strap_t, centered=(True, True, False))
        )
        body = body.union(bar)
        # bartack posts bridging this bar to the backing at 1.5 in pitch.
        x0 = -((panel_cols) * col_pitch) / 2.0 + col_pitch / 2.0
        for c in range(panel_cols + 1):
            px = x0 + (c - 0.5) * col_pitch
            if abs(px) > (width - 2.0 * margin) / 2.0:
                continue
            post = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(px, by, back_t - 0.01))
                .box(post_w, bar_w, gap_behind + 0.02, centered=(True, True, False))
            )
            body = body.union(post)

    # Mounting holes at the corners (through Z, vent).
    hx = width / 2.0 - margin * 0.5
    hy = height / 2.0 - margin * 0.5
    for sx in (-hx, hx):
        for sy in (-hy, hy):
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(sx, sy, -0.5))
                .circle(2.1)
                .extrude(back_t + 1.0)
            )
            body = body.cut(hole)
    return body


def build_malice_clip():
    """A MALICE-style single-column clip: a long stiff spine that threads two PALS
    rows and locks with a hooked foot at the bottom. A lanyard hole up top and a
    weep slot in the spine keep it manifold and vented. One solid built by
    unioning the spine, the hook foot and the head."""
    spine_len = 2.0 * row_pitch + row_h + 10.0
    spine_w = row_h * 0.55
    t = strap_t + 0.8

    spine = (
        cq.Workplane("XY")
        .box(spine_w, spine_len, t, centered=(True, True, False))
    )
    spine = _fillet_z(spine, min(4.0, spine_w * 0.25))
    body = spine

    # Hooked foot at the −Y end: an L returning up +Z then back +Y to catch a row.
    foot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -spine_len / 2.0 + 4.0, 0))
        .box(spine_w, 8.0, t + row_pitch * 0.5, centered=(True, True, False))
    )
    body = body.union(foot)
    hook = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -spine_len / 2.0 + 9.0,
                                      t + row_pitch * 0.5 - t))
        .box(spine_w, 10.0, t, centered=(True, True, False))
    )
    body = body.union(hook)

    # Head at the +Y end with a lanyard hole (through Z, vents).
    lan = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, spine_len / 2.0 - 6.0, -0.5))
        .circle(min(4.0, spine_w * 0.28))
        .extrude(t + 1.0)
    )
    body = body.cut(lan)

    # Weep / flex slot in the middle of the spine (obround through, vents).
    weep = _obround_through(spine_w * 0.5, 2.4, t, cx=0.0, cy=row_pitch * 0.3)
    body = body.cut(weep)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pals_panel":
    result = build_pals_panel()
elif target_part == "malice_clip":
    result = build_malice_clip()
else:
    result = build_molle_clip()
