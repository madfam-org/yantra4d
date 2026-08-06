"""
Wire / Cable Labels & Markers — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Clip-on cable labels that snap onto a wire and carry a short text marker
(embossed or debossed on a plate). Three styles (dispatched by `target_part`):

  * "flag_label"  — a C-clip that snaps on, with a flat flag sticking out to one
                    side carrying the text (reads like a little flag on the wire).
  * "wrap_label"  — a fuller band / cuff that wraps most of the cable, with a
                    raised text panel on the outside.
  * "clip_marker" — a compact C that snaps on with a small marker face and text.

Text is optional and rendered with CadQuery's text(); each glyph op is guarded
so a font/glyph failure degrades to a blank (still watertight) plate rather than
crashing. Text defaults to DEBOSSED (a shallow cut), which is the most reliably
watertight; embossed (raised) is available via `text_mode`.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cable_dia`).
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
style        = str(  PARAM(lambda: style, "flag"))       # flag | wrap | clip
target_part  = str(  PARAM(lambda: target_part, ""))     # overrides style if a part id

cable_dia    = float(PARAM(lambda: cable_dia,   6.0))    # cable diameter = clip bore (mm)
clip_wall    = float(PARAM(lambda: clip_wall,   2.0))    # clip ring wall thickness (mm)
clip_len     = float(PARAM(lambda: clip_len,   12.0))    # clip length along the cable (mm)
gap_frac     = float(PARAM(lambda: gap_frac,   0.55))    # clip mouth opening (fraction of dia)

plate_w      = float(PARAM(lambda: plate_w,    22.0))    # label plate width (mm)
plate_h      = float(PARAM(lambda: plate_h,    12.0))    # label plate height (mm)
plate_t      = float(PARAM(lambda: plate_t,     2.0))    # label plate thickness (mm)

text         = str(  PARAM(lambda: text,       "A1"))    # marker text (short)
text_mode    = str(  PARAM(lambda: text_mode, "deboss")) # deboss | emboss | none
text_depth   = float(PARAM(lambda: text_depth,  0.6))    # emboss/deboss depth (mm)

# ── Resolve active part ──────────────────────────────────────────────────────
_PARTS = ("flag_label", "wrap_label", "clip_marker")
if target_part in _PARTS:
    active = target_part
else:
    active = {
        "flag": "flag_label",
        "wrap": "wrap_label",
        "clip": "clip_marker",
    }.get(style, "flag_label")

# ── Clamps / derived values ──────────────────────────────────────────────────
cable_dia = max(2.0, min(cable_dia, 40.0))
clip_wall = max(1.2, min(clip_wall, 6.0))
clip_len  = max(5.0, min(clip_len, 60.0))
gap_frac  = max(0.2, min(gap_frac, 0.85))
plate_w   = max(8.0, min(plate_w, 120.0))
plate_h   = max(6.0, min(plate_h, 80.0))
plate_t   = max(1.2, min(plate_t, 6.0))
text_depth = max(0.2, min(text_depth, min(plate_t - 0.6, 2.0)))
if text_mode not in ("deboss", "emboss", "none"):
    text_mode = "deboss"

bore_r = cable_dia / 2.0
ring_r = bore_r + clip_wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def c_clip(length, mouth_frac):
    """A C-shaped snap clip: a solid tube (bore = cable) of `length` along the Y
    axis, with a mouth slot cut on the +X side so it snaps over a cable. The
    clip axis lies along Y; the mouth faces +X. Watertight (a solid with a
    through bore and a radial slot)."""
    tube = (
        cq.Workplane("XZ")
        .circle(ring_r)
        .circle(bore_r)
        .extrude(length)
        .translate((0, length / 2.0, 0))
    )
    # Mouth: a radial slot from the bore out through the +X wall.
    mouth_w = cable_dia * mouth_frac
    mouth = (
        cq.Workplane("XZ")
        .rect(ring_r + 2.0, mouth_w, centered=(False, True))
        .extrude(length + 2.0)
        .translate((0, length / 2.0 + 1.0, 0))
    )
    # rect built from x=0 outward; shift so it starts inside the bore.
    mouth = mouth.translate((0, -1.0, 0))
    return tube.cut(mouth)


def label_plate(w, h, t):
    """A rounded-corner label plate lying in the XY plane, centred, base z=0."""
    plate = cq.Workplane("XY").box(w, h, t, centered=(True, True, False))
    try:
        plate = plate.edges("|Z").fillet(min(h, w) * 0.12)
    except Exception:
        pass
    return plate


def apply_text(plate, w, h, t):
    """Emboss or deboss `text` on the top (+Z) face of a plate that lies in XY,
    top at z=t. Guarded per the brief: any glyph/font failure returns the plate
    unchanged (blank but watertight)."""
    if text_mode == "none" or not text.strip():
        return plate
    fontsize = _fit_fontsize(w, h)
    try:
        if text_mode == "emboss":
            raised = (
                cq.Workplane("XY")
                .workplane(offset=t)
                .text(text, fontsize, text_depth, combine=False)
            )
            return plate.union(raised)
        # deboss: cut a shallow recess of the glyphs into the top face.
        carved = (
            cq.Workplane("XY")
            .workplane(offset=t)
            .text(text, fontsize, -text_depth, combine=False)
        )
        return plate.cut(carved)
    except Exception:
        # Font/glyph problem — ship a blank, watertight plate.
        return plate


def _fit_fontsize(w, h):
    """Pick a font size that keeps the text inside the plate."""
    per_char = (w * 0.85) / max(1, len(text.strip()))
    return max(3.0, min(h * 0.6, per_char * 1.4, 14.0))


def _clip_axis_to_plate():
    """Common orientation: the clip axis runs along Y; the plate attaches on the
    -X side of the ring so it projects away from the cable. Returns the plate X
    offset where its inner edge meets the ring."""
    return -(ring_r)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_flag_label():
    """C-clip with a flat flag projecting to -X carrying the text."""
    clip = c_clip(clip_len, gap_frac)

    # Flag plate: lies flat (in XY), centred on the clip length in Y, projecting
    # in -X from the ring. Its top face (z = +plate_t/2 region) carries text.
    plate = label_plate(plate_w, plate_h, plate_t)
    plate = apply_text(plate, plate_w, plate_h, plate_t)
    # Move plate so it sits centred vertically on the ring and reaches out -X.
    px = _clip_axis_to_plate() - plate_w / 2.0 + 0.5
    plate = plate.translate((px, clip_len / 2.0, -plate_t / 2.0))

    # A short neck bridges ring → plate so the union is solid (overlap both).
    neck = (
        cq.Workplane("XY")
        .box(clip_wall + 2.0, min(plate_h, clip_len), plate_t,
             centered=(True, True, False))
        .translate((_clip_axis_to_plate() + 0.5, clip_len / 2.0, -plate_t / 2.0))
    )
    body = clip.union(neck).union(plate)
    return body


def build_wrap_label():
    """A longer band/cuff wrapping the cable (a full tube with a narrow mouth),
    with a raised text panel standing off the outside (-X)."""
    length = max(clip_len, plate_h + 4.0)
    # Narrow mouth so it grips more of the circumference (a wrap, not a light clip).
    clip = c_clip(length, min(gap_frac, 0.35))

    # Text panel: a plate tangent to the outside of the band on -X.
    panel_t = plate_t
    plate = label_plate(plate_w, min(plate_h, length - 2.0), panel_t)
    plate = apply_text(plate, plate_w, min(plate_h, length - 2.0), panel_t)
    px = -(ring_r) - panel_t / 2.0 + 0.4
    # Stand the plate vertical (in the YZ-ish orientation) on the band's flank:
    # rotate the flat plate to face -X.
    plate = plate.rotate((0, 0, 0), (0, 1, 0), 90)
    plate = plate.translate((px, length / 2.0, 0))

    # Boss to fuse panel to band.
    boss = (
        cq.Workplane("XZ")
        .rect(clip_wall + 2.0, min(plate_h, length - 2.0) * 0.7, centered=True)
        .extrude(-(ring_r + 1.0))
        .translate((0, length / 2.0, 0))
    )
    body = clip.union(boss).union(plate)
    return body


def build_clip_marker():
    """A compact C-clip with a small marker face on -X carrying the text."""
    length = clip_len
    clip = c_clip(length, gap_frac)

    face_w = min(plate_w, cable_dia * 2.2)
    face_h = min(plate_h, length - 1.0)
    plate = label_plate(face_w, face_h, plate_t)
    plate = apply_text(plate, face_w, face_h, plate_t)
    px = _clip_axis_to_plate() - plate_t / 2.0 + 0.4
    plate = plate.rotate((0, 0, 0), (0, 1, 0), 90)
    plate = plate.translate((px, length / 2.0, 0))

    boss = (
        cq.Workplane("XZ")
        .rect(clip_wall + 2.0, face_h * 0.7, centered=True)
        .extrude(-(ring_r + 1.0))
        .translate((0, length / 2.0, 0))
    )
    body = clip.union(boss).union(plate)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "wrap_label":
    result = build_wrap_label()
elif active == "clip_marker":
    result = build_clip_marker()
else:
    result = build_flag_label()
