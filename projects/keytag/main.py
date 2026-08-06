"""
Keychain / Tag — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A flat keychain tag with an embossed or debossed name/number and a ring hole. The
personalization gateway: pick a shape, type a label, print.

Three parts (dispatched via `target_part`):
  * "tag"        — a flat tag (rounded-rect / circle / dogtag / bone) + one text line.
  * "tag_2line"  — the same tag with a second text line.
  * "luggage_tag"— a larger tag with a strap slot (instead of a small ring hole) and
                   room for a longer label.

Text robustness (per the brief): text is applied via cq `text()` and the boolean
result is validated with `.val().isValid()`. If the requested mode (emboss/deboss)
produces an invalid solid — some accented glyphs break a debossed cut — the code
falls back to the other mode, and finally to a blank (but watertight) plate. A
missing CJK/glyph font degrades to a blank plate rather than crashing.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `shape`).
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
target_part = str(PARAM(lambda: target_part, "tag"))       # tag | tag_2line | luggage_tag
shape       = str(PARAM(lambda: shape,        "rounded_rect"))  # rounded_rect|circle|dogtag|bone
text_mode   = str(PARAM(lambda: text_mode,    "deboss"))    # emboss | deboss

size        = float(PARAM(lambda: size,       45.0))   # nominal tag length (mm)
thick       = float(PARAM(lambda: thick,       3.0))   # tag thickness (mm)
hole_dia    = float(PARAM(lambda: hole_dia,    5.0))   # ring hole diameter (mm)
hole_pos    = float(PARAM(lambda: hole_pos,    6.0))   # hole inset from the leading edge (mm)
text        = str(  PARAM(lambda: text,       "KEY-01"))  # primary line
text2       = str(  PARAM(lambda: text2,      ""))        # second line (tag_2line)
text_depth  = float(PARAM(lambda: text_depth,  0.8))   # emboss height / deboss depth (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
size       = max(20.0, min(size, 100.0))
thick      = max(2.0, min(thick, 8.0))
hole_dia   = max(2.0, min(hole_dia, 14.0))
hole_pos   = max(3.0, min(hole_pos, size * 0.4))
text_depth = max(0.3, min(text_depth, 1.5))

if text_mode not in ("emboss", "deboss"):
    text_mode = "deboss"


# ── Tag body (3D primitives — robust + watertight) ───────────────────────────
def tag_solid(length, is_luggage):
    """The flat tag SOLID for the chosen `shape` on XY (base at z=0), centred, long
    axis along X. Returns (solid, width, height). Rounded corners are filleted on the
    3D vertical edges (extruding a 2D rounded wire is fragile — box+fillet is not)."""
    if shape == "circle":
        d = length
        solid = cq.Workplane("XY").circle(d / 2.0).extrude(thick)
        return solid, d, d
    if shape == "dogtag":
        w = length
        h = length * 0.55
        r = min(h * 0.48, w * 0.2)
        return _rounded_rect_solid(w, h, r), w, h
    if shape == "bone":
        w = length
        h = length * 0.42
        return _bone_solid(w, h), w, h
    # rounded_rect (default)
    w = length
    h = length * (0.62 if is_luggage else 0.5)
    r = min(h * 0.35, 10.0)
    return _rounded_rect_solid(w, h, r), w, h


def _rounded_rect_solid(w, h, r):
    r = max(0.0, min(r, min(w, h) / 2.0 - 0.01))
    solid = cq.Workplane("XY").box(w, h, thick, centered=(True, True, False))
    if r > 0.05:
        try:
            solid = solid.edges("|Z").fillet(r)
        except Exception:
            pass  # degenerate radius — leave square corners (non-fatal)
    return solid


def _bone_solid(w, h):
    """A dog-bone solid: a central bar plus four rounded lobes (a union of extruded
    boxes and cylinders — all watertight primitives)."""
    lobe_r = h / 2.0
    bar_w = max(1.0, w - 2.0 * lobe_r)
    offs = h * 0.28
    body = cq.Workplane("XY").box(bar_w, h, thick, centered=(True, True, False))
    body = body.union(cq.Workplane("XY").box(w, h - 2.0 * offs, thick, centered=(True, True, False)))
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            lobe = (
                cq.Workplane("XY")
                .center(sx * bar_w / 2.0, sy * offs)
                .circle(lobe_r)
                .extrude(thick)
            )
            body = body.union(lobe)
    return body


# ── Text (robust: validate + fall back) ──────────────────────────────────────
def _fit_fontsize(s, w, n_chars, avail_h):
    per_char = (w * 0.82) / max(1, n_chars)
    return max(3.0, min(avail_h, per_char * 1.5, 14.0))


# ── Hole / slot ──────────────────────────────────────────────────────────────
def add_ring_hole(plate, w):
    """A round ring hole inset from the leading (-X) edge."""
    r = hole_dia / 2.0
    x = -w / 2.0 + hole_pos
    cutter = (
        cq.Workplane("XY")
        .center(x, 0.0)
        .circle(r)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return plate.cut(cutter)


def add_strap_slot(plate, w, h):
    """A wide strap slot for a luggage tag (a rounded slot near the -X end)."""
    slot_l = min(h * 0.5, 16.0)
    slot_w = max(3.0, min(hole_dia, 8.0))
    x = -w / 2.0 + max(hole_pos, slot_w)
    cutter = (
        cq.Workplane("XY")
        .center(x, 0.0)
        .slot2D(slot_l, slot_w, 90)
        .extrude(thick + 2.0)
        .translate((0, 0, -1.0))
    )
    return plate.cut(cutter)


# ── Part builders ────────────────────────────────────────────────────────────
def build_tag(two_line=False, luggage=False):
    plate, w, h = tag_solid(size * (1.15 if luggage else 1.0), luggage)
    if luggage:
        plate = add_strap_slot(plate, w, h)
    else:
        plate = add_ring_hole(plate, w)

    # Text region avoids the hole/slot end (shift text toward +X).
    text_cx_shift = hole_pos * 0.5
    if two_line:
        plate = _apply_two_lines(plate, w, h, text_cx_shift)
    else:
        plate = apply_line_at(plate, text, 0.0, w, h * 0.55, text_cx_shift)
    return plate


def apply_line_at(plate, txt, y, w, avail_h, x_shift):
    """apply_line but translated in X to clear the hole end."""
    if not txt.strip():
        return plate
    fontsize = _fit_fontsize(size, w - x_shift, len(txt.strip()), avail_h)
    other = "emboss" if text_mode == "deboss" else "deboss"
    for mode in (text_mode, other):
        out = _try_text_shifted(plate, txt, y, fontsize, mode, x_shift)
        if out is not None:
            return out
    return plate


def _try_text_shifted(plate, txt, y, fontsize, mode, x_shift):
    if not txt.strip():
        return plate
    try:
        glyphs = (
            cq.Workplane("XY")
            .workplane(offset=thick)
            .center(x_shift, y)
            .text(txt, fontsize, text_depth if mode == "emboss" else -text_depth, combine=False)
        )
        out = plate.union(glyphs) if mode == "emboss" else plate.cut(glyphs)
        if out.val().isValid():
            return out
        return None
    except Exception:
        return None


def _apply_two_lines(plate, w, h, x_shift):
    """Two stacked text lines; the second falls back to a repeat of line 1 if empty."""
    line2 = text2 if text2.strip() else "----"
    gap = h * 0.24
    plate = apply_line_at(plate, text, gap, w, h * 0.34, x_shift)
    plate = apply_line_at(plate, line2, -gap, w, h * 0.34, x_shift)
    return plate


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tag_2line":
    result = build_tag(two_line=True, luggage=False)
elif target_part == "luggage_tag":
    result = build_tag(two_line=True, luggage=True)
else:
    result = build_tag(two_line=False, luggage=False)
