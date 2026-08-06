"""
FPV Camera Cage — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Protects and angles a micro FPV camera. The camera drops into a cradle pocket
sized to the standard form factor (nano 14 mm, micro 19 mm, mini 21 mm) and the
whole assembly tilts to a chosen up-angle, with tabs that bolt to the frame's
side plates. Three modes trade protection for weight: a full protective cage, an
open tilt bracket, and a minimal naked mount.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `cam_size`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use
    globals()/eval/getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Camera form-factor table (nominal body width in mm) ──────────────────────
CAM_SIZES = {"nano": 14.0, "micro": 19.0, "mini": 21.0}


def cam_body(size):
    """Return (width, height, depth) for the camera body by form factor.
    FPV cams are near-square in front; depth is the lens+board stack."""
    w = CAM_SIZES.get(size, 19.0)
    return (w, w, w * 0.85)


# ── Parameters ───────────────────────────────────────────────────────────────
cam_size    = str(  PARAM(lambda: cam_size, "micro"))    # nano | micro | mini
tilt        = float(PARAM(lambda: tilt,        30.0))    # camera up-tilt angle (deg)
wall        = float(PARAM(lambda: wall,         2.0))    # cradle wall thickness
cam_clear   = float(PARAM(lambda: cam_clear,    0.4))    # per-side clearance around the cam
mount_width = float(PARAM(lambda: mount_width, 19.0))    # frame plate spacing (tab centres)
tab_thick   = float(PARAM(lambda: tab_thick,    3.0))    # mount tab thickness
tab_hole_d  = float(PARAM(lambda: tab_hole_d,   2.2))    # tab bolt hole (M2 default)
base_h      = float(PARAM(lambda: base_h,       6.0))    # mount base height below the cradle
lens_hole   = bool( PARAM(lambda: lens_hole,   True))    # cut a lens aperture in the front

target_part = str(PARAM(lambda: target_part, "cage"))
# "cage" | "tilt_mount" | "naked_mount"


# ── Derived / clamped geometry ───────────────────────────────────────────────
cw, ch, cd = cam_body(cam_size)
pocket_w = cw + 2.0 * cam_clear
pocket_h = ch + 2.0 * cam_clear
pocket_d = cd + 2.0 * cam_clear
out_w = pocket_w + 2.0 * wall
out_h = pocket_h + 2.0 * wall
out_d = pocket_d + wall               # closed at the back only
tilt = max(0.0, min(tilt, 55.0))
tab_r = max(0.6, tab_hole_d / 2.0)
lens_r = max(2.0, min(cw, ch) * 0.32)


def _cam_shell():
    """The camera housing shell: an outer block with the cradle pocket cut from
    the front (+Y open), optionally a lens aperture in the back (-Y closed) wall.
    Built centred in X/Z, front face at Y=0, extending back to Y=-out_d."""
    shell = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -out_d / 2.0, 0))
        .box(out_w, out_d, out_h, centered=(True, True, True))
    )
    # Pocket opens toward +Y (front); leave `wall` at the back.
    pocket = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -pocket_d / 2.0 + 0.5, 0))
        .box(pocket_w, pocket_d + 1.0, pocket_h, centered=(True, True, True))
    )
    shell = shell.cut(pocket)
    # Lens aperture through the back wall so the picture / focus is reachable.
    if lens_hole:
        aperture = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, 0, out_d))
            .circle(lens_r)
            .extrude(-out_d - 2.0)
        )
        shell = shell.cut(aperture)
    return shell


def _cage_bars():
    """Protective bars across the open front for the full-cage mode: a rim frame
    plus a diagonal cross that shields the lens from impacts while leaving the
    view mostly clear."""
    bar = max(1.4, wall * 0.7)
    rim_w, rim_h = out_w, out_h
    # Build the 4-sided front rim frame by unioning four bars just ahead of the
    # open pocket face (Y ~ 0).
    top = cq.Workplane("XY").transformed(offset=cq.Vector(0, bar / 2.0, rim_h / 2.0 - bar / 2.0)).box(rim_w, bar, bar, centered=(True, True, True))
    bot = cq.Workplane("XY").transformed(offset=cq.Vector(0, bar / 2.0, -rim_h / 2.0 + bar / 2.0)).box(rim_w, bar, bar, centered=(True, True, True))
    lft = cq.Workplane("XY").transformed(offset=cq.Vector(-rim_w / 2.0 + bar / 2.0, bar / 2.0, 0)).box(bar, bar, rim_h, centered=(True, True, True))
    rgt = cq.Workplane("XY").transformed(offset=cq.Vector(rim_w / 2.0 - bar / 2.0, bar / 2.0, 0)).box(bar, bar, rim_h, centered=(True, True, True))
    rim = top.union(bot).union(lft).union(rgt)
    # Diagonal guard bar across the front (one strut is enough to break a fall).
    diag_len = math.sqrt(rim_w * rim_w + rim_h * rim_h) - bar
    diag_ang = math.degrees(math.atan2(rim_h, rim_w))
    diag = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, bar / 2.0, 0), rotate=cq.Vector(0, diag_ang, 0))
        .box(diag_len, bar, bar, centered=(True, True, True))
    )
    return rim.union(diag)


def _mount_base_and_tabs():
    """A base block under the housing plus two side tabs that bolt to the frame
    plates at `mount_width` spacing. The base is what the housing tilts on."""
    base = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -out_d / 2.0, -out_h / 2.0 - base_h / 2.0))
        .box(out_w, out_d, base_h, centered=(True, True, True))
    )
    try:
        base = base.edges("|Y").fillet(min(1.5, base_h / 2.0 - 0.4))
    except Exception:
        pass
    # Two tabs projecting out in +/-X, each with a bolt hole through X.
    tabs = None
    tab_z = -out_h / 2.0 - base_h / 2.0
    tab_span = max(mount_width, out_w) + 2.0 * tab_thick
    for sx in (-1.0, 1.0):
        tab = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(sx * (tab_span / 2.0 - tab_thick / 2.0), -out_d / 2.0, tab_z))
            .box(tab_thick, out_d * 0.8, base_h, centered=(True, True, True))
        )
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(-out_d / 2.0, tab_z, sx * (tab_span / 2.0)))
            .circle(tab_r)
            .extrude(tab_thick * 2.0, both=True)
        )
        tab = tab.cut(hole)
        tabs = tab if tabs is None else tabs.union(tab)
    return base.union(tabs)


def _tilt_and_place(housing):
    """Tilt the housing up by `tilt` degrees about X (nose up) so it looks upward
    like a real FPV cam, then sit it on the mount base."""
    tilted = housing.rotate((0, 0, 0), (1, 0, 0), -tilt)
    return tilted


def build_cage():
    """Full protective cage: shell + front guard bars, on the tilting mount."""
    shell = _cam_shell().union(_cage_bars())
    shell = _tilt_and_place(shell)
    return shell.union(_mount_base_and_tabs())


def build_tilt_mount():
    """Open tilt bracket: the shell (no front bars) on the tilting mount — the
    lightest weather/impact-tolerant option that still cradles the cam."""
    shell = _tilt_and_place(_cam_shell())
    return shell.union(_mount_base_and_tabs())


def build_naked_mount():
    """Minimal mount: a thin backing plate with the lens aperture and side tabs,
    for 'naked'/board cameras where the cam is bolted flat, no full pocket."""
    plate = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -wall / 2.0, 0))
        .box(out_w, wall, out_h, centered=(True, True, True))
    )
    if lens_hole:
        aperture = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, 0, wall + 1.0))
            .circle(lens_r)
            .extrude(-wall - 2.0)
        )
        plate = plate.cut(aperture)
    # Two small cam-fixing holes flanking the aperture (M2 board mount).
    for sx in (-1.0, 1.0):
        h = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(sx * cw * 0.36, 0, wall + 1.0))
            .circle(tab_r)
            .extrude(-wall - 2.0)
        )
        plate = plate.cut(h)
    plate = _tilt_and_place(plate)
    return plate.union(_mount_base_and_tabs())


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "tilt_mount":
    result = build_tilt_mount()
elif target_part == "naked_mount":
    result = build_naked_mount()
else:  # "cage"
    result = build_cage()
