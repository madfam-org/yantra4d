"""
Deck Box — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A card-game deck box sized to hold a sleeved deck, with a press-/friction-fit lid.
Footprints follow the common card standards: standard (63x88), mini (41x63) and
tarot (70x120) mm.

Three parts (dispatched via `target_part`):
  * "deck_box"   — a single-deck box with a friction lid (base + lid built together,
                   the lid sitting alongside the base for one-plate printing).
  * "token_tray" — a shallow open tray for tokens / dice / counters, sized to the
                   same card footprint so it stacks in a game box.
  * "dual_deck"  — a wider box with a central divider that holds two decks.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `card`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.

Watertight strategy: every part is a solid outer block with a BLIND interior cavity
cut from the top (a cup) — a single closed manifold. The lid is a plate plus a
hollow downward skirt (a closed shell) placed beside the base. The dual-deck divider
is a solid wall unioned into the floor. No sphere-tangent unions; hollows stay open
at the top only.
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


# ── Card footprints (mm): (width, height) of a sleeved-ready card. ───────────
_CARDS = {
    "standard": (63.0, 88.0),
    "mini": (41.0, 63.0),
    "tarot": (70.0, 120.0),
}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "deck_box"))   # deck_box|token_tray|dual_deck
card        = str(PARAM(lambda: card,         "standard"))  # standard|mini|tarot

deck_count  = int(  PARAM(lambda: deck_count,   80))   # cards to fit (sets interior height)
per_card    = float(PARAM(lambda: per_card,    0.55))  # mm per sleeved card (thickness budget)
clearance   = float(PARAM(lambda: clearance,   1.5))   # per-side gap around the cards (mm)
wall        = float(PARAM(lambda: wall,        2.0))   # wall thickness (mm)
floor       = float(PARAM(lambda: floor,       2.0))   # floor thickness (mm)
corner_r    = float(PARAM(lambda: corner_r,    3.0))   # outer corner radius (mm)

lid_h       = float(PARAM(lambda: lid_h,       18.0))  # friction-lid skirt height (mm)
lid_clear   = float(PARAM(lambda: lid_clear,   0.35))  # lid-to-wall clearance (print fit)

tray_h      = float(PARAM(lambda: tray_h,      22.0))  # token tray interior height (mm)
tray_div    = int(  PARAM(lambda: tray_div,     1))    # token tray dividers (compartments-1)

# ── Clamp to sane ranges so extreme UI values still build watertight. ────────
deck_count  = max(10, min(deck_count, 400))
per_card    = max(0.3, min(per_card, 1.2))
clearance   = max(0.5, min(clearance, 5.0))
wall        = max(1.2, min(wall, 5.0))
floor       = max(1.2, min(floor, 6.0))
lid_h       = max(6.0, min(lid_h, 40.0))
lid_clear   = max(0.15, min(lid_clear, 0.8))
tray_h      = max(8.0, min(tray_h, 60.0))
tray_div    = max(0, min(tray_div, 6))


def _card_dims():
    if card in _CARDS:
        return _CARDS[card]
    return _CARDS["standard"]


# ── Cup builder (solid block with a blind top cavity) ────────────────────────
def _cup(inner_w, inner_d, inner_h, w, floor_t, rad):
    """A watertight cup: outer rounded block minus a blind interior cavity."""
    outer_w = inner_w + 2.0 * w
    outer_d = inner_d + 2.0 * w
    outer_h = inner_h + floor_t
    rad = max(0.0, min(rad, min(outer_w, outer_d) / 2.0 - 0.01))

    body = cq.Workplane("XY").box(outer_w, outer_d, outer_h, centered=(True, True, False))
    if rad > 0.05:
        try:
            body = body.edges("|Z").fillet(rad)
        except Exception:
            pass
    cavity = (
        cq.Workplane("XY").workplane(offset=floor_t)
        .box(inner_w, inner_d, inner_h + 1.0, centered=(True, True, False))
    )
    inner_r = max(0.0, rad - w)
    if inner_r > 0.05:
        try:
            cavity = cavity.edges("|Z").fillet(inner_r)
        except Exception:
            pass
    return body.cut(cavity), outer_w, outer_d, outer_h


def _friction_lid(inner_w, inner_d, w, floor_t, rad, height, place_x):
    """A friction lid: a top plate + a hollow downward skirt that nests inside the
    box walls with `lid_clear` on each side. Placed at x=place_x for flat printing."""
    outer_w = inner_w + 2.0 * w
    outer_d = inner_d + 2.0 * w
    plate = cq.Workplane("XY").box(outer_w, outer_d, floor_t, centered=(True, True, False))
    prad = max(0.0, min(rad, min(outer_w, outer_d) / 2.0 - 0.01))
    if prad > 0.05:
        try:
            plate = plate.edges("|Z").fillet(prad)
        except Exception:
            pass

    skirt_w = inner_w - 2.0 * lid_clear
    skirt_d = inner_d - 2.0 * lid_clear
    skirt_wall = max(1.2, w - 0.4)
    skirt_outer = cq.Workplane("XY").box(skirt_w, skirt_d, height, centered=(True, True, False))
    skirt_inner = cq.Workplane("XY").box(
        skirt_w - 2.0 * skirt_wall, skirt_d - 2.0 * skirt_wall, height + 1.0,
        centered=(True, True, False),
    )
    skirt = skirt_outer.cut(skirt_inner).translate((0, 0, -height))
    lid = plate.union(skirt)
    return lid.translate((place_x, 0, height))   # lift so skirt tip sits at z=0


# ── Part builders ────────────────────────────────────────────────────────────
def build_deck_box():
    cw, ch = _card_dims()
    inner_w = cw + 2.0 * clearance
    inner_d = ch + 2.0 * clearance
    inner_h = deck_count * per_card + clearance
    box, ow, od, _oh = _cup(inner_w, inner_d, inner_h, wall, floor, corner_r)
    # Place the lid beside the base (clear gap) so both print on one plate.
    lid = _friction_lid(inner_w, inner_d, wall, floor, corner_r, lid_h, ow / 2.0 + od / 2.0 + 8.0)
    return box.union(lid)


def build_token_tray():
    cw, ch = _card_dims()
    inner_w = cw + 2.0 * clearance
    inner_d = ch + 2.0 * clearance
    box, _ow, _od, _oh = _cup(inner_w, inner_d, tray_h, wall, floor, corner_r)
    if tray_div > 0:
        step = inner_d / (tray_div + 1)
        div_t = max(1.2, wall - 0.4)
        walls = None
        for i in range(1, tray_div + 1):
            y = -inner_d / 2.0 + i * step
            dv = (
                cq.Workplane("XY").workplane(offset=floor)
                .center(0, y).box(inner_w, div_t, tray_h, centered=(True, True, False))
            )
            walls = dv if walls is None else walls.union(dv)
        if walls is not None:
            box = box.union(walls)
    return box


def build_dual_deck():
    cw, ch = _card_dims()
    single_w = cw + 2.0 * clearance
    inner_d = ch + 2.0 * clearance
    inner_h = deck_count * per_card + clearance
    div_t = max(1.6, wall)
    inner_w = 2.0 * single_w + div_t          # two decks + a central divider
    box, _ow, _od, _oh = _cup(inner_w, inner_d, inner_h, wall, floor, corner_r)
    divider = (
        cq.Workplane("XY").workplane(offset=floor)
        .center(0, 0).box(div_t, inner_d, inner_h, centered=(True, True, False))
    )
    return box.union(divider)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "token_tray":
    result = build_token_tray()
elif target_part == "dual_deck":
    result = build_dual_deck()
else:
    result = build_deck_box()
