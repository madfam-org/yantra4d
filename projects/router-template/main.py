"""
Sanding / Router Template — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A flat template that a router follows with a guide bushing (or a bearing-guided
bit) to reproduce a shape exactly. The template is a plate with the shape cut
clean through; the opening is intentionally OFFSET from the finished size by the
bushing-to-bit offset so the routed part comes out on-size.

Guide-bushing offset: with a guide bushing the cutter is inset from the template
edge by (bushing_OD − bit_dia) / 2. `bushing_offset` is that radial offset. For
an INSIDE cutout the template opening is made LARGER than final by the offset;
this cartridge cuts the opening at final + offset so the routed pocket lands on
nominal. Set `bushing_offset = 0` for a flush-trim bearing bit (bearing rides the
template edge).

Three shapes, dispatched by `target_part`:
  - circle_template : a round opening of `radius`.
  - rect_template   : a W×D rectangular opening with corner radius `corner_r`.
  - slot_template   : a rounded slot of length `slot_len`, width `slot_w`.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `radius`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr. Assign the final solid to a top-level name `result`.
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
radius         = float(PARAM(lambda: radius,          40.0))  # circle opening radius (final)
rect_w         = float(PARAM(lambda: rect_w,          80.0))  # rectangle opening width (final)
rect_d         = float(PARAM(lambda: rect_d,          50.0))  # rectangle opening depth (final)
corner_r       = float(PARAM(lambda: corner_r,         8.0))  # rectangle corner radius (final)
slot_len       = float(PARAM(lambda: slot_len,        70.0))  # slot centre-line length (final)
slot_w         = float(PARAM(lambda: slot_w,          18.0))  # slot width (final)
bushing_offset = float(PARAM(lambda: bushing_offset,   3.0))  # (bushing_OD - bit)/2 radial offset
plate_t        = float(PARAM(lambda: plate_t,          6.0))  # template thickness
border         = float(PARAM(lambda: border,          25.0))  # plate margin around the opening
mount_holes    = bool( PARAM(lambda: mount_holes,     True))  # screw/pin fixing holes
mount_dia      = float(PARAM(lambda: mount_dia,        4.5))  # fixing hole diameter

target_part = str(PARAM(lambda: target_part, "circle_template"))

off = max(0.0, bushing_offset)   # opening grows by this so routed part is on-size


# ── Helpers ──────────────────────────────────────────────────────────────────
def plate(w, d):
    """Flat template plate, centred in X/Y, base at z=0, corners rounded."""
    p = cq.Workplane("XY").box(w, d, plate_t, centered=(True, True, False))
    r = min(border * 0.5, min(w, d) / 2.0 - 0.5, 8.0)
    if r > 0.3:
        try:
            p = p.edges("|Z").fillet(r)
        except Exception:
            pass
    return p


def add_mount_holes(p, w, d):
    """Countersink-free through-holes near the four corners to fix the template."""
    if not mount_holes:
        return p
    mx = w / 2.0 - border / 2.0
    my = d / 2.0 - border / 2.0
    for sx in (1, -1):
        for sy in (1, -1):
            hole = (
                cq.Workplane("XY")
                .circle(mount_dia / 2.0)
                .extrude(plate_t + 2.0)
                .translate((sx * mx, sy * my, -1.0))
            )
            p = p.cut(hole)
    return p


def cut_through(p, sketch_wp):
    """Extrude a 2D sketch through the plate and subtract it (clean through-cut)."""
    cutter = sketch_wp.extrude(plate_t + 2.0).translate((0, 0, -1.0))
    return p.cut(cutter)


# ── Circle template ──────────────────────────────────────────────────────────
def build_circle_template():
    r_open = radius + off
    w = d = 2.0 * r_open + 2.0 * border
    p = plate(w, d)
    p = cut_through(p, cq.Workplane("XY").circle(r_open))
    return add_mount_holes(p, w, d)


# ── Rectangle template ───────────────────────────────────────────────────────
def build_rect_template():
    ow = rect_w + 2.0 * off
    od = rect_d + 2.0 * off
    cr = min(corner_r + off, min(ow, od) / 2.0 - 0.01)
    w = ow + 2.0 * border
    d = od + 2.0 * border
    p = plate(w, d)

    sketch = cq.Workplane("XY").rect(ow, od)
    if cr > 0.3:
        # Build a rounded-rect opening by cutting a filleted prism instead.
        opening = (
            cq.Workplane("XY")
            .box(ow, od, plate_t + 2.0, centered=(True, True, True))
            .edges("|Z").fillet(cr)
            .translate((0, 0, plate_t / 2.0))
        )
        p = p.cut(opening)
    else:
        p = cut_through(p, sketch)
    return add_mount_holes(p, w, d)


# ── Slot template ────────────────────────────────────────────────────────────
def build_slot_template():
    ow = slot_len + 2.0 * off      # overall slot length (end to end)
    sw = slot_w + 2.0 * off        # slot width
    w = ow + 2.0 * border
    d = sw + 2.0 * border
    p = plate(w, d)
    # Rounded slot = central rectangle + two end caps, cut through.
    r = sw / 2.0
    straight = max(0.0, ow - sw)   # centre-to-centre run of the caps
    sketch = cq.Workplane("XY").slot2D(straight + sw, sw, 0) if straight > 0.05 \
        else cq.Workplane("XY").circle(r)
    return add_mount_holes(cut_through(p, sketch), w, d)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "rect_template":
    result = build_rect_template()
elif target_part == "slot_template":
    result = build_slot_template()
else:
    result = build_circle_template()
