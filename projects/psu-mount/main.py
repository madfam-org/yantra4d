"""
Power Supply / PSU Mount — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Mounts an enclosed switching PSU of the Meanwell LRS / RS family to a panel or a
2020 aluminium extrusion. A `psu_size` select carries the real case footprints
and approximate bottom mounting-hole pitch for LRS-50 / LRS-100 / LRS-350, with a
"custom" option exposing the case W/D and the hole pitch directly. Three mounting
strategies, each its own studio mode:

  * "foot_bracket"    — a pair of L-feet that bolt to the PSU's own bottom
                        mounting holes and lie the PSU flush against a panel, with
                        panel screw slots in each foot.
  * "extrusion_mount" — the same foot idea but the panel flange carries a 2020
                        T-slot bolt pattern (M5 at 20 mm pitch) to drop onto an
                        aluminium extrusion.
  * "strap"           — an open band clamp that wraps the PSU body and screws down
                        to the panel — no access to the PSU's own holes needed.

Shared across the batch: a bolt-pattern helper (`bolt_grid`) places both the PSU
case holes and the panel/extrusion holes identically.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `psu_size`).
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


# ── Meanwell LRS / RS footprint table ────────────────────────────────────────
# case_w/case_d/case_h — nominal enclosure size (mm).
# hole_px/hole_py     — approximate bottom mounting-hole pitch (on-centre), the
#                       screw squares Meanwell provides on the case underside.
# screw               — case mounting screw (M3 on LRS-50/100, M4 on LRS-350).
PSU_TABLE = {
    "LRS-50":  {"case_w": 99.0,  "case_d": 82.0,  "case_h": 30.0, "hole_px": 95.0,  "hole_py": 50.0, "screw_dia": 3.4},
    "LRS-100": {"case_w": 129.0, "case_d": 97.0,  "case_h": 30.0, "hole_px": 124.0, "hole_py": 50.0, "screw_dia": 3.4},
    "LRS-350": {"case_w": 215.0, "case_d": 115.0, "case_h": 30.0, "hole_px": 205.0, "hole_py": 60.0, "screw_dia": 4.5},
}


# ── Parameters ───────────────────────────────────────────────────────────────
# Every injected global is read once here at module scope (the reference-cartridge
# pattern) so ruff sees the self-referential binding and does not flag F821.
psu_size    = str(PARAM(lambda: psu_size, "LRS-100"))  # LRS-50|LRS-100|LRS-350|custom
target_part = str(PARAM(lambda: target_part, ""))      # studio dispatch (part id)

custom_w    = float(PARAM(lambda: custom_w,  129.0))  # custom case width  (mm)
custom_d    = float(PARAM(lambda: custom_d,   97.0))  # custom case depth  (mm)
custom_px   = float(PARAM(lambda: custom_px, 124.0))  # custom hole pitch X (mm)
custom_py   = float(PARAM(lambda: custom_py,  50.0))  # custom hole pitch Y (mm)
case_screw_dia = float(PARAM(lambda: case_screw_dia, 3.4))  # custom case screw dia (mm)

thickness   = float(PARAM(lambda: thickness,   4.0))  # bracket material thickness (mm)
foot_h      = float(PARAM(lambda: foot_h,     22.0))  # height the foot rises up the PSU side (mm)
panel_screw = float(PARAM(lambda: panel_screw, 4.5))  # panel screw clearance dia (mm)
strap_gap   = float(PARAM(lambda: strap_gap,   0.8))  # strap-to-case clearance per side (mm)

_part_ids = ("foot_bracket", "extrusion_mount", "strap")
active_part = target_part if target_part in _part_ids else "foot_bracket"


def psu_spec():
    """Resolve the active PSU footprint. 'custom' uses the custom_* params so the
    user can dial in any enclosed PSU; a known key returns the table entry."""
    key = psu_size.strip()
    if key == "custom":
        return {
            "case_w": custom_w, "case_d": custom_d, "case_h": 30.0,
            "hole_px": custom_px, "hole_py": custom_py, "screw_dia": case_screw_dia,
        }
    return PSU_TABLE.get(key, PSU_TABLE["LRS-100"])


# ── Safe clamps ──────────────────────────────────────────────────────────────
spec = psu_spec()
case_w = max(40.0, spec["case_w"])
case_d = max(30.0, spec["case_d"])
case_h = max(20.0, spec["case_h"])
hole_px = max(20.0, min(spec["hole_px"], case_w - 4.0))
hole_py = max(10.0, min(spec["hole_py"], case_d - 4.0))
case_screw = max(2.5, min(spec["screw_dia"], 6.0))

thickness = max(2.0, min(thickness, 10.0))
foot_h = max(8.0, min(foot_h, case_h + 10.0))
panel_screw = max(2.5, min(panel_screw, 8.0))
strap_gap = max(0.0, min(strap_gap, 2.0))

EXT_PITCH = 20.0          # 2020 extrusion T-slot pitch (mm)
EXT_SCREW = 5.2           # M5 clearance for extrusion T-nuts


# ── Shared plate + bolt-pattern helpers (reused across the batch) ─────────────
def slab(length_x, length_y, thick_z):
    """A flat slab: X:[0,length_x], centered in Y, Z:[0,thick_z]."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(length_x / 2.0, 0, thick_z / 2.0))
        .box(length_x, length_y, thick_z)
    )


