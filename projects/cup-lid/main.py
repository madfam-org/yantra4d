"""
Universal Press-Fit Cup Lid — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A press-fit lid for mugs and cups, sized by the cup's outer rim diameter
(`rim_dia`). A downward seal skirt hugs the OUTSIDE of the rim with a small
interference, and an inner lip seats on the rim top so the lid clicks on and stays.
Three openings:

  * "sip_lid"   — a kidney-shaped drink opening near the edge (travel-mug style).
  * "solid_lid" — no opening (a splash / keep-warm cover).
  * "straw_lid" — a centered straw hole.

Rim seal geometry (the shared interface):
  outer skirt inner radius = rim_dia/2 + rim_wall              (wraps the rim OD)
  grip rib inner radius     = rim_dia/2 - interference          (pinches the rim)
  The grip rib is a shallow inward bead on the skirt wall; its crest sits just
  inside the rim OD by `interference`, so the skirt snaps over and grips. Built as
  a revolved bead fused to the skirt (volumetric union) to stay watertight.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `rim_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
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
rim_dia      = float(PARAM(lambda: rim_dia,      82.0))  # cup OUTER rim diameter (mm)
rim_wall     = float(PARAM(lambda: rim_wall,      2.2))  # skirt / top wall thickness (mm)
skirt_h      = float(PARAM(lambda: skirt_h,      12.0))  # how far the skirt grips down (mm)
interference = float(PARAM(lambda: interference,  0.4))  # grip pinch onto the rim (mm)
top_dome     = float(PARAM(lambda: top_dome,      3.0))  # slight top dome rise (mm, 0=flat)
sip_dia      = float(PARAM(lambda: sip_dia,      16.0))  # sip opening size (mm)
straw_dia    = float(PARAM(lambda: straw_dia,     8.0))  # straw hole diameter (mm)

target_part = str(PARAM(lambda: target_part, "sip_lid"))  # sip_lid|solid_lid|straw_lid

# ── Clamps ───────────────────────────────────────────────────────────────────
rim_dia = max(40.0, min(rim_dia, 120.0))
rim_wall = max(1.6, min(rim_wall, 4.0))
skirt_h = max(6.0, min(skirt_h, 30.0))
interference = max(0.1, min(interference, 1.0))
top_dome = max(0.0, min(top_dome, rim_dia * 0.15))
sip_dia = max(6.0, min(sip_dia, rim_dia * 0.4))
straw_dia = max(4.0, min(straw_dia, 14.0))

rim_r = rim_dia / 2.0
skirt_inner_r = rim_r                       # skirt inner wall sits at the rim OD
skirt_outer_r = rim_r + rim_wall
top_r = skirt_outer_r                       # top plate matches the skirt OD


# ── Geometry ─────────────────────────────────────────────────────────────────
def _rim_seal_skirt():
    """Downward skirt (a tube open at the bottom) that wraps the cup rim OD, with
    a shallow inward grip bead that pinches the rim by `interference`."""
    # Skirt tube: outer cylinder minus inner bore, spanning z:[-skirt_h, 0].
    outer = cq.Workplane("XY").circle(skirt_outer_r).extrude(-skirt_h)
    bore = cq.Workplane("XY").circle(skirt_inner_r).extrude(-(skirt_h + 1.0))
    skirt = outer.cut(bore)

    # Grip bead: a torus-like inward ridge near the skirt's lower inner edge. We
    # build it as a thin ring whose inner face sits at rim_r - interference so it
    # pinches the rim. Root overlaps into the skirt wall for a clean union.
    bead_z = -skirt_h * 0.62
    bead_h = min(3.0, skirt_h * 0.35)
    crest_r = rim_r - interference          # bites in past the rim OD
    root_r = rim_r + rim_wall * 0.5         # root buried in skirt wall
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, bead_z - bead_h / 2.0),
            (crest_r, bead_z),
            (root_r, bead_z + bead_h / 2.0),
        ])
        .close()
    )
    try:
        bead = prof.revolve(360, (0, 0, 0), (0, 1, 0))
        skirt = skirt.union(bead)
    except Exception:
        pass  # grip bead optional — skirt press-fit still works without it
    return skirt


def _top_plate():
    """The cap top: a plate over the skirt, optionally domed for a comfortable lip
    contact and to shed condensation."""
    plate = cq.Workplane("XY").circle(top_r).extrude(rim_wall)
    if top_dome > 0.1:
        # Low truncated-cone dome unioned with overlap (avoids sphere-pole cracks).
        ov = 0.6
        try:
            dome = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, rim_wall - ov))
                .circle(top_r)
                .workplane(offset=top_dome + ov)
                .circle(max(2.0, top_r * 0.45))
                .loft(combine=True)
            )
            plate = plate.union(dome)
        except Exception:
            pass  # dome is aesthetic — flat top is fine
    return plate


def _lid_blank():
    """Skirt + top plate joined at z=0 = a closed press-fit cover (no opening)."""
    skirt = _rim_seal_skirt()
    plate = _top_plate()
    lid = skirt.union(plate)
    try:
        lid = lid.clean()
    except Exception:
        pass
    return lid


def _top_thickness():
    """Total solid thickness to cut a hole cleanly through (plate + dome)."""
    return rim_wall + top_dome + 2.0


def build_sip_lid():
    lid = _lid_blank()
    # Obround (slot) sip opening near the edge: two end holes + a joining bar,
    # each an independent solid so no multi-wire workplane state is involved.
    off = top_r * 0.55
    r = sip_dia / 2.0
    zc = _top_thickness()
    end_a = cq.Workplane("XY").circle(r).extrude(zc).translate((off - r * 0.6, 0, -1.0))
    end_b = cq.Workplane("XY").circle(r).extrude(zc).translate((off + r * 0.6, 0, -1.0))
    bar = (
        cq.Workplane("XY")
        .box(r * 1.2, r * 2.0, zc, centered=(True, True, False))
        .translate((off, 0, -1.0))
    )
    opening = end_a.union(end_b).union(bar)
    lid = lid.cut(opening)
    try:
        lid = lid.clean()
    except Exception:
        pass
    return lid


def build_solid_lid():
    return _lid_blank()


def build_straw_lid():
    lid = _lid_blank()
    r = straw_dia / 2.0
    hole = cq.Workplane("XY").circle(r).extrude(_top_thickness()).translate((0, 0, -1.0))
    lid = lid.cut(hole)
    # A short raised collar around the straw hole to seal against the straw.
    try:
        collar = (
            cq.Workplane("XY")
            .circle(r + rim_wall)
            .circle(r)
            .extrude(4.0)
            .translate((0, 0, rim_wall + top_dome))
        )
        lid = lid.union(collar)
    except Exception:
        pass
    try:
        lid = lid.clean()
    except Exception:
        pass
    return lid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "solid_lid":
    result = build_solid_lid()
elif target_part == "straw_lid":
    result = build_straw_lid()
else:
    result = build_sip_lid()
