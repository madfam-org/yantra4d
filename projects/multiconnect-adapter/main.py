"""
Multiconnect / GOEWS Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

An accessory back that snaps into the popular Multiconnect (and GOEWS) wall-mount
systems, so you can hang your own thing off a Multiconnect board. The back models
the male snap profile — a keyed, tapered snap tab that slides down into the
system's channel and locks — on a flat plate. Three accessory faces, each its own
studio mode:

  * "blank_back" — the base adapter: a flat plate with the snap back and nothing
                   else, ready for you to glue / screw your own object to.
  * "hook_back"  — the plate + snap plus a J-hook projecting forward, for hanging
                   cables, tools, bags, or cups.
  * "bin_back"   — the plate + snap plus a small open bin (tray) for parts, pens,
                   or oddments.

A `system` select switches the snap geometry between Multiconnect and GOEWS
spacing. Shared across the batch: a plate helper builds the flat back every mode
starts from.

The Multiconnect snap is approximated as a community-standard tapered snap tab
(a trapezoidal wedge whose lower edge is undercut so it catches the channel lip).
It is dimensionally close to the real profile; verify against your board for a
critical fit, or tune the exposed `snap_w` / `slot_pitch`.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `plate_w`).
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


# ── System snap table ─────────────────────────────────────────────────────────
# slot_pitch — vertical on-centre spacing of the system's snap channels (mm).
# snap_w     — width of one snap tab across the plate (mm).
# snap_proj  — how far the snap projects behind the plate into the channel (mm).
# snap_h     — vertical height of one snap tab (mm).
# undercut   — depth of the locking undercut lip (mm).
SYSTEM_TABLE = {
    "multiconnect": {"slot_pitch": 25.0, "snap_w": 23.0, "snap_proj": 6.5, "snap_h": 15.0, "undercut": 2.0},
    "goews":        {"slot_pitch": 25.0, "snap_w": 21.0, "snap_proj": 7.0, "snap_h": 16.0, "undercut": 2.4},
}


# ── Parameters ───────────────────────────────────────────────────────────────
# Read every injected global once at module scope (reference-cartridge pattern)
# so ruff sees the self-referential binding and does not flag F821.
system      = str(PARAM(lambda: system, "multiconnect"))  # multiconnect|goews
target_part = str(PARAM(lambda: target_part, ""))         # studio dispatch (part id)

plate_w     = float(PARAM(lambda: plate_w,  50.0))  # accessory plate width  X (mm)
plate_h     = float(PARAM(lambda: plate_h,  50.0))  # accessory plate height Z (mm)
plate_t     = float(PARAM(lambda: plate_t,   4.0))  # plate thickness (mm)
snap_rows   = int(PARAM(lambda: snap_rows,     2))  # number of snap tabs stacked up Z

# Custom overrides for the snap (used to fine-tune fit).
snap_w_o    = float(PARAM(lambda: snap_w,    0.0))  # override snap width (0 = table)
slot_pitch_o = float(PARAM(lambda: slot_pitch, 0.0))  # override slot pitch (0 = table)

# Hook parameters.
hook_len    = float(PARAM(lambda: hook_len,  35.0))  # forward reach of the hook (mm)
hook_dia    = float(PARAM(lambda: hook_dia,   8.0))  # hook rod diameter (mm)

# Bin parameters.
bin_depth   = float(PARAM(lambda: bin_depth, 40.0))  # how far the bin projects forward Y (mm)
bin_height  = float(PARAM(lambda: bin_height, 35.0)) # bin wall height Z (mm)
bin_wall    = float(PARAM(lambda: bin_wall,   2.4))  # bin wall thickness (mm)


# ── System resolution + clamps ───────────────────────────────────────────────
spec = SYSTEM_TABLE.get(system.strip().lower(), SYSTEM_TABLE["multiconnect"])
slot_pitch = slot_pitch_o if slot_pitch_o > 1.0 else spec["slot_pitch"]
snap_w = snap_w_o if snap_w_o > 1.0 else spec["snap_w"]
snap_proj = spec["snap_proj"]
snap_h = spec["snap_h"]
undercut = spec["undercut"]

plate_w = max(20.0, plate_w)
plate_h = max(20.0, plate_h)
plate_t = max(2.5, min(plate_t, 10.0))
snap_rows = max(1, min(snap_rows, 8))
snap_w = max(10.0, min(snap_w, plate_w - 4.0))
hook_len = max(10.0, min(hook_len, 120.0))
hook_dia = max(3.0, min(hook_dia, 20.0))
bin_depth = max(15.0, min(bin_depth, 150.0))
bin_height = max(10.0, min(bin_height, 120.0))
bin_wall = max(1.6, min(bin_wall, 6.0))

_part_ids = ("blank_back", "hook_back", "bin_back")
active_part = target_part if target_part in _part_ids else "blank_back"


# ── Shared plate helper (reused across the batch) ─────────────────────────────
def plate():
    """The flat accessory plate: footprint plate_w × plate_h, occupying
    Y:[0, plate_t] (y=0 is the wall-facing back), centered in X, base at z=0.
    The snap tabs project in -Y (behind the plate) into the system channel; the
    accessory (hook/bin) projects in +Y (out from the wall)."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_t / 2.0, plate_h / 2.0))
        .box(plate_w, plate_t, plate_h)
    )


