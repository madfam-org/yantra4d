"""
License Plate Frame — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A parametric license-plate frame plus trim fillers, for the two dominant plate
formats: US (12 × 6 in) and EU (520 × 110 mm). Three modes:

  * "frame"           — a full plate frame: an outer border with a recessed
                        window that reveals the plate, carrying the standard
                        mounting-bolt slots.
  * "tag_frame_slim"  — a minimal thin-border frame (less border, same slots) —
                        the low-profile "slim" look.
  * "panel_filler"    — a blank filler panel that plugs an oversized factory
                        plate recess so a smaller plate sits flush.

The mounting-bolt slot pattern (US 4-bolt / EU 2-bolt) is the Common Denominator
Geometry — every mode carries the same standard holes so the frame bolts to the
same studs as the OEM plate.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `plate`).
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


# ── Plate standard table ─────────────────────────────────────────────────────
# w/h = plate size (mm). bolts = list of (x, y) mounting-hole centres relative to
# the plate centre. US: four holes on a 7 in (177.8 mm) horizontal centre near
# the top edge; a standard second pair lower for 4-hole frames. EU: two holes on
# a common ~200 mm horizontal spacing.
PLATE_TABLE = {
    "US": {
        "w": 304.8, "h": 152.4, "slot": 8.0,
        "bolts": [(-88.9, 47.6), (88.9, 47.6), (-88.9, -47.6), (88.9, -47.6)],
    },
    "EU": {
        "w": 520.0, "h": 110.0, "slot": 7.0,
        "bolts": [(-100.0, 0.0), (100.0, 0.0)],
    },
}


def plate_spec(key):
    """Look up a plate format, tolerant of case / spacing / aliases."""
    k = str(key).strip().upper().replace(" ", "")
    if k in ("US", "USA", "NA", "12X6"):
        k = "US"
    elif k in ("EU", "EURO", "EUROPE", "520X110"):
        k = "EU"
    return PLATE_TABLE.get(k, PLATE_TABLE["US"])


# ── Parameters ───────────────────────────────────────────────────────────────
plate        = str(  PARAM(lambda: plate,        "US"))   # "US" | "EU"
border       = float(PARAM(lambda: border,       14.0))   # frame border width (frame mode)
slim_border  = float(PARAM(lambda: slim_border,   7.0))   # border width for the slim frame
frame_thick  = float(PARAM(lambda: frame_thick,   5.0))   # frame plate thickness
lip          = float(PARAM(lambda: lip,           2.5))   # front lip overlapping the plate edge
corner_r     = float(PARAM(lambda: corner_r,      6.0))   # outer corner radius
slot_len     = float(PARAM(lambda: slot_len,     10.0))   # mounting slot vertical travel
filler_inset = float(PARAM(lambda: filler_inset,  0.0))   # shrink filler vs plate size (per side)

target_part  = str(  PARAM(lambda: target_part, "frame"))
# "frame" | "tag_frame_slim" | "panel_filler"


# ── Derived / clamped geometry ───────────────────────────────────────────────
spec = plate_spec(plate)
pw, ph = spec["w"], spec["h"]
slot_d = spec["slot"]
bolts = spec["bolts"]
frame_thick = max(2.0, frame_thick)
lip = max(0.0, min(lip, frame_thick - 1.0))


# ── Shared helpers ────────────────────────────────────────────────────────────
def rounded_plate(w, d, h, r):
    """Axis-aligned plate on XY, base at z=0, optional rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(min(r, w / 2.0 - 0.5, d / 2.0 - 0.5))
        except Exception:
            pass
    return wp


def bolt_slots(body, thick):
    """Cut a vertical slot (elongated hole) at each standard bolt centre so the
    frame can slide on the studs. Overshoots both faces → watertight."""
    r = slot_d / 2.0
    travel = max(0.0, slot_len)
    for (bx, by) in bolts:
        # Slot = two end-circles + a connecting rectangle, extruded through.
        cutter = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(bx, by, -1.0))
            .slot2D(travel + 2.0 * r, 2.0 * r, 90.0)
            .extrude(thick + 2.0)
        )
        body = body.cut(cutter)
    return body


def build_border_frame(border_w):
    """A border frame of the given border width: outer rounded plate with a
    recessed window revealing the plate, plus a small front lip that overlaps the
    plate edge to retain it."""
    ow = pw + 2.0 * border_w
    oh = ph + 2.0 * border_w
    body = rounded_plate(ow, oh, frame_thick, corner_r)

    # Window: cut fully through, leaving the border. A front lip (top face) keeps
    # a thin ledge overlapping the plate; so cut the through-window smaller and a
    # deeper back-relief larger.
    win_w = pw - 2.0 * lip
    win_h = ph - 2.0 * lip
    through = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .box(win_w, win_h, frame_thick + 2.0, centered=(True, True, False))
    )
    body = body.cut(through)

    # Back relief: from the BACK face up to (frame_thick - lip), open to full
    # plate size, so the plate sits into the frame and the lip overlaps its face.
    if lip > 0.05:
        relief_h = frame_thick - lip
        relief = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -1.0))
            .box(pw, ph, relief_h + 1.0, centered=(True, True, False))
        )
        body = body.cut(relief)

    body = bolt_slots(body, frame_thick)
    return body


def build_panel_filler():
    """A blank filler panel that plugs an oversized plate recess: a solid plate
    at the OEM plate size (optionally inset), carrying the same bolt slots."""
    fw = pw - 2.0 * filler_inset
    fh = ph - 2.0 * filler_inset
    body = rounded_plate(fw, fh, frame_thick, corner_r)
    body = bolt_slots(body, frame_thick)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tag_frame_slim":
    result = build_border_frame(max(2.0, slim_border))
elif target_part == "panel_filler":
    result = build_panel_filler()
else:  # "frame"
    result = build_border_frame(max(3.0, border))
