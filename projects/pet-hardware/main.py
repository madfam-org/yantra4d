"""
Pet Collar Hardware — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Printable webbing hardware for pet collars and leashes, all sized to a standard
webbing width (20 mm or 25 mm): a side-release buckle housing, a D-ring anchor
plate for a leash or tag, and a soft tag silencer that stops the ID tag from
jingling.

  * "side_buckle" — a side-release female buckle housing with a webbing slot and
                    two sprung side arms + latch windows (target_part ==
                    "side_buckle").
  * "d_ring"      — a webbing loop plate carrying an integral D-ring for clipping
                    a leash / tag (target_part == "d_ring").
  * "tag_silencer"— a two-slot flat cover that sandwiches an ID tag to mute it
                    (target_part == "tag_silencer").

Watertight strategy: the buckle housing is a solid box with a rectangular tube
cavity and latch windows cut through; the webbing slots are through-rectangles;
the D-ring is a solid torus-like ring built by revolving a circle (closed, no
axis pole). Every result is one manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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


# ── Webbing standards ─────────────────────────────────────────────────────────
WEBBING = {"20mm": 20.0, "25mm": 25.0}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "side_buckle"))  # side_buckle | d_ring | tag_silencer

webbing   = str(  PARAM(lambda: webbing, "25mm"))   # webbing width standard
web_th    = float(PARAM(lambda: web_th,   2.5))     # webbing thickness (slot height)
wall      = float(PARAM(lambda: wall,     3.0))     # housing / plate wall
clearance = float(PARAM(lambda: clearance, 0.4))    # slot / latch clearance
ring_dia  = float(PARAM(lambda: ring_dia, 22.0))    # D-ring inner size (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
web_th    = max(1.5, min(web_th, 5.0))
wall      = max(2.0, min(wall, 6.0))
clearance = max(0.0, min(clearance, 1.2))
ring_dia  = max(12.0, min(ring_dia, 45.0))

WEB_W = WEBBING.get(webbing, 25.0)
SLOT_W = WEB_W + 2.0 * clearance
SLOT_H = web_th + 2.0 * clearance


# ── Helpers ──────────────────────────────────────────────────────────────────
def webbing_slot(length_x, at_y, z0, h):
    """A through rectangular slot (cutter) for the webbing to thread, centred on
    X, at Y=`at_y`, spanning z0..z0+h."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, at_y, z0))
        .box(SLOT_W, web_th + 2.0 * clearance, h + 2.0, centered=(True, True, False))
        .translate((0, 0, -1.0))
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_side_buckle():
    """Female side-release buckle housing: a flat box whose interior is a
    rectangular tube (the male prongs slide in), with two latch windows on the
    sides and a webbing bar slot at the back."""
    body_w = SLOT_W + 2.0 * wall + 6.0    # extra for the side arms
    body_l = WEB_W * 1.9                    # length along Y
    body_h = SLOT_H + 2.0 * wall
    body = cq.Workplane("XY").box(body_w, body_l, body_h, centered=(True, True, False))

    # Hollow the front as a rectangular receiver tube for the male prongs.
    receiver = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, body_l * 0.12, wall))
        .box(SLOT_W, body_l, SLOT_H, centered=(True, True, False))
    )
    body = body.cut(receiver)

    # Latch windows: rectangular openings on each long side where the male
    # sprung arms click out.
    for sx in (-1.0, 1.0):
        win = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * body_w / 2.0, body_l * 0.05, wall))
            .box(wall * 3.0, body_l * 0.5, SLOT_H, centered=(True, True, False))
        )
        body = body.cut(win)

    # Webbing bar slot at the back (a through slot with a solid bar behind it).
    slot = webbing_slot(body_w, -body_l / 2.0 + wall + SLOT_H / 2.0 + 1.0, 0, body_h)
    body = body.cut(slot)

    # Round the outer edges for comfort (non-fatal).
    try:
        body = body.edges("|Z").fillet(min(2.0, wall * 0.6))
    except Exception:
        pass
    return body


def build_d_ring():
    """A webbing loop plate with an integral D-ring. The plate has a webbing
    slot; a D-shaped ring stands up from one edge for clipping."""
    plate_w = WEB_W + 2.0 * wall + 4.0
    plate_l = WEB_W * 1.4
    plate_h = SLOT_H + wall
    plate = cq.Workplane("XY").box(plate_w, plate_l, plate_h, centered=(True, True, False))
    # Webbing slot through the plate.
    slot = webbing_slot(plate_w, 0, 0, plate_h)
    plate = plate.cut(slot)

    # D-ring: a FLAT ring plate standing in the XZ plane at the front edge (a
    # washer = outer disc minus inner hole). A flat ring is fully watertight and
    # prints without supports, unlike a round-section torus.
    ring_r = ring_dia / 2.0
    ring_th = wall * 1.2
    ring = (
        cq.Workplane("XZ")
        .circle(ring_r + wall)
        .circle(ring_r)
        .extrude(ring_th)
    )
    # Stand it up at the front edge, base overlapping into the plate.
    ring = ring.translate((0, plate_l / 2.0 - ring_th / 2.0, ring_r + wall * 0.4))
    # A short neck welds the ring base into the plate so the union is volumetric.
    neck = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_l / 2.0 - ring_th / 2.0, 0))
        .box(ring_r, ring_th, plate_h + wall * 0.8, centered=(True, True, False))
    )
    body = plate.union(neck).union(ring)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_tag_silencer():
    """A flat two-piece-look silencer: a rounded pad with a central pocket for an
    ID tag and a slot to thread onto the collar ring, printed in a soft material
    to mute jingling. One solid: a pad with a shallow tag recess and a hang
    slot."""
    pad_d = max(ring_dia + 14.0, 34.0)
    pad_h = web_th + wall
    pad = cq.Workplane("XY").circle(pad_d / 2.0).extrude(pad_h)
    try:
        pad = pad.edges(">Z or <Z").chamfer(min(1.5, pad_h * 0.3))
    except Exception:
        pass
    # Shallow tag recess (never perforates).
    recess = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, pad_h * 0.55))
        .circle(pad_d / 2.0 - wall)
        .extrude(pad_h)
    )
    pad = pad.cut(recess)
    # Hang slot near the top edge to thread onto the collar / split ring.
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, pad_d / 2.0 - wall - 2.0, -1.0))
        .box(WEB_W * 0.5, wall * 2.0, pad_h + 2.0, centered=(True, True, False))
    )
    pad = pad.cut(slot)
    return pad


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "d_ring":
    result = build_d_ring()
elif target_part == "tag_silencer":
    result = build_tag_silencer()
else:  # "side_buckle"
    result = build_side_buckle()
