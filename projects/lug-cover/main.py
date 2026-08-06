"""
Battery Terminal / Lug Cover — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Insulating covers and boots for battery terminals, threaded studs and bolted lug
joints — the short-circuit and accidental-contact protection that keeps a dropped
spanner off a live post. The pocket lands on standard post / stud / lug sizes, so
a printed boot seats over a real terminal and its ring lug. Pick the terminal type
and the cover shrouds it with a cable-exit notch.

Modes are dispatched via `target_part`:
  * "post_cover" — a snap boot over a tapered automotive battery POST + ring lug:
                   an open-bottom domed pocket with a cable-exit notch.
  * "stud_boot"  — an insulating boot over an M8/M10 threaded STUD terminal and
                   its ring lug: a cylindrical open-bottom socket with a top hole.
  * "bar_boot"   — a cover over a bolted bus-LUG / link joint: a rectangular
                   open-bottom pocket with two cable-exit notches.

Standards encoded (mm):
  Automotive SAE tapered post top Ø: positive ~17.5, negative ~15.9 (post height
  ~19). Ring-lug stud sizes: M8 (8), M10 (10). Ring-lug body Ø ~ 20-24 for those.

Watertightness: every cover is a solid, filleted blank with a pocket cut that
OPENS to the bottom face (never a sealed cavity); the top is closed by `wall`. The
domed post_cover uses a flat-topped frustum loft (no sphere/pole apex crack).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `terminal`).
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


# ── Standard terminal dimensions (mm) ────────────────────────────────────────
_POSTS = {
    "positive": {"top_d": 17.5, "post_h": 19.0},   # SAE automotive positive post
    "negative": {"top_d": 15.9, "post_h": 19.0},   # SAE automotive negative post
}
_STUDS = {
    "M8":  {"stud_d": 8.0,  "lug_d": 20.0},
    "M10": {"stud_d": 10.0, "lug_d": 24.0},
}


def post_spec(name):
    return _POSTS.get(str(name).strip().lower(), _POSTS["positive"])


def stud_spec(name):
    return _STUDS.get(str(name).strip().upper(), _STUDS["M8"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "post_cover"))
terminal    = str(PARAM(lambda: terminal, "positive"))   # positive|negative (post)
stud        = str(PARAM(lambda: stud, "M8"))             # M8|M10 (stud/bar)
clearance   = float(PARAM(lambda: clearance, 0.6))       # pocket clearance per side (mm)
wall        = float(PARAM(lambda: wall, 2.4))            # cover wall thickness (mm)
cover_h     = float(PARAM(lambda: cover_h, 26.0))        # cover height (mm)
lug_len     = float(PARAM(lambda: lug_len, 30.0))        # ring-lug body reach (mm)
notch_w     = float(PARAM(lambda: notch_w, 12.0))        # cable-exit notch width (mm)

# Clamp to sane ranges.
clearance = max(0.2, min(clearance, 1.5))
wall = max(1.6, min(wall, 5.0))
cover_h = max(10.0, min(cover_h, 60.0))
lug_len = max(12.0, min(lug_len, 70.0))
notch_w = max(4.0, min(notch_w, 30.0))


# ── Part builders ─────────────────────────────────────────────────────────────
def build_post_cover():
    """Snap boot over a tapered automotive post + ring lug: an open-bottom pocket
    with a closed, rim-filleted roof and a cable-exit skirt toward the lug."""
    spec = post_spec(terminal)
    post_top_r = spec["top_d"] / 2.0
    # Cavity must clear the post base (wider than the top) + the ring lug seat.
    cav_r = post_top_r + clearance + 2.0
    outer_r = cav_r + wall
    body_h = cover_h

    # Body: a straight cylinder (full outer_r) up to the top. A domed frustum
    # whose top radius is smaller than the cavity would let the pocket punch
    # through the roof wall and sever the cap — so the wall stays full-radius and
    # the top is merely eased with a fillet after cutting.
    body = cq.Workplane("XY").circle(outer_r).extrude(body_h)
    # Ease the top rim on the clean blank BEFORE any feature cut/union.
    try:
        body = body.edges(">Z").fillet(min(outer_r * 0.25, 3.0))
    except Exception:
        pass

    # Skirt: a rectangular lug shroud that reaches out one side toward the ring
    # lug. It PASSES THROUGH the cylinder center (spans y = +outer_r/2 down to
    # -(outer_r + lug_len)) so the union is deeply volumetric — never a tangent
    # kiss on the round wall.
    skirt_h = body_h * 0.55
    skirt_y_far = -(outer_r + lug_len)
    skirt_y_near = outer_r * 0.5
    skirt_len = skirt_y_near - skirt_y_far
    skirt_yc = (skirt_y_near + skirt_y_far) / 2.0
    skirt = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, skirt_yc, 0))
        .box(notch_w + 2.0 * wall, skirt_len, skirt_h, centered=(True, True, False))
    )
    body = body.union(skirt)

    # Pocket: the round terminal pocket, opening to the bottom face, closed roof.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(cav_r).extrude(body_h - wall + 1.0)
    )
    body = body.cut(pocket)

    # Skirt cavity: hollow the shroud from below (open bottom) and open the cable
    # exit at the far end. Runs from the pocket out through the far face.
    cav_far = skirt_y_far - 1.0
    cav_near = 0.0
    cav_len = cav_near - cav_far
    cav_yc = (cav_near + cav_far) / 2.0
    skirt_cav = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, cav_yc, -1.0))
        .box(notch_w, cav_len, skirt_h - wall + 1.0, centered=(True, True, False))
    )
    body = body.cut(skirt_cav)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_stud_boot():
    """Insulating boot over an M8/M10 threaded stud + ring lug: a cylindrical
    open-bottom socket with a small top access hole (for the nut / stud tip)."""
    spec = stud_spec(stud)
    lug_r = spec["lug_d"] / 2.0
    cav_r = lug_r + clearance + 1.0
    outer_r = cav_r + wall
    body_h = cover_h

    body = cq.Workplane("XY").circle(outer_r).extrude(body_h)
    try:
        body = body.edges(">Z").fillet(min(outer_r * 0.4, 4.0))
    except Exception:
        pass

    # Pocket opens to the bottom, closed roof (wall).
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(cav_r).extrude(body_h - wall + 1.0)
    )
    body = body.cut(pocket)

    # Small top access hole (stud tip / inspection). Opens roof to the pocket ->
    # the cavity stays open to a face (bottom), never sealed.
    top_hole = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, body_h - wall - 1.0))
        .circle(spec["stud_d"] / 2.0 + clearance).extrude(wall + 2.0)
    )
    body = body.cut(top_hole)

    # Side cable-exit notch for the ring lug.
    notch = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -outer_r, -1.0))
        .box(notch_w, 2.0 * wall + 2.0, body_h * 0.5 + 1.0, centered=(True, True, False))
    )
    body = body.cut(notch)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bar_boot():
    """Cover over a bolted bus-lug / link joint: a rectangular open-bottom pocket
    with two opposed cable-exit notches (through-link)."""
    spec = stud_spec(stud)
    lug_r = spec["lug_d"] / 2.0
    inner_w = 2.0 * (lug_r + clearance) + 4.0
    inner_l = lug_len + 2.0 * clearance
    outer_w = inner_w + 2.0 * wall
    outer_l = inner_l + 2.0 * wall
    body_h = cover_h

    body = cq.Workplane("XY").box(outer_l, outer_w, body_h, centered=(True, True, False))
    try:
        body = body.edges("|Z").fillet(min(3.0, wall * 1.2))
    except Exception:
        pass

    # Pocket opens to the bottom, closed roof.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(inner_l, inner_w, body_h - wall + 1.0, centered=(True, True, False))
    )
    body = body.cut(pocket)

    # Two opposed cable-exit notches at each end (a link cover: cable in one end,
    # out the other).
    for sx in (-1.0, 1.0):
        notch = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (outer_l / 2.0), 0.0, -1.0))
            .box(2.0 * wall + 2.0, notch_w, body_h * 0.5 + 1.0, centered=(True, True, False))
        )
        body = body.cut(notch)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "post_cover": build_post_cover,
    "stud_boot": build_stud_boot,
    "bar_boot": build_bar_boot,
}

result = _dispatch.get(target_part, build_post_cover)()
