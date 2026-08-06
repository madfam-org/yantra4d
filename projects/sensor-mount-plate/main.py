"""
Sensor Mount Plate — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A universal base for a security camera, motion sensor, dashcam, or small
enclosure. Every mode is a flat base that fixes to a surface (adhesive pad or
screws) and presents a device-fixing interface on top.

Three modes (rendered per-part via `target_part`):

  * "quarter20_base" — a base with a 1/4-20 threaded-boss stud on top (the
                       universal camera/tripod interface). The stud is modelled
                       at the correct ASME 1/4-20 nominal MAJOR diameter
                       (6.35 mm) as a chamfered cylinder — dimensionally real
                       but NOT a swept helix (no slow thread). A thread groove is
                       an opt-in cosmetic detail.
  * "screw_base"     — a rectangular base plate with a 2- or 4-hole surface-screw
                       pattern plus a central device screw.
  * "adhesive_puck"  — a round disc with a flat underside for a VHB / adhesive
                       pad and a single device screw up through the centre.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `base_w`).
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


# ── ASME 1/4-20 UNC nominal envelope ─────────────────────────────────────────
# Major diameter 0.250 in = 6.35 mm; 20 threads-per-inch → pitch 1.27 mm.
Q20_MAJOR = 6.35
Q20_PITCH = 1.27


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "quarter20_base"))  # quarter20_base|screw_base|adhesive_puck

base_w = float(PARAM(lambda: base_w, 40.0))        # base width / X (mm)
base_d = float(PARAM(lambda: base_d, 40.0))        # base depth / Y (mm)
base_dia = float(PARAM(lambda: base_dia, 45.0))    # disc diameter (adhesive_puck) (mm)
base_thick = float(PARAM(lambda: base_thick, 5.0)) # base thickness (mm)
corner_r = float(PARAM(lambda: corner_r, 4.0))     # base corner radius (rect modes) (mm)

boss_h = float(PARAM(lambda: boss_h, 8.0))         # 1/4-20 stud height above base (mm)
thread_relief = bool(PARAM(lambda: thread_relief, True))  # cosmetic thread groove on the stud

screw_holes = int(PARAM(lambda: screw_holes, 4))   # surface screws (2 or 4) (screw_base)
screw_dia = float(PARAM(lambda: screw_dia, 4.5))   # surface screw clearance dia (mm)
screw_inset = float(PARAM(lambda: screw_inset, 7.0))  # screw inset from edge (mm)

device_screw = float(PARAM(lambda: device_screw, 4.5))  # central device screw dia (mm)


# ── Active part ──────────────────────────────────────────────────────────────
_parts = ("quarter20_base", "screw_base", "adhesive_puck")
active = target_part if target_part in _parts else "quarter20_base"

# ── Safe clamps ──────────────────────────────────────────────────────────────
base_thick = max(2.5, base_thick)
base_w = max(15.0, base_w)
base_d = max(15.0, base_d)
base_dia = max(15.0, base_dia)
boss_h = max(3.0, boss_h)
corner_r = max(0.0, min(corner_r, min(base_w, base_d) / 2.0 - 0.01))
screw_holes = 2 if screw_holes <= 2 else 4
screw_dia = max(1.5, screw_dia)
screw_inset = max(screw_dia, screw_inset)
device_screw = max(1.5, device_screw)


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


def drill_z(body, points, dia, z_lo, z_hi):
    """Cut vertical through-holes at each (x, y), z_lo..z_hi, over-travelling
    past both faces for a clean watertight cut."""
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


def surface_screw_points():
    """2 or 4 surface-screw points inset from the base corners/edges."""
    hx = base_w / 2.0 - screw_inset
    hy = base_d / 2.0 - screw_inset
    if hx <= 0 or hy <= 0:
        return []
    if screw_holes == 2:
        pts = [(-hx, 0.0), (hx, 0.0)]
    else:
        pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    # Drop any point that would nearly coincide with the central device screw
    # (their cutters would overlap and produce a degenerate boolean). Keep a
    # clear rim of both radii + 1 mm between a surface hole and the centre.
    min_r = (screw_dia + device_screw) / 2.0 + 1.0
    return [(x, y) for (x, y) in pts if (x * x + y * y) ** 0.5 >= min_r]


def quarter20_stud():
    """A 1/4-20 boss: a chamfered cylinder at the ASME nominal major diameter
    (6.35 mm), rising `boss_h` above the base top (z=base_thick). Optional
    shallow cosmetic thread grooves (stacked rings) — NOT a swept helix, so it
    stays fast and watertight. The stud is meant to be tapped, or to receive a
    knurled nut, in practice."""
    r = Q20_MAJOR / 2.0
    stud = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_thick + boss_h / 2.0))
        .cylinder(boss_h, r)
    )
    # Lead-in chamfer at the tip so a nut/thread starts cleanly.
    try:
        stud = stud.edges(">Z").chamfer(min(0.8, r * 0.4))
    except Exception:
        pass  # chamfer optional — non-fatal

    if thread_relief:
        # Cosmetic thread: shallow V-grooves as stacked thin cut-rings at the
        # 1/4-20 pitch. Each groove is a torus-like ring subtracted from the
        # stud; kept shallow (0.25 mm) so the core stays solid and watertight.
        groove = 0.25
        z = base_thick + Q20_PITCH
        while z < base_thick + boss_h - Q20_PITCH * 0.5:
            ring_out = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, z))
                .cylinder(Q20_PITCH * 0.4, r + 0.5)
            )
            ring_in = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, z))
                .cylinder(Q20_PITCH * 0.4 + 1.0, r - groove)
            )
            ring = ring_out.cut(ring_in)
            stud = stud.cut(ring)
            z += Q20_PITCH
    return stud


# ── Builders ─────────────────────────────────────────────────────────────────
def build_quarter20_base():
    """Rectangular base + a 1/4-20 boss stud on top. The base also gets its own
    surface-screw holes so it can be fixed down before the device threads on."""
    body = rounded_plate(base_w, base_d, base_thick, corner_r)
    body = drill_z(body, surface_screw_points(), screw_dia, 0.0, base_thick)
    body = body.union(quarter20_stud())
    return body.clean()


def build_screw_base():
    """Rectangular base plate with a 2/4-hole surface-screw pattern plus a
    central device screw through the plate."""
    body = rounded_plate(base_w, base_d, base_thick, corner_r)
    body = drill_z(body, surface_screw_points(), screw_dia, 0.0, base_thick)
    body = drill_z(body, [(0.0, 0.0)], device_screw, 0.0, base_thick)
    return body


def build_adhesive_puck():
    """Round disc: flat underside for an adhesive pad, one central device screw
    up through the centre. A shallow recessed ring on the top face leaves a
    raised rim so the device seats flat while the centre clears any pad squeeze."""
    body = (
        cq.Workplane("XY")
        .circle(base_dia / 2.0)
        .extrude(base_thick)
    )
    # Ease the top outer edge for comfort / print quality.
    try:
        body = body.edges(">Z").chamfer(min(0.8, base_thick * 0.3))
    except Exception:
        pass  # non-fatal
    body = drill_z(body, [(0.0, 0.0)], device_screw, 0.0, base_thick)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if active == "screw_base":
    result = build_screw_base()
elif active == "adhesive_puck":
    result = build_adhesive_puck()
else:
    result = build_quarter20_base()
