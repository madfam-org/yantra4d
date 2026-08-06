"""
Universal / D-Shaft Coupler — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Joins two shafts end-to-end. Each end has its own bore: a round hole or a D-flat
(circle with one chord flat) for a flatted shaft. The coupler is locked by radial
set screws (grub screws into each bore) or by a pinch clamp (a slit plus a clamp
bolt). An optional flexible section — a ring of interleaved beam slots cut in the
middle — absorbs small shaft misalignment while staying watertight.

Modes (dispatched via `target_part`):
  * "rigid"    — a solid coupler, both bores the same diameter.
  * "flexible" — adds the interleaved beam-slot section for misalignment.
  * "stepped"  — the two bores are DIFFERENT diameters (a reducing coupler).

Bore geometry:
  * round  — a plain circular bore of the given diameter (+ print clearance).
  * D-flat — a circle with ONE flat chord cut `flat_depth` in from the wall,
             matching a shaft with a machined flat.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `bore_a`).
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
bore_a       = float(PARAM(lambda: bore_a,        6.35))   # bore A diameter, mm (1/4")
bore_a_type  = str(  PARAM(lambda: bore_a_type, "round"))  # "round" | "D-flat"
bore_b       = float(PARAM(lambda: bore_b,        5.0))    # bore B diameter, mm
bore_b_type  = str(  PARAM(lambda: bore_b_type, "round"))  # "round" | "D-flat"
outer_dia    = float(PARAM(lambda: outer_dia,    19.0))    # coupler outer diameter, mm
length        = float(PARAM(lambda: length,      25.0))    # overall length, mm
flat_depth    = float(PARAM(lambda: flat_depth,   0.5))    # D-flat depth from the wall
clamp_style   = str(  PARAM(lambda: clamp_style, "setscrew"))  # "setscrew" | "clamp"
setscrew_dia  = float(PARAM(lambda: setscrew_dia,  3.2))   # grub screw clearance (≈ M3)
flexible      = bool( PARAM(lambda: flexible,    False))   # helical/beam flex section

target_part = str(  PARAM(lambda: target_part, "rigid"))   # rigid|flexible|stepped


# ── Derived / clamped geometry ───────────────────────────────────────────────
outer_dia = max(8.0, outer_dia)
outer_r = outer_dia / 2.0
length = max(10.0, length)
CLR = 0.15                                      # per-side bore print clearance

# In stepped mode the bores stay independent; otherwise B matches A.
if target_part != "stepped":
    bore_b = bore_a
    bore_b_type = bore_a_type

bore_a = max(2.0, min(bore_a, outer_dia - 3.0))
bore_b = max(2.0, min(bore_b, outer_dia - 3.0))
flat_depth = max(0.0, min(flat_depth, min(bore_a, bore_b) / 2.0 - 0.6))
setscrew_dia = max(1.5, setscrew_dia)

want_flex = flexible or target_part == "flexible"

# Each bore reaches to just short of the mid-plane so a web / flex band remains.
bore_len = length / 2.0 - 1.0


# ── Bore cutters ──────────────────────────────────────────────────────────────
def round_bore_cutter(dia, up_from, height):
    """Cylindrical bore of (dia/2 + clearance), extruded `height` from up_from."""
    r = dia / 2.0 + CLR
    return (
        cq.Workplane("XY")
        .circle(r)
        .extrude(height)
        .translate((0, 0, up_from))
    )


def dflat_bore_cutter(dia, up_from, height):
    """Round bore with ONE flat chord cut `flat_depth` in from the +X wall."""
    r = dia / 2.0 + CLR
    cutter = round_bore_cutter(dia, up_from, height)
    if flat_depth <= 0.02:
        return cutter
    # Subtract the outboard sliver so material past x = (r - flat_depth) is kept
    # inside the shaft flat: the cut leaves a chord on the +X side.
    sliver = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((r - flat_depth) + r, 0, up_from + height / 2.0))
        .box(2.0 * r, 2.2 * r + 2.0, height + 2.0, centered=(True, True, True))
    )
    return cutter.cut(sliver)


def make_bore(dia, kind, up_from, height):
    if kind == "D-flat":
        return dflat_bore_cutter(dia, up_from, height)
    return round_bore_cutter(dia, up_from, height)


# ── Locking features ──────────────────────────────────────────────────────────
def add_setscrews(body):
    """One radial grub-screw hole into each bore, near each end."""
    d = max(1.5, min(setscrew_dia, outer_dia * 0.35))
    z_a = max(2.5, bore_len * 0.5)
    z_b = length - max(2.5, bore_len * 0.5)
    for z in (z_a, z_b):
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, z, 0))
            .circle(d / 2.0)
            .extrude(outer_r + 0.5)     # centre outward through +X wall
        )
        body = body.cut(hole)
    return body


def add_clamp(body):
    """A pinch clamp on each end: an axial slit through the wall into the bore,
    plus a cross bolt to squeeze it. Kept watertight (the slit is a thin slab)."""
    slit_w = 1.2
    for (z0, z1) in ((0.5, bore_len + 0.5), (length - bore_len - 0.5, length - 0.5)):
        # Radial slit from the +X wall to the bore, across the full end length.
        slit = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(outer_r / 2.0, 0, (z0 + z1) / 2.0))
            .box(outer_r + 1.0, slit_w, (z1 - z0), centered=(True, True, True))
        )
        body = body.cut(slit)
        # Cross clamp bolt (through the two ears the slit forms), along Y.
        zc = (z0 + z1) / 2.0
        bolt = (
            cq.Workplane("XZ")
            .transformed(offset=cq.Vector(0, zc, 0))
            .center(outer_r * 0.6, 0)
            .circle(setscrew_dia / 2.0)
            .extrude(outer_dia + 2.0)
            .translate((0, -(outer_dia + 2.0) / 2.0, 0))
        )
        body = body.cut(bolt)
    return body


def add_flex(body):
    """Interleaved beam-coupler slots in the middle band: thin slots alternating
    side to leave a central spine, evoking a helical flex coupler."""
    band = min(length * 0.5, outer_dia * 0.9)
    mid0 = length / 2.0 - band / 2.0
    mid1 = length / 2.0 + band / 2.0
    n = max(4, int(round(band / 2.4)))
    slot_w = max(0.8, min(1.4, band / (n * 1.6)))
    spine = max(1.5, outer_r * 0.28)
    cutter = None
    for i in range(n):
        z = mid0 + (mid1 - mid0) * (i + 0.5) / n
        ang = 180.0 * i / n
        side = 1.0 if (i % 2 == 0) else -1.0
        slot = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z), rotate=cq.Vector(0, 0, ang))
            .box(2.0 * outer_r + 2.0, slot_w, slot_w, centered=(True, True, True))
        )
        slot = slot.translate((0, side * spine, 0))
        cutter = slot if cutter is None else cutter.union(slot)
    if cutter is not None:
        body = body.cut(cutter)
    return body


# ── Assemble ─────────────────────────────────────────────────────────────────
def build():
    body = cq.Workplane("XY").circle(outer_r).extrude(length)
    # Bore A from the bottom, Bore B from the top.
    body = body.cut(make_bore(bore_a, bore_a_type, -0.5, bore_len + 0.5))
    body = body.cut(make_bore(bore_b, bore_b_type, length - bore_len, bore_len + 0.5))
    if want_flex:
        body = add_flex(body)
    if clamp_style == "clamp":
        body = add_clamp(body)
    else:
        body = add_setscrews(body)
    return body


result = build()
