"""
Webbing Buckle & Adjusters — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Standard side-release buckle and strap adjusters for 20 / 25 / 38 mm webbing.
A two-part side-release buckle (a male half with two sprung cantilever prongs
that snap into the female housing's side apertures), a ladder-lock slider, and a
tri-glide. Every part shares ONE webbing-slot helper so the bar geometry a strap
threads through is identical across the family.

Modes (dispatched via `target_part`):
  * "side_release" — an ASSEMBLY mode building BOTH the male and female buckle
                     halves nested together (male prongs seated in the female
                     apertures) so the snap fit is visible in one render.
  * "slider"       — a strap-adjuster / ladder-lock with a central sprung bar.
  * "tri_glide"    — a tri-glide (three-bar slide) for fixing a webbing end.

Snap fit: the male's two prongs are cantilevers that flex inward while entering
the female mouth, then spring out so their barbs catch behind the female's side
windows. The prong outer span at rest is (mouth inner span), and the barbs stand
proud by `snap_ledge`; a `snap_clear` gap on every mating face keeps the printed
fit assemble-able. See build_side_release() for the exact clearances.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `webbing`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
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


# ── Parameters ───────────────────────────────────────────────────────────────
webbing     = str(  PARAM(lambda: webbing, "25mm"))     # "20mm"|"25mm"|"38mm"
web_t       = float(PARAM(lambda: web_t,      2.0))     # webbing thickness (mm)
wall        = float(PARAM(lambda: wall,       2.4))     # structural wall (mm)
snap_clear  = float(PARAM(lambda: snap_clear, 0.4))     # per-face fit clearance (mm)
snap_ledge  = float(PARAM(lambda: snap_ledge, 1.4))     # barb ledge that catches (mm)
show_gap    = float(PARAM(lambda: show_gap,   0.0))     # assembly explode gap (mm, cosmetic)

target_part = str(  PARAM(lambda: target_part, "side_release"))  # side_release|slider|tri_glide

# ── Webbing nominal widths ────────────────────────────────────────────────────
_WEB = {"20mm": 20.0, "25mm": 25.0, "38mm": 38.0}
web_w = _WEB.get(webbing, 25.0)

# ── Safe clamps ──────────────────────────────────────────────────────────────
web_t      = max(1.0, min(web_t, 4.0))
wall       = max(1.6, min(wall, 4.0))
snap_clear = max(0.2, min(snap_clear, 0.8))
snap_ledge = max(0.8, min(snap_ledge, 2.5))
slot_h = web_t + 0.6          # webbing slot height (thickness direction) + clearance


# ── Shared webbing-slot helper ────────────────────────────────────────────────
def webbing_slot(strap_w, strap_t, length, clearance):
    """A rounded prism sized to a webbing cross-section: strap WIDTH along Y,
    strap THICKNESS (the slot's short dimension) along Z, and the pass-through
    LENGTH along X. Cut this from a bar to form the slot a strap threads through.
    `clearance` widens both cross-section dims. Reused by every part so all
    webbing slots in this cartridge share one definition."""
    w = strap_w + clearance
    t = strap_t + clearance
    r = min(t / 2.0 - 0.01, 0.8)
    slot = cq.Workplane("XY").box(length, w, t, centered=(True, True, True))
    if r > 0.05:
        try:
            slot = slot.edges("|X").fillet(r)
        except Exception:
            pass
    return slot


def bar_frame(outer_w, outer_l, thick, slot_len, n_slots):
    """A flat rectangular frame (a slide body) with `n_slots` webbing slots cut
    across it, evenly spaced along its length (X). Used by slider / tri_glide.
    outer_w spans Y (strap width + walls), outer_l spans X, `thick` spans Z."""
    body = cq.Workplane("XY").box(outer_l, outer_w, thick, centered=(True, True, True))
    try:
        body = body.edges("|Z").fillet(min(thick, 2.0))
    except Exception:
        pass
    if n_slots == 1:
        xs = [0.0]
    else:
        step = (outer_l - 2.0 * wall - slot_len) / (n_slots - 1)
        start = -(step * (n_slots - 1)) / 2.0
        xs = [start + i * step for i in range(n_slots)]
    for x in xs:
        slot = webbing_slot(web_w, web_t, slot_len, 0.6)
        slot = slot.translate((x, 0, 0))
        body = body.cut(slot)
    return body


# ── Side-release buckle: female + male ───────────────────────────────────────
def _female_half():
    """The female (socket) half: a hollow box the male slides into, with two side
    windows the male barbs catch behind, and a webbing slot at the closed end.
    Built centred; its open mouth faces +X."""
    inner_w = web_w + 2.0 * snap_clear          # cavity width (male body fits in)
    inner_h = slot_h + 2.0 * snap_clear
    cav_w = inner_w + 2.0 * wall
    cav_h = inner_h + 2.0 * wall
    length = web_w * 0.9 + 10.0                 # socket depth along X

    body = cq.Workplane("XY").box(length, cav_w, cav_h, centered=(True, True, True))
    try:
        body = body.edges("|X").fillet(min(wall, 1.5))
    except Exception:
        pass

    # Hollow cavity, open at the +X mouth.
    cavity = cq.Workplane("XY").box(length, inner_w, inner_h, centered=(True, True, True))
    cavity = cavity.translate((length * 0.5, 0, 0))   # push toward +X so mouth is open
    body = body.cut(cavity)

    # Two side windows (the snap catches) on ±Y walls, near the mouth.
    win_l = snap_ledge + 1.2
    win_w = min(web_w * 0.34, 9.0)
    win_x = length * 0.5 - win_l * 0.5 - 1.0
    for sy in (-1.0, 1.0):
        win = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(win_x, sy * cav_w / 2.0, 0))
            .box(win_l, 2.0 * wall + 2.0, win_w)
        )
        body = body.cut(win)

    # Webbing slot at the closed (-X) end, strap exits along X.
    slot = webbing_slot(web_w, web_t, 3.0 * wall, 0.6)
    slot = slot.translate((-length * 0.5 + wall + 1.5, 0, 0))
    body = body.cut(slot)
    return body, length, inner_w, inner_h


def _male_half(inner_w, inner_h):
    """The male (plug) half: a webbing bar plus two sprung cantilever prongs that
    enter the female cavity and catch behind its side windows. Sized to the SAME
    cavity the female exposes, minus snap_clear per face. Built centred; prongs
    point toward +X (into the female)."""
    # Central spine bar carrying the webbing slot.
    bar_l = web_w * 0.9 + 8.0
    bar_h = inner_h - 2.0 * snap_clear
    bar_w = min(web_w * 0.5, inner_w - 2.0 * snap_clear - 4.0)   # narrow central web
    bar_w = max(bar_w, 6.0)
    body = cq.Workplane("XY").box(bar_l, web_w + 2.0 * wall, bar_h, centered=(True, True, True))
    # Webbing slot at the -X end of the bar.
    slot = webbing_slot(web_w, web_t, 3.0 * wall, 0.6)
    slot = slot.translate((-bar_l * 0.5 + wall + 1.5, 0, 0))
    body = body.cut(slot)

    # Two prongs from the +X face of the bar. Their OUTER faces sit at
    # ±(inner_w/2 - snap_clear) so they ride the cavity walls; barbs add snap_ledge.
    prong_reach = web_w * 0.9 + 6.0
    prong_t = max(1.6, wall)                       # prong thickness (flex direction = Y)
    prong_h = bar_h - 2.0 * snap_clear
    outer_y = inner_w / 2.0 - snap_clear
    for sy in (-1.0, 1.0):
        py = sy * (outer_y - prong_t / 2.0)
        prong = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(bar_l * 0.5, py, 0))
            .box(prong_reach, prong_t, prong_h, centered=(False, True, True))
        )
        # Barb: a small block on the prong's outer face near the tip that catches
        # behind the female window.
        barb = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(bar_l * 0.5 + prong_reach - snap_ledge - 1.5, sy * (outer_y + snap_ledge / 2.0), 0))
            .box(snap_ledge + 1.4, snap_ledge, min(web_w * 0.3, 8.0), centered=(True, True, True))
        )
        body = body.union(prong).union(barb)
    return body, bar_l, prong_reach


def build_side_release():
    """Assemble the female and male halves nested together. The male is placed so
    its prong tips reach into the female cavity and its barbs sit at the female
    windows — the visible snap engagement. `show_gap` can slide the male out for
    an exploded view."""
    female, f_len, inner_w, inner_h = _female_half()
    male, bar_l, prong_reach = _male_half(inner_w, inner_h)

    # Female mouth faces +X, centred at x=0 (mouth plane at x=+f_len/2).
    # Place the male on the +X side so its prongs (pointing +X) insert into the
    # female mouth (which is at +X of the female). Flip the male 180° about Z so
    # its prongs point -X toward the female.
    male = male.rotate((0, 0, 0), (0, 0, 1), 180)
    # Now male prongs point -X. Seat it so prong tips overlap the female cavity.
    male_x = f_len * 0.5 + bar_l * 0.5 - prong_reach * 0.85 + show_gap
    male = male.translate((male_x, 0, 0))

    asm = cq.Assembly()
    asm.add(female, name="female", color=cq.Color(0.29, 0.44, 0.54))
    asm.add(male, name="male", color=cq.Color(0.55, 0.71, 0.78))
    return asm


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "slider":
    outer_w = web_w + 2.0 * wall
    outer_l = web_w * 0.7 + 4.0 * wall
    result = bar_frame(outer_w, outer_l, slot_h + 2.0 * wall, min(web_w * 0.8, web_w), 1)
elif target_part == "tri_glide":
    outer_w = web_w + 2.0 * wall
    outer_l = web_w * 0.55 + 3.0 * wall
    # tri-glide = three bars => two slots.
    result = bar_frame(outer_w, outer_l, slot_h + 2.0 * wall, web_w * 0.42, 2)
else:
    result = build_side_release()
