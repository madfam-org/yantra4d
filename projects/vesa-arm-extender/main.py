"""
VESA Arm Extender — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Extends or offsets a VESA display mount for extra reach, wall clearance, or to
bridge two pattern sizes. Every part carries a real VESA MIS-D bolt square on
BOTH a mount-side face (bolts to the arm / wall bracket) and a display-side face
(the monitor bolts to it), so it drops transparently into a VESA screw chain.

Three modes (rendered per-part via `target_part`):

  * "spacer"       — a flat standoff / riser: the same VESA square on the mount
                     face and the display face, separated by `offset` of solid
                     material. Pushes the display straight out from the wall.
  * "offset_arm"   — an L/Z crank: the mount square sits low, a web carries the
                     pattern OUT (in +Y) and UP (in +Z) to a raised display
                     square, so the screen clears an obstruction or gains reach.
  * "combo_adapter"— like the spacer but the mount face and display face carry
                     DIFFERENT VESA squares (75 ↔ 100) while still offsetting,
                     so a 75 monitor mounts to a 100 arm (or vice-versa) with
                     clearance in one part.

VESA MIS-D per the FDMI standard: 75×75 and 100×100 hole squares, M4 screws
(≈4.5 mm printable clearance).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `offset`).
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


# ── VESA MIS-D table (FDMI) ──────────────────────────────────────────────────
# Square bolt patterns; screw_clear is a printable M4 clearance diameter.
VESA_TABLE = {
    "75":  {"span": 75.0,  "screw": "M4", "screw_clear": 4.5},
    "100": {"span": 100.0, "screw": "M4", "screw_clear": 4.5},
}


def vesa_spec(key):
    """Look up a VESA square, tolerant of ints/floats and stray spellings."""
    k = str(key).strip().lower().replace(" ", "").replace("*", "x")
    if k in ("75x75", "75.0"):
        k = "75"
    elif k in ("100x100", "100.0"):
        k = "100"
    return VESA_TABLE.get(k, VESA_TABLE["100"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "spacer"))  # spacer|offset_arm|combo_adapter

vesa = str(PARAM(lambda: vesa, "100"))            # mount-side VESA square
dest_vesa = str(PARAM(lambda: dest_vesa, "75"))   # display-side square (combo only)

offset = float(PARAM(lambda: offset, 40.0))       # reach / standoff distance (mm)
plate_thick = float(PARAM(lambda: plate_thick, 5.0))   # face-plate thickness (mm)
web_thick = float(PARAM(lambda: web_thick, 6.0))       # connecting web / column thickness (mm)
plate_margin = float(PARAM(lambda: plate_margin, 11.0))  # material beyond the bolt square (mm)
corner_r = float(PARAM(lambda: corner_r, 6.0))          # plate corner radius (mm)

cable_slot = bool(PARAM(lambda: cable_slot, True))      # cable-management pass slot
slot_w = float(PARAM(lambda: slot_w, 16.0))             # cable slot width (mm)


# ── Active part ──────────────────────────────────────────────────────────────
_parts = ("spacer", "offset_arm", "combo_adapter")
active = target_part if target_part in _parts else "spacer"

# ── Safe clamps ──────────────────────────────────────────────────────────────
plate_thick = max(2.5, plate_thick)
web_thick = max(3.0, web_thick)
plate_margin = max(4.0, plate_margin)
offset = max(12.0, offset)
slot_w = max(4.0, slot_w)

src = vesa_spec(vesa)
dst = vesa_spec(dest_vesa) if active == "combo_adapter" else src

# Plate footprint must clear the larger of the two squares it carries.
face_span = max(src["span"], dst["span"])
plate_w = face_span + 2.0 * plate_margin
plate_d = face_span + 2.0 * plate_margin
corner_r = max(0.0, min(corner_r, plate_w / 2.0 - 0.01))


# ── Shared plate + bolt-pattern helpers (reused across the batch) ─────────────
def rounded_plate(w, d, h, r):
    """Axis-aligned plate on XY, base at z=0, optional rounded vertical edges."""
    wp = cq.Workplane("XY").box(w, d, h, centered=(True, True, False))
    if r > 0.05:
        try:
            wp = wp.edges("|Z").fillet(r)
        except Exception:
            pass  # degenerate radius — leave square (non-fatal)
    return wp


def vesa_points(span):
    """Four corners of a VESA square centred on the origin (XY)."""
    h = span / 2.0
    return [(-h, -h), (h, -h), (h, h), (-h, h)]


def drill_z(body, points, dia, z_lo, z_hi):
    """Cut vertical (Z) through-holes at each (x, y) between z_lo and z_hi,
    with a small over-travel past both faces for a clean watertight cut."""
    r = dia / 2.0
    if r <= 0.05 or not points:
        return body
    span = (z_hi - z_lo) + 2.0
    cutter = (
        cq.Workplane("XY")
        .pushPoints(points)
        .circle(r)
        .extrude(span)
        .translate((0, 0, z_lo - 1.0))
    )
    return body.cut(cutter)


def cut_cable_slot_z(body, z_lo, z_hi):
    """A rounded vertical channel through the plate centre for routing cables."""
    if not cable_slot:
        return body
    span = (z_hi - z_lo) + 2.0
    length = min(face_span * 0.55, plate_w - 2.0 * plate_margin)
    length = max(length, slot_w)
    tool = (
        cq.Workplane("XY")
        .slot2D(length, slot_w, 0)
        .extrude(span)
        .translate((0, 0, z_lo - 1.0))
    )
    return body.cut(tool)


# ── Builders ─────────────────────────────────────────────────────────────────
def build_spacer():
    """Solid standoff: one VESA square drilled straight through a block of
    height `offset`, so mount face (z=0) and display face (z=offset) share the
    pattern. A central web is implicit (the whole block is solid)."""
    body = rounded_plate(plate_w, plate_d, offset, corner_r)
    pts = vesa_points(src["span"])
    body = drill_z(body, pts, src["screw_clear"], 0.0, offset)
    body = cut_cable_slot_z(body, 0.0, offset)
    return body


def build_combo_adapter():
    """Standoff whose two faces carry DIFFERENT squares: bolts of the mount
    square (bottom) and the display square (top) are drilled from their own
    face and stop short of the other so neither pattern is confused. A ≥3 mm
    solid core is always left between the two blind bores."""
    body = rounded_plate(plate_w, plate_d, offset, corner_r)

    core = max(3.0, offset * 0.25)
    bore_depth = max(plate_thick + 1.0, (offset - core) / 2.0)
    bore_depth = min(bore_depth, offset - core)

    # Mount square: blind bores rising from the bottom face.
    src_pts = vesa_points(src["span"])
    body = drill_z(body, src_pts, src["screw_clear"], -1.0, bore_depth)

    # Display square: blind bores dropping from the top face.
    dst_pts = vesa_points(dst["span"])
    body = drill_z(body, dst_pts, dst["screw_clear"], offset - bore_depth, offset + 1.0)

    body = cut_cable_slot_z(body, 0.0, offset)
    return body


def build_offset_arm():
    """L/Z crank. A mount plate lies flat (its VESA square drilled in Z). A
    vertical web rises at the back (+Y) and carries the pattern OUT and UP to a
    display plate that stands in the XZ plane facing forward (-Y). The display
    square is drilled through the standing plate in Y. Everything fuses into one
    watertight solid."""
    half = plate_w / 2.0

    # Mount plate: flat on XY, VESA drilled vertically.
    mount = rounded_plate(plate_w, plate_d, plate_thick, corner_r)
    mount = drill_z(mount, vesa_points(src["span"]), src["screw_clear"], 0.0, plate_thick)

    # Rise: a vertical web at the back edge, climbing to display height.
    rise_h = offset + plate_w  # total lift so the screen clears the mount plate
    web = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, half - web_thick / 2.0, rise_h / 2.0))
        .box(plate_w, web_thick, rise_h)
    )

    # Reach: a horizontal web carrying the pattern forward (-Y) at the top.
    reach_len = offset + plate_d
    reach = (
        cq.Workplane("XY")
        .transformed(
            offset=cq.Vector(0, half - reach_len / 2.0, rise_h - web_thick / 2.0)
        )
        .box(plate_w, reach_len, web_thick)
    )

    # Display plate: stands in the XZ plane at the FRONT (-Y), facing -Y.
    disp_y = half - reach_len + plate_thick / 2.0
    disp_cz = rise_h - web_thick - plate_w / 2.0
    disp = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, disp_y, disp_cz))
        .box(plate_w, plate_thick, plate_w)
    )
    # Drill the display VESA square through the standing plate (in Y).
    dpts = vesa_points(src["span"])
    for (px, pz) in dpts:
        hole = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(px, disp_cz + pz, -disp_y))
            .cylinder(plate_thick + 2.0, src["screw_clear"] / 2.0)
        )
        disp = disp.cut(hole)

    body = mount.union(web).union(reach).union(disp)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "offset_arm":
    result = build_offset_arm()
elif active == "combo_adapter":
    result = build_combo_adapter()
else:
    result = build_spacer()
