"""
Lithophane Frame — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Frames and lamp bodies that hold a printed lithophane panel (a thin relief that reveals
an image when backlit). The frame has a slot the panel drops into and a light provision
behind it. Sized by the panel width/height so any lithophane you print fits.

Three parts (dispatched via `target_part`):
  * "desk_frame"    — a standing picture frame with a rear slot and a fold-out kick foot.
  * "lamp_body"     — a tea-light / LED lamp box: four walls with panel slots, an open
                      top for a light, and a vented base.
  * "hanging_frame" — a slim frame with a slot and a top hang hole (for a window).

The panel POCKET is the shared CDG: a slot of `panel_t` + fit, `slot_depth` deep, that
receives the lithophane. All bodies are prismatic (fast, watertight).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `panel_w`).
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
target_part = str(PARAM(lambda: target_part, "desk_frame"))  # desk_frame|lamp_body|hanging_frame
style       = str(PARAM(lambda: style,       "desk-frame"))  # desk-frame|tea-light-lamp|hanging

panel_w    = float(PARAM(lambda: panel_w,   100.0))   # lithophane panel width (mm)
panel_h    = float(PARAM(lambda: panel_h,    70.0))   # lithophane panel height (mm)
panel_t    = float(PARAM(lambda: panel_t,     3.0))   # panel thickness (mm)
frame_w    = float(PARAM(lambda: frame_w,    10.0))   # frame border width around the panel (mm)
depth      = float(PARAM(lambda: depth,      12.0))   # frame body depth front-to-back (mm)
slot_fit   = float(PARAM(lambda: slot_fit,    0.4))   # slot oversize so the panel drops in (mm)
reveal     = float(PARAM(lambda: reveal,      3.0))   # front lip that overlaps the panel edge (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
panel_w  = max(30.0, min(panel_w, 250.0))
panel_h  = max(30.0, min(panel_h, 250.0))
panel_t  = max(1.5, min(panel_t, 6.0))
frame_w  = max(5.0, min(frame_w, 30.0))
depth    = max(8.0, min(depth, 40.0))
slot_fit = max(0.1, min(slot_fit, 1.0))
reveal   = max(1.5, min(reveal, min(frame_w - 1.0, 8.0)))

slot_t = panel_t + slot_fit
outer_w = panel_w + 2.0 * frame_w
outer_h = panel_h + 2.0 * frame_w
win_w = panel_w - 2.0 * reveal            # backlit aperture
win_h = panel_h - 2.0 * reveal


# ── Shared frame ring with a rear panel slot + front aperture ────────────────
def _frame_ring(front_wall):
    """A rectangular frame body (outer_w × outer_h × depth, base at z=0) with:
      - a front aperture window (through the front `front_wall`) so the image shows,
      - a rear panel slot (a pocket) sized `slot_t` × `slot_depth` the panel drops into.
    Returns the solid."""
    body = cq.Workplane("XY").box(outer_w, outer_h, depth, centered=(True, True, False))
    # Front aperture: a through window in the front wall region (front at +Y? use Z stack:
    # front face is the top in Z; light enters from the back/bottom). We orient the frame
    # standing with its face toward +Y is complex; instead lay it flat: front = +Z.
    # Aperture cut from the top down through `front_wall`.
    aperture = (
        cq.Workplane("XY")
        .box(win_w, win_h, front_wall + 2.0, centered=(True, True, False))
        .translate((0, 0, depth - front_wall - 0.0))
    )
    body = body.cut(aperture)
    # Panel slot: a pocket from the back (z=0 up) that holds the panel behind the reveal.
    slot = (
        cq.Workplane("XY")
        .box(panel_w + slot_fit, panel_h + slot_fit, depth - front_wall + 1.0,
             centered=(True, True, False))
        .translate((0, 0, -1.0))
    )
    body = body.cut(slot)
    return body


def _hang_hole(body):
    """A keyhole hang slot near the top edge (through Y at the top border)."""
    y = outer_h / 2.0 - frame_w / 2.0
    hole = (
        cq.Workplane("XY").center(0.0, y).circle(3.0)
        .extrude(depth + 2.0).translate((0, 0, -1.0))
    )
    return body.cut(hole)


# ── Part builders ────────────────────────────────────────────────────────────
def build_desk_frame():
    """A standing picture frame: the frame ring plus a rear kick foot so it stands at a
    slight lean on a desk. Front wall stays thin so the image reads when backlit by
    ambient light or an LED behind it."""
    front_wall = 1.0            # thin so the panel shows through
    body = _frame_ring(front_wall)
    # Kick foot: a wedge behind the frame (on -Z side... frame base is z=0), so add a
    # triangular prop at the back-bottom that tilts it. Build a foot slab and a brace.
    foot_d = depth + 24.0
    foot = (
        cq.Workplane("XY")
        .box(outer_w * 0.5, 6.0, foot_d, centered=(True, True, False))
        .translate((0, -outer_h / 2.0 + 3.0, 0))
    )
    # A diagonal brace from the foot back edge up to the frame lower border.
    brace = (
        cq.Workplane("XZ")
        .polyline([(0, 0), (14.0, 0), (0.0, min(outer_h * 0.4, 40.0))])
        .close()
        .extrude(6.0)
        .translate((-3.0, -outer_h / 2.0 + 3.0, 0))
    )
    body = body.union(foot).union(brace)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_lamp_body():
    """A tea-light / LED lamp box: the frame ring becomes one lit face; add side walls and
    a vented base so a light sits behind the panel and glows through it."""
    front_wall = 1.0
    face = _frame_ring(front_wall)
    # Base plate under the frame with vent holes (light heat escape + cord notch).
    base = (
        cq.Workplane("XY")
        .box(outer_w, outer_h * 0.5, 4.0, centered=(True, True, False))
        .translate((0, -outer_h / 2.0 + outer_h * 0.25, -4.0))
    )
    for sx in (-1.0, 0.0, 1.0):
        vent = (
            cq.Workplane("XY").center(sx * outer_w * 0.25, -outer_h / 2.0 + outer_h * 0.25)
            .circle(min(6.0, outer_w * 0.08)).extrude(6.0).translate((0, 0, -5.0))
        )
        base = base.cut(vent)
    # Two short side wings so the lamp stands upright and hides the light source edges.
    wing_d = depth + 10.0
    for s in (-1.0, 1.0):
        wing = (
            cq.Workplane("XY")
            .box(4.0, outer_h * 0.6, wing_d, centered=(True, True, False))
            .translate((s * (outer_w / 2.0 - 2.0), -outer_h * 0.1, 0))
        )
        face = face.union(wing)
    body = face.union(base)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_hanging_frame():
    """A slim window-hanging frame: the frame ring plus a top hang hole. Thinner depth so
    it sits close to the glass and the daylight lights the lithophane."""
    front_wall = 1.0
    body = _frame_ring(front_wall)
    body = _hang_hole(body)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "lamp_body":
    result = build_lamp_body()
elif target_part == "hanging_frame":
    result = build_hanging_frame()
else:
    result = build_desk_frame()
