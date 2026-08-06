"""
Door Reinforcement / Strike Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A parametric door strike plate: the flat metal plate mortised into the door jamb
that the latch bolt or deadbolt seats into. Three distinct strikes are generated:

  - latch_strike   : full-lip strike plate for a spring latch (curved latch bore
                     open to the jamb face, radiused lip, two countersunk screws).
  - deadbolt_strike: round-corner deadbolt strike (a 1 in / 25.4 mm bolt bore,
                     1-1/8 in x 2-1/4 in body, two screws) — the classic deadbolt
                     strike geometry.
  - box_strike     : high-security box strike / reinforcer with a recessed pocket
                     and four long screw bores reaching into the wall stud.

Dimensionally real (ANSI/BHMA A156.2 residential strike hardware):
  - full-lip strike body   = 1-1/8 in x 2-1/4 in  (28.58 x 57.15 mm)
  - screw hole spacing      = 2-1/4 in (57.15 mm) tall body, holes on the vertical
                              centreline at the ANSI A156.2 T-strike spacing
                              (2-1/8 in / 53.98 mm center-to-center is common;
                              here derived from body length so it stays in-plate).
  - deadbolt bolt bore      = 1 in (25.40 mm) diameter, round-corner body
  - corner radius           = ~1/8 in (3.2 mm) rounded corners
  - screws                  = #8/#10 wood screws (4.2 mm shank, ~8 mm head)

Watertight strategy:
  Every strike is a filleted rectangular blank. Screw bores, the latch/deadbolt
  bore and the box pocket are all through- or open-to-a-face cuts (they vent to
  outside — no sealed cavity). Fillets are applied to the CLEAN blank BEFORE any
  feature is cut (filleting a feature-laden solid crashes OCCT clean()). The curved
  latch lip is a boolean of overlapping solids, never a revolve of a cut profile.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals (e.g. `target_part`).
  - Read them via PARAM(lambda: <name>, <default>) — globals()/eval/getattr are
    NOT exposed by the sandbox builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError raised for an unbound param name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (ANSI/BHMA A156.2 residential strike hardware) ────────────────
target_part = str(PARAM(lambda: target_part, "latch_strike"))
# "latch_strike" | "deadbolt_strike" | "box_strike"

plate_w = float(PARAM(lambda: plate_w, 28.58))    # plate width  (X) — 1-1/8 in
plate_h = float(PARAM(lambda: plate_h, 57.15))    # plate height (Y) — 2-1/4 in
plate_t = float(PARAM(lambda: plate_t, 3.0))      # plate thickness (Z)

bolt_bore_d = float(PARAM(lambda: bolt_bore_d, 25.40))   # deadbolt bore Ø — 1 in
latch_bore_w = float(PARAM(lambda: latch_bore_w, 16.0))  # spring-latch mouth width
screw_d = float(PARAM(lambda: screw_d, 4.2))      # #8/#10 wood-screw shank Ø
screw_head_d = float(PARAM(lambda: screw_head_d, 8.4))   # countersink head Ø
corner_r = float(PARAM(lambda: corner_r, 3.2))    # rounded corner radius (~1/8 in)
box_screw_d = float(PARAM(lambda: box_screw_d, 4.8))     # box-strike long screw Ø

# Clamp to sane ranges so extreme UI values never crash the kernel.
plate_w = max(20.0, min(plate_w, 60.0))
plate_h = max(40.0, min(plate_h, 130.0))
plate_t = max(1.6, min(plate_t, 8.0))
bolt_bore_d = max(10.0, min(bolt_bore_d, min(plate_w, plate_h) - 6.0))
latch_bore_w = max(8.0, min(latch_bore_w, plate_w - 6.0))
screw_d = max(2.5, min(screw_d, 8.0))
screw_head_d = max(screw_d + 2.0, min(screw_head_d, plate_w - 3.0))
corner_r = max(1.0, min(corner_r, min(plate_w, plate_h) / 4.0))
box_screw_d = max(3.0, min(box_screw_d, 8.0))


# ── Primitives ───────────────────────────────────────────────────────────────
def _blank(w, h, t):
    """A filleted rectangular plate, base at z=0, centred on X/Y. Fillet the CLEAN
    blank BEFORE any feature is cut (OCCT clean() dislikes filleting feature-laden
    solids). Vertical edges get the corner radius."""
    p = (
        cq.Workplane("XY")
        .box(w, h, t, centered=(True, True, False))
    )
    try:
        p = p.edges("|Z").fillet(min(corner_r, w / 2.0 - 0.5, h / 2.0 - 0.5))
    except Exception:
        pass
    return p


def _screw_hole(cx, cy, t):
    """A counterbored wood-screw hole: a through shank bore plus a shallow conical
    countersink open to the top face. Both vent to outside (no trapped void)."""
    shank = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, -0.5))
        .circle(screw_d / 2.0)
        .extrude(t + 1.0)
    )
    # Countersink: a truncated cone widening to the top face.
    csk_depth = min(t * 0.6, (screw_head_d - screw_d) / 2.0 + 0.4)
    csk = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(cx, cy, t - csk_depth))
        .circle(screw_d / 2.0)
        .workplane(offset=csk_depth + 0.01)
        .circle(screw_head_d / 2.0)
        .loft(combine=True)
    )
    return shank, csk


def _two_screws(t):
    """Return the two on-centreline screw cuts (top + bottom), at the ANSI-style
    spacing derived from the plate length so they always sit inside the plate."""
    off = plate_h / 2.0 - max(screw_head_d / 2.0 + 1.5, corner_r + 2.0)
    cuts = []
    for cy in (off, -off):
        cuts.extend(_screw_hole(0.0, cy, t))
    return cuts


# ── Part builders ────────────────────────────────────────────────────────────
def build_latch_strike():
    """A full-lip spring-latch strike: the plate with a curved latch mouth open to
    the +X (jamb) edge and a raised radiused lip that the latch bolt ramps over.
    Two countersunk screws on the vertical centreline."""
    body = _blank(plate_w, plate_h, plate_t)

    # Latch mouth: an obround pocket open to the +X edge (vents to outside). Built
    # as a slot bored from above through the full thickness, its outer end past the
    # +X face so the mouth opens to the jamb.
    mouth_len = plate_w * 0.7
    mouth = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(plate_w / 2.0 - mouth_len / 2.0 + 0.5, 0, -0.5))
        .slot2D(mouth_len + plate_w, latch_bore_w, angle=0)
        .extrude(plate_t + 1.0)
    )
    body = body.cut(mouth)

    # Curved return lip: a quarter-round rib on the -X (back-of-jamb) side that the
    # latch ramps against. Boolean of an overlapping box minus a cylinder — never a
    # revolve of a cut profile.
    lip_h = min(plate_t * 1.6, 5.0)
    rib = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(-plate_w / 2.0 + lip_h / 2.0, 0, 0))
        .box(lip_h, latch_bore_w + 6.0, plate_t + lip_h, centered=(True, True, False))
    )
    round_cut = (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, plate_t + lip_h, -plate_w / 2.0 + lip_h))
        .circle(lip_h)
        .extrude(plate_w, both=True)
    )
    rib = rib.cut(round_cut)
    # Clip rib to the plate footprint so it bonds flush, then union (overlaps into
    # shared plate material → solid weld).
    rib = rib.intersect(
        cq.Workplane("XY").box(plate_w, plate_h, plate_t + lip_h, centered=(True, True, False))
    )
    body = body.union(rib)

    for c in _two_screws(plate_t):
        body = body.cut(c)
    return body


def build_deadbolt_strike():
    """The classic round-corner deadbolt strike: a 1 in (25.4 mm) bolt bore through
    the plate and two countersunk screws. The plate is the ANSI 1-1/8 x 2-1/4 in
    body with rounded corners."""
    body = _blank(plate_w, plate_h, plate_t)

    # Deadbolt bore: a full-thickness circular hole (vents both faces).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(bolt_bore_d / 2.0)
        .extrude(plate_t + 1.0)
    )
    body = body.cut(bore)

    for c in _two_screws(plate_t):
        body = body.cut(c)
    return body


def build_box_strike():
    """A high-security box strike / reinforcer: a thicker plate with a recessed
    bolt pocket (open to the +X jamb edge and to the top) and FOUR long screw bores
    that would reach past the jamb into the wall stud. All cuts vent to a face."""
    t = plate_t + 2.0
    body = _blank(plate_w, plate_h, t)

    # Recessed bolt pocket open to the +X edge and to the top face (vented twice).
    pocket_depth = t * 0.7
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(plate_w / 2.0 - bolt_bore_d * 0.55 + 0.5,
                                      0, t - pocket_depth))
        .slot2D(bolt_bore_d + plate_w, bolt_bore_d, angle=0)
        .extrude(pocket_depth + 1.0)
    )
    body = body.cut(pocket)

    # Four long screws near the corners (box-strike anchoring into the stud).
    ox = plate_w / 2.0 - (box_screw_d / 2.0 + 2.5)
    oy = plate_h / 2.0 - (box_screw_d / 2.0 + 3.5)
    for cx in (ox, -ox):
        for cy in (oy, -oy):
            hole = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(cx, cy, -0.5))
                .circle(box_screw_d / 2.0)
                .extrude(t + 1.0)
            )
            body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "deadbolt_strike":
    result = build_deadbolt_strike()
elif target_part == "box_strike":
    result = build_box_strike()
else:
    result = build_latch_strike()