def _snap_tab(z_center):
    """One male snap tab centred vertically at z_center, projecting behind the
    plate (into -Y). Profile in the Y-Z plane: a trapezoid tapering to the tip
    with a lower undercut lip that catches the channel. Extruded across snap_w."""
    y0 = 0.0                       # plate back face
    y1 = -snap_proj                # tip (deepest into the channel)
    ht = snap_h / 2.0
    # Y-Z outline (drawn on the XZ-like plane via a polyline in local coords).
    pts = [
        (y0, -ht),                 # bottom at plate face
        (y0, ht),                  # top at plate face
        (y1, ht - undercut),       # top tapers in toward the tip
        (y1, -ht + undercut * 0.4),# tip bottom
        (y0 - undercut, -ht),      # undercut lip hanging below, catches the lip
    ]
    tab = (
        cq.Workplane("YZ")
        .polyline([(p[0], p[1] + z_center) for p in pts])
        .close()
        .extrude(snap_w)
    )
    # `extrude` on YZ pushes along +X from x=0; recenter across snap_w.
    return tab.translate((-snap_w / 2.0, 0, 0))


def with_snaps(body):
    """Fuse `snap_rows` snap tabs up the back of the plate at slot_pitch spacing,
    centred vertically on the plate."""
    total = (snap_rows - 1) * slot_pitch
    z0 = plate_h / 2.0 - total / 2.0
    for i in range(snap_rows):
        zc = z0 + i * slot_pitch
        # Keep tabs within the plate height.
        zc = max(snap_h / 2.0 + 1.0, min(zc, plate_h - snap_h / 2.0 - 1.0))
        body = body.union(_snap_tab(zc))
    return body.clean()


# ── Builders ─────────────────────────────────────────────────────────────────
def build_blank_back():
    """The base adapter: plate + snap back only."""
    return with_snaps(plate())


def build_hook_back():
    """Plate + snap plus a J-hook: a horizontal rod projecting forward (+Y) from
    low on the plate, turning up at the tip to retain whatever hangs on it."""
    body = with_snaps(plate())
    z_hook = plate_h * 0.30
    # Horizontal rod from the plate front out to +Y.
    rod = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, z_hook, -plate_t))
        .cylinder(hook_len, hook_dia / 2.0)
    )
    rod = rod.translate((0, plate_t + hook_len / 2.0, 0))
    # Upturn at the tip.
    up = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_t + hook_len, z_hook + hook_dia * 0.9))
        .cylinder(hook_dia * 1.8, hook_dia / 2.0)
    )
    # Small fillet-like gusset where the rod meets the plate for strength.
    gusset = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, z_hook - hook_dia, 0))
        .box(hook_dia, hook_dia * 1.5, plate_t)
    )
    gusset = gusset.translate((0, plate_t / 2.0, 0))
    body = body.union(rod).union(up).union(gusset)
    return body.clean()


def build_bin_back():
    """Plate + snap plus a small open bin projecting forward (+Y): a solid block
    sized to plate_w × bin_depth × bin_height, hollowed from the top to a wall of
    bin_wall, fused to the plate front."""
    body = with_snaps(plate())
    # Outer bin block, front face of plate at y=plate_t.
    outer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_t + bin_depth / 2.0, bin_height / 2.0))
        .box(plate_w, bin_depth, bin_height)
    )
    # Cavity: open top, leaving a floor and walls of bin_wall.
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, plate_t + bin_depth / 2.0, bin_wall + bin_height / 2.0))
        .box(plate_w - 2.0 * bin_wall, bin_depth - 2.0 * bin_wall, bin_height)
    )
    bin_solid = outer.cut(cavity)
    body = body.union(bin_solid)
    return body.clean()


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active_part == "hook_back":
    result = build_hook_back()
elif active_part == "bin_back":
    result = build_bin_back()
else:
    result = build_blank_back()
