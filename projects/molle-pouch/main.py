"""
MOLLE Utility Pouch Clip — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Attachment hardware and a small pouch body for the MOLLE / PALS webbing grid.
PALS is the open military webbing standard (MIL-W-17337 / A-A-55301): 1 in
(25.4 mm) webbing in horizontal rows on a 1 in (25.4 mm) vertical pitch, bartacked
at 1.5 in (38.1 mm) column intervals. This cartridge lets you hang your own gear
off MOLLE and grows the webbing-strap family alongside molle-clip and paracord-jig.

Three modes, each its own studio part (a single manifold solid):
  * pouch_body — a small open-top utility pouch (a hollowed box) with an integrated
                 PALS-weave back so the pouch itself threads onto a MOLLE field.
  * pouch_clip — a stiff attachment clip that threads two PALS rows and locks with a
                 hooked foot; a wide slot near the head lets a soft pouch's own
                 webbing loop pass through, joining the pouch to the grid.
  * belt_loop  — a webbing belt loop (open channel that slips over a 20-50 mm belt)
                 carrying a short PALS field on the front, so a MOLLE pouch rides on
                 a plain belt.

Watertight strategy:
  Every part is ONE solid built by UNIONING overlapping solids — the pouch is a box
  minus an open-top cavity (vents to outside); the clip is a spine + hook + head
  with through-slots (obround, vent); the belt loop is a channel whose slot opens
  to outside. No sealed cavity ever forms. Fillets clean blanks BEFORE cuts, in
  try/except.

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
target_part = str(PARAM(lambda: target_part, "pouch_body"))
# "pouch_body" | "pouch_clip" | "belt_loop"

row_h = float(PARAM(lambda: row_h, 25.4))          # 1 in webbing width / row height
row_pitch = float(PARAM(lambda: row_pitch, 25.4))  # 1 in row-to-row vertical pitch
strap_t = float(PARAM(lambda: strap_t, 2.6))       # clip / back material thickness

pouch_w = float(PARAM(lambda: pouch_w, 80.0))      # pouch width  (X, mm)
pouch_d = float(PARAM(lambda: pouch_d, 35.0))      # pouch depth  (Y out from wall, mm)
pouch_h = float(PARAM(lambda: pouch_h, 60.0))      # pouch height (Z, mm)
wall = float(PARAM(lambda: wall, 2.4))             # pouch wall thickness (mm)

weave_rows = int(round(float(PARAM(lambda: weave_rows, 2))))  # PALS rows the back spans
belt_w = float(PARAM(lambda: belt_w, 38.0))        # belt webbing width the loop fits (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
row_h = max(18.0, min(row_h, 32.0))
row_pitch = max(18.0, min(row_pitch, 40.0))
strap_t = max(1.6, min(strap_t, 4.0))
pouch_w = max(30.0, min(pouch_w, 160.0))
pouch_d = max(18.0, min(pouch_d, 90.0))
pouch_h = max(25.0, min(pouch_h, 140.0))
wall = max(1.6, min(wall, 6.0))
weave_rows = max(1, min(weave_rows, 5))
belt_w = max(20.0, min(belt_w, 55.0))


# ── Shared helpers ───────────────────────────────────────────────────────────
def _fillet_z(solid, r):
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


def _obround_z(length, width, thickness, cx=0.0, cy=0.0, z0=-0.5):
    """Stadium/obround through-solid cut tool along Z, long axis along X."""
    overall = max(width + 0.001, length)
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, z0))
        .slot2D(overall, width, angle=0)
        .extrude(thickness + 1.0)
    )


def pals_back(width, height, base_t):
    """A rigid PALS/MOLLE back field: a backing plate (in the XY plane, base at
    z=0, extruded +Z to base_t) with solid horizontal webbing bars standing off it
    on posts, on a 1 in vertical pitch. Loops are the open gaps → no trapped void.
    Returns the solid. `width` spans X, `height` spans Z-equivalent... here the
    field lies in the XZ plane wrapped onto the pouch back, so we build it flat and
    the caller orients it. Built flat in XY: X=width, Y=height, +Z=depth."""
    bar_h = row_h * 0.62
    gap_behind = strap_t + 1.0
    back = (
        cq.Workplane("XY")
        .box(width, height, base_t, centered=(True, True, False))
    )
    back = _fillet_z(back, min(4.0, width * 0.05))
    body = back
    n = max(1, weave_rows)
    total = (n - 1) * row_pitch
    y0 = -total / 2.0
    for i in range(n):
        by = y0 + i * row_pitch
        if abs(by) > height / 2.0 - bar_h / 2.0 - 1.0:
            by = max(-(height / 2.0 - bar_h / 2.0 - 1.0),
                     min(by, height / 2.0 - bar_h / 2.0 - 1.0))
        bar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, by, base_t + gap_behind))
            .box(width - 8.0, bar_h, strap_t, centered=(True, True, False))
        )
        body = body.union(bar)
        # two bartack posts bridging the bar to the back.
        for px in (-(width - 8.0) / 2.0 + 5.0, (width - 8.0) / 2.0 - 5.0):
            post = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(px, by, base_t - 0.01))
                .box(7.0, bar_h, gap_behind + 0.02, centered=(True, True, False))
            )
            body = body.union(post)
    return body.clean()


# ── Part builders ─────────────────────────────────────────────────────────────
def build_pouch_body():
    """An open-top utility pouch: a box hollowed from the top, with a PALS-weave
    field on its back wall so the pouch threads onto a MOLLE field. The cavity
    opens to the top (vents), the weave loops open to outside → one manifold solid.
    Layout: back wall in the XZ plane at y=0; the box body projects +Y; the weave
    bars project -Y behind the back."""
    # Outer box: X=pouch_w, Y=pouch_d, Z=pouch_h, back face at y=0.
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, pouch_d / 2.0, pouch_h / 2.0))
        .box(pouch_w, pouch_d, pouch_h)
    )
    outer = _fillet_z(outer, min(6.0, pouch_w * 0.05))
    # Cavity open at the top: leave a floor and walls of `wall`.
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, pouch_d / 2.0, wall + pouch_h / 2.0))
        .box(pouch_w - 2.0 * wall, pouch_d - 2.0 * wall, pouch_h)
    )
    body = outer.cut(cavity)
    # PALS weave field on the back wall (behind y=0), built flat then rotated so
    # its plate lies in the XZ plane against the pouch back and bars project -Y.
    field_h = min(pouch_h - 8.0, (weave_rows + 0.6) * row_pitch)
    field = pals_back(pouch_w - 6.0, field_h, wall)
    # Rotate flat XY field (X=width, Y=height, +Z=depth) so height -> +Z and
    # depth -> -Y (behind the pouch).
    field = field.rotate((0, 0, 0), (1, 0, 0), 90)   # Y->+Z, +Z->-Y (right-hand)
    field = field.translate((0, 0.0, pouch_h / 2.0))
    body = body.union(field)
    return body.clean()


def build_pouch_clip():
    """A stiff MOLLE attachment clip: a long spine that threads two PALS rows and
    locks with a hooked foot; a wide slot near the head passes a soft pouch's own
    webbing loop, joining pouch to grid. One solid: spine + hook + head, with
    obround through-slots that vent."""
    spine_w = row_h * 0.7
    spine_len = 2.0 * row_pitch + row_h + 14.0
    t = strap_t + 1.0

    spine = (
        cq.Workplane("XY")
        .box(spine_w, spine_len, t, centered=(True, True, False))
    )
    spine = _fillet_z(spine, min(4.0, spine_w * 0.2))
    body = spine

    # Hooked foot at the -Y end (an L returning up +Z then a lip toward +Y).
    foot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -spine_len / 2.0 + 5.0, 0))
        .box(spine_w, 10.0, t + row_pitch * 0.55, centered=(True, True, False))
    )
    body = body.union(foot)
    lip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -spine_len / 2.0 + 11.0, row_pitch * 0.55))
        .box(spine_w, 11.0, t, centered=(True, True, False))
    )
    body = body.union(lip)

    # Wide pouch-webbing slot near the head (+Y): an obround the pouch loop threads.
    slot = _obround_z(spine_w * 0.6, 4.0, t, cx=0.0, cy=spine_len / 2.0 - 12.0)
    body = body.cut(slot)
    # A weave/lightening slot mid-spine (vents).
    weep = _obround_z(spine_w * 0.5, 3.0, t, cx=0.0, cy=0.0)
    body = body.cut(weep)
    return body.clean()


def build_belt_loop():
    """A webbing belt loop with a short PALS field on the front, so a MOLLE pouch
    rides on a plain 20-50 mm belt. The loop is a flat back panel + a U bridge that
    the belt threads behind; the U opening vents to outside. The PALS field sits on
    the front face."""
    panel_w = max(belt_w + 16.0, row_h + 10.0)
    panel_h = max((weave_rows + 0.8) * row_pitch, belt_w + 20.0)
    base_t = max(3.0, wall)

    # Back panel in the XZ plane: base at y=0, extruded +Y = base_t. Build flat in
    # XY (X=width, Y=height) then rotate so height->+Z.
    field = pals_back(panel_w, panel_h, base_t)   # bars project +Z(depth) initially
    field = field.rotate((0, 0, 0), (1, 0, 0), 90)  # height->+Z, depth->-Y
    field = field.translate((0, 0, panel_h / 2.0))
    body = field

    # Belt bridge: a flat bar spanning across the back, standing off in -Y to form
    # a channel the belt threads. It bridges left-right, leaving a belt_w gap in Z.
    gap = strap_t + 3.0                      # belt thickness clearance
    bridge_z0 = panel_h / 2.0 - belt_w / 2.0
    for zc in (bridge_z0, panel_h / 2.0 + belt_w / 2.0):
        bar = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, -gap - strap_t / 2.0, zc))
            .box(panel_w, strap_t, 8.0, centered=(True, True, True))
        )
        body = body.union(bar)
    # Two side webs closing the channel ends into the panel (leaves front/back open
    # so the belt slides through → vents).
    for sx in (-panel_w / 2.0 + strap_t / 2.0, panel_w / 2.0 - strap_t / 2.0):
        web = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx, -gap / 2.0 - strap_t / 2.0, panel_h / 2.0))
            .box(strap_t, gap + strap_t, belt_w + 8.0, centered=(True, True, True))
        )
        body = body.union(web)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "pouch_clip":
    result = build_pouch_clip()
elif target_part == "belt_loop":
    result = build_belt_loop()
else:
    result = build_pouch_body()