def bolt_grid(solid, points, top_z, dia, thru):
    """Cut a vertical screw hole (Z axis) of diameter `dia` at each (x, y); the
    top of each bore sits at z=top_z and it passes fully through the slab."""
    r = dia / 2.0
    if r <= 0.05:
        return solid
    for (x, y) in points:
        hole = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, y, top_z - thru / 2.0))
            .cylinder(thru + 1.0, r)
        )
        solid = solid.cut(hole)
    return solid


def slot_x(solid, cx, cy, top_z, length, dia, thru):
    """Cut a horizontal slotted hole centred at (cx,cy) running along X — a
    rounded slot (two bores + a connecting box) for panel-screw adjustability."""
    r = dia / 2.0
    half = max(0.0, (length - dia) / 2.0)
    for x in (cx - half, cx + half):
        solid = solid.cut(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(x, cy, top_z - thru / 2.0))
            .cylinder(thru + 1.0, r)
        )
    if half > 0.05:
        solid = solid.cut(
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, top_z - thru / 2.0))
            .box(2.0 * half, dia, thru + 1.0)
        )
    return solid


# ── Foot geometry (shared by foot_bracket and extrusion_mount) ────────────────
def _one_foot(panel_pattern):
    """Build a single L-foot standing at the origin: a vertical web that bolts to
    ONE PSU case-hole column (two holes along Y at hole_py pitch) and a horizontal
    flange lying on the panel. `panel_pattern` selects how the flange is drilled:
      - "slot"      → one adjustable panel screw slot (foot_bracket)
      - "extrusion" → a 2020 T-slot pair at 20 mm pitch (extrusion_mount)
    Foot spans Y across the case depth; web stands up +Z; flange projects -Y."""
    web_w = hole_py + 2.0 * (case_screw + 3.0)     # Y span of the foot
    flange_d = max(16.0, panel_screw * 3.0)         # how far the flange projects
    # Vertical web: thickness in X, spans web_w in Y, foot_h in Z.
    web = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(thickness / 2.0, 0, foot_h / 2.0))
        .box(thickness, web_w, foot_h)
    )
    # PSU case holes through the web (bores run along X).
    for sy in (-hole_py / 2.0, hole_py / 2.0):
        web = web.cut(
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(sy, foot_h * 0.5, 0))
            .cylinder(thickness + 2.0, case_screw / 2.0)
        )
    # Horizontal flange on the panel (Z:[0,thickness]), projecting outward in +X
    # from the web foot and spanning the full foot width in Y.
    flange = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(thickness / 2.0 + flange_d / 2.0, 0, thickness / 2.0))
        .box(flange_d, web_w, thickness)
    )
    fx = thickness / 2.0 + flange_d / 2.0
    if panel_pattern == "extrusion":
        flange = bolt_grid(flange, [(fx, -EXT_PITCH / 2.0), (fx, EXT_PITCH / 2.0)],
                           thickness, EXT_SCREW, thickness + 2.0)
    else:
        flange = slot_x(flange, fx, 0.0, thickness, flange_d * 0.5, panel_screw, thickness + 2.0)
    return web.union(flange).clean()


def _feet(panel_pattern):
    """Two mirrored feet, one at each PSU case-hole column (±hole_px/2 in X)."""
    left = _one_foot(panel_pattern).translate((-hole_px / 2.0, 0, 0))
    right = _one_foot(panel_pattern).mirror("YZ").translate((hole_px / 2.0, 0, 0))
    return left.union(right)


def build_foot_bracket():
    """A pair of L-feet with adjustable panel screw slots."""
    return _feet("slot")


def build_extrusion_mount():
    """A pair of L-feet whose flanges carry a 2020 T-slot bolt pair (M5)."""
    return _feet("extrusion")


def build_strap():
    """Open band clamp: an inverted-U band that wraps the PSU body (width + gap)
    with two panel feet at the bottom. Modelled as a solid U — a full outer block
    minus the interior channel — plus a foot flange each side with a screw hole.
    Needs no access to the PSU's own mounting holes."""
    inner_w = case_w + 2.0 * strap_gap
    inner_h = case_h + strap_gap
    band = thickness
    band_d = min(case_d * 0.35, 30.0)          # how wide the band is along Y
    outer_w = inner_w + 2.0 * band
    outer_h = inner_h + band                    # closed across the top only

    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, outer_h / 2.0))
        .box(outer_w, band_d, outer_h)
    )
    # Channel: open at the bottom (a slot up to the underside of the top band).
    channel = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, inner_h / 2.0))
        .box(inner_w, band_d + 2.0, inner_h)
    )
    body = outer.cut(channel)

    # Two panel feet at the bottom of each leg, projecting outward in X.
    foot_len = max(16.0, panel_screw * 3.0)
    for sx in (-1.0, 1.0):
        foot_cx = sx * (outer_w / 2.0 + foot_len / 2.0)
        foot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(foot_cx, 0, thickness / 2.0))
            .box(foot_len, band_d, thickness)
        )
        foot = slot_x(foot, foot_cx, 0.0, thickness, foot_len * 0.5, panel_screw, thickness + 2.0)
        body = body.union(foot)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active_part == "extrusion_mount":
    result = build_extrusion_mount()
elif active_part == "strap":
    result = build_strap()
else:
    result = build_foot_bracket()
