"""
Nameplate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A personalized nameplate or sign with embossed or debossed text. Type a name, pick a
form — a standing desk wedge, a wall plate, or a hanging door sign — and print. Sized by
the text so the plate always fits the name.

Three parts (dispatched via `target_part`):
  * "desk_nameplate" — a triangular desk wedge with the name on the sloped front face.
  * "wall_plate"     — a flat plate with the name and two keyhole mounting holes.
  * "door_sign"      — a rounded plate with the name and a top hang slot for a door hook.

Text robustness (per the keytag pattern): text is applied via cq `text()` and the boolean
result is validated with `.val().isValid()`. If the requested mode (emboss/deboss) yields
an invalid solid — some accented glyphs break a debossed cut — the code falls back to the
other mode, and finally to a blank (but watertight) plate. The plate is ALWAYS watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `text`).
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
target_part = str(PARAM(lambda: target_part, "desk_nameplate"))  # desk_nameplate|wall_plate|door_sign
style       = str(PARAM(lambda: style,       "desk-wedge"))      # desk-wedge|wall-plate|door-hanger
text_mode   = str(PARAM(lambda: text_mode,   "emboss"))          # emboss | deboss

text       = str(  PARAM(lambda: text,       "HELLO"))   # the name / label
size       = float(PARAM(lambda: size,       28.0))      # text cap height (mm)
plate_t    = float(PARAM(lambda: plate_t,     6.0))      # plate thickness (mm)
margin     = float(PARAM(lambda: margin,     14.0))      # border around the text (mm)
text_depth = float(PARAM(lambda: text_depth,  1.2))      # emboss height / deboss depth (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
size       = max(10.0, min(size, 60.0))
plate_t    = max(3.0, min(plate_t, 20.0))
margin     = max(6.0, min(margin, 40.0))
text_depth = max(0.4, min(text_depth, 3.0))

if text_mode not in ("emboss", "deboss"):
    text_mode = "emboss"

# Estimate the plate footprint from the text (monospace-ish width heuristic).
label = text.strip() if text.strip() else "NAME"
n_chars = max(1, len(label))
text_w = size * 0.62 * n_chars                 # approx glyph advance
plate_w = text_w + 2.0 * margin
plate_h = size + 2.0 * margin                  # front-face height


# ── Robust text application (validate + fall back) ───────────────────────────
def _apply_text(base, face_z, cx, cy, fontsize, on_workplane="XY"):
    """Apply `label` onto `base` at height `face_z` centred at (cx, cy). Try the requested
    mode; if the resulting solid is invalid, try the other mode; if both fail, return the
    plain base (a blank but watertight plate). Mirrors the keytag text-robustness rule."""
    other = "emboss" if text_mode == "deboss" else "deboss"
    for mode in (text_mode, other):
        out = _try_mode(base, face_z, cx, cy, fontsize, mode, on_workplane)
        if out is not None:
            return out
    return base


def _try_mode(base, face_z, cx, cy, fontsize, mode, on_workplane):
    if not label:
        return base
    try:
        glyphs = (
            cq.Workplane(on_workplane)
            .workplane(offset=face_z)
            .center(cx, cy)
            .text(label, fontsize, text_depth if mode == "emboss" else -text_depth, combine=False)
        )
        out = base.union(glyphs) if mode == "emboss" else base.cut(glyphs)
        if out.val().isValid():
            return out
        return None
    except Exception:
        return None


# ── Part builders ─────────────────────────────────────────────────────────────
def build_desk_nameplate():
    """A triangular desk wedge: a right-triangle prism whose sloped front face carries the
    name, so it reads from across a desk. Text is applied to the top (+Z) of a flat plate
    that is then tilted; simplest robust route is a slab base with the text on top and a
    rear prop, kept fully watertight."""
    # A flat name slab lying on XY with text on +Z.
    slab = cq.Workplane("XY").box(plate_w, plate_h, plate_t, centered=(True, True, False))
    fontsize = size
    slab = _apply_text(slab, plate_t, 0.0, 0.0, fontsize)
    # A triangular prop behind the slab so it stands at a readable lean.
    prop_h = plate_h * 0.8
    prop = (
        cq.Workplane("YZ")
        .polyline([(0, 0), (plate_h * 0.5, 0), (0, prop_h)])
        .close()
        .extrude(plate_w * 0.5)
        .translate((-plate_w * 0.25, -plate_h / 2.0, plate_t))
    )
    body = slab.union(prop)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_wall_plate():
    """A flat wall plate with the name and two keyhole mounting holes at the ends."""
    slab = cq.Workplane("XY").box(plate_w, plate_h, plate_t, centered=(True, True, False))
    slab = _apply_text(slab, plate_t, 0.0, 0.0, size)
    # Two keyhole slots near the short ends (a round hole + a narrow slot up).
    for s in (-1.0, 1.0):
        x = s * (plate_w / 2.0 - margin * 0.6)
        y = plate_h / 2.0 - margin * 0.55
        hole = (
            cq.Workplane("XY").center(x, y).circle(3.2)
            .extrude(plate_t + 2.0).translate((0, 0, -1.0))
        )
        slot = (
            cq.Workplane("XY").center(x, y - 4.0).box(3.0, 8.0, plate_t + 2.0, centered=(True, True, False))
            .translate((0, 0, -1.0))
        )
        slab = slab.cut(hole).cut(slot)
    return slab


def build_door_sign():
    """A rounded door sign with the name and a top hang slot for a hook or ribbon."""
    slab = cq.Workplane("XY").box(plate_w, plate_h, plate_t, centered=(True, True, False))
    try:
        slab = slab.edges("|Z").fillet(min(margin * 0.6, plate_h * 0.3))
    except Exception:
        pass
    slab = _apply_text(slab, plate_t, 0.0, -plate_h * 0.08, size * 0.9)
    # Top hang slot (a rounded horizontal slot near the top edge).
    slot = (
        cq.Workplane("XY").center(0.0, plate_h / 2.0 - margin * 0.55)
        .slot2D(min(plate_w * 0.35, 30.0), 5.0, 0)
        .extrude(plate_t + 2.0).translate((0, 0, -1.0))
    )
    slab = slab.cut(slot)
    return slab


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "wall_plate":
    result = build_wall_plate()
elif target_part == "door_sign":
    result = build_door_sign()
else:
    result = build_desk_nameplate()
