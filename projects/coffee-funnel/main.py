"""
Espresso Dosing Funnel & Ring — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A dosing aid that slips over an espresso portafilter basket rim to guide ground
coffee in cleanly and keep the counter tidy. Sized to a standard basket
("58mm", "54mm", or "51mm") — the three parts share one CDG interface, the
portafilter basket rim.

  * "dosing_funnel" — a friction RING that grips the basket rim, with a flared
                      FUNNEL wall above to guide grounds into the basket. Optional
                      magnet pockets for a magnetic dosing funnel.
  * "dosing_ring"   — a short RING / collar only (no flare) — a minimal dosing
                      cuff that raises the basket wall a few mm.
  * "leveler_base"  — a low BASE disc with a basket-locating skirt and a central
                      bore, used as a leveling / distribution reference that sits
                      on the basket.

Watertight strategy: solids of revolution built by hollow-by-cut (outer cylinder
minus inner bore) and a lofted funnel flare fused with a volumetric overlap. The
ring grips the basket via a shallow inward retaining bead — a revolved profile
fused to the wall (like the reference cup-lid grip bead), NOT a tangent kiss.
Magnet pockets are blind cylinders cut from the underside, leaving a solid floor
(no through-void); they open downward so no cavity is sealed. Fillets go on clean
blanks before bores are cut. No sphere-tangent unions.

FOOD-CONTACT NOTE: ground coffee passes through. Geometry only — food-safe
filament and hygiene are the maker's responsibility (see README).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; parameters injected as bare globals.
  - Access params via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
"""

import math

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Portafilter basket standards (nominal rim OD, mm) ────────────────────────
# Dosing rings slip OVER the basket rim, so the interface is the basket outer
# diameter. These are sensible nominal figures for each common size class.
BASKETS = {
    "58mm": {"rim_od": 58.0},
    "54mm": {"rim_od": 54.0},
    "51mm": {"rim_od": 51.0},
}


def basket_geo(name):
    return BASKETS.get(name, BASKETS["58mm"])


# ── Parameters ───────────────────────────────────────────────────────────────
basket      = str(  PARAM(lambda: basket,     "58mm"))  # 58mm|54mm|51mm
wall        = float(PARAM(lambda: wall,          2.6))  # ring wall thickness (mm)
ring_h      = float(PARAM(lambda: ring_h,        9.0))  # gripping ring height (mm)
funnel_h    = float(PARAM(lambda: funnel_h,     18.0))  # funnel flare height (mm)
flare       = float(PARAM(lambda: flare,        10.0))  # extra radius at the funnel top (mm)
clearance   = float(PARAM(lambda: clearance,     0.4))  # slip-fit slop over the rim (per side)
grip        = float(PARAM(lambda: grip,          0.6))  # inward retaining bead depth (mm)
magnets     = bool( PARAM(lambda: magnets,     False))  # magnet pockets (dosing funnel)
magnet_d    = float(PARAM(lambda: magnet_d,      6.2))  # magnet pocket diameter (mm)
magnet_h    = float(PARAM(lambda: magnet_h,      3.2))  # magnet pocket depth (mm)

target_part = str(  PARAM(lambda: target_part, "dosing_funnel"))  # dosing_funnel|dosing_ring|leveler_base

# ── Clamps ───────────────────────────────────────────────────────────────────
wall        = max(1.8,  min(wall, 6.0))
ring_h      = max(4.0,  min(ring_h, 25.0))
funnel_h    = max(6.0,  min(funnel_h, 40.0))
flare       = max(3.0,  min(flare, 30.0))
clearance   = max(0.1,  min(clearance, 1.0))
grip        = max(0.0,  min(grip, 1.2))
magnet_d    = max(3.0,  min(magnet_d, 12.0))
magnet_h    = max(1.5,  min(magnet_h, min(wall + 2.0, 6.0)))

rim_od = basket_geo(basket)["rim_od"]
ring_ir = rim_od / 2.0 + clearance          # ring inner radius (slips over rim)
ring_or = ring_ir + wall                    # ring outer radius


# ── Helpers ──────────────────────────────────────────────────────────────────
def _grip_bead(inner_r, z_center):
    """A shallow inward retaining bead on the ring bore that pinches the basket
    rim. Revolved profile fused volumetrically (root buried in the wall)."""
    if grip < 0.05:
        return None
    crest_r = inner_r - grip                 # bites inward past the rim
    root_r = inner_r + wall * 0.5            # root buried in the wall
    h = 2.4
    try:
        prof = (
            cq.Workplane("XZ")
            .polyline([
                (root_r, z_center - h / 2.0),
                (crest_r, z_center),
                (root_r, z_center + h / 2.0),
            ])
            .close()
        )
        return prof.revolve(360, (0, 0, 0), (0, 1, 0))
    except Exception:
        return None


def _magnet_pockets(base_z, ring_mid_r, n=3):
    """Blind magnet pockets opening DOWNWARD from the ring underside. Each a short
    cylinder cut into the wall, floor left solid (no through-void). Union of `n`
    pockets → one cutter."""
    cutter = None
    for i in range(n):
        ang = 2.0 * math.pi * i / n
        x = ring_mid_r * math.cos(ang)
        y = ring_mid_r * math.sin(ang)
        pk = (
            cq.Workplane("XY")
            .circle(magnet_d / 2.0)
            .extrude(magnet_h)
            .translate((x, y, base_z))
        )
        cutter = pk if cutter is None else cutter.union(pk)
    return cutter


# ── Part builders ────────────────────────────────────────────────────────────
def _ring_blank(height):
    """A plain gripping ring: outer cylinder minus the rim bore. Watertight tube."""
    outer = cq.Workplane("XY").circle(ring_or).extrude(height)
    bore = cq.Workplane("XY").circle(ring_ir).extrude(height + 2.0).translate((0, 0, -1.0))
    return outer.cut(bore)


def build_dosing_ring():
    """A short ring / collar that grips the basket rim (no funnel flare)."""
    body = _ring_blank(ring_h)
    bead = _grip_bead(ring_ir, ring_h * 0.5)
    if bead is not None:
        body = body.union(bead)
    # Soften the top rim.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.4, 0.8))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_dosing_funnel():
    """Gripping ring + a flared funnel wall above it, guiding grounds into the
    basket. Optional magnet pockets in the ring underside."""
    # Lower gripping ring.
    body = _ring_blank(ring_h)

    # Funnel flare: a conical wall rising from the ring top, widening by `flare`.
    # Built as outer loft minus inner loft (a real-thickness cone), fused with a
    # small vertical overlap onto the ring (volumetric union → watertight).
    ov = 1.0
    top_or = ring_or + flare
    top_ir = ring_ir + flare
    outer_cone = (
        cq.Workplane("XY")
        .circle(ring_or)
        .workplane(offset=funnel_h + ov)
        .circle(top_or)
        .loft(combine=True)
        .translate((0, 0, ring_h - ov))
    )
    inner_cone = (
        cq.Workplane("XY")
        .circle(ring_ir)
        .workplane(offset=funnel_h + ov + 2.0)
        .circle(top_ir)
        .loft(combine=True)
        .translate((0, 0, ring_h - ov - 1.0))
    )
    funnel = outer_cone.cut(inner_cone)
    body = body.union(funnel)

    # Grip bead in the lower ring bore.
    bead = _grip_bead(ring_ir, ring_h * 0.45)
    if bead is not None:
        body = body.union(bead)

    # Optional magnet pockets from the underside (blind, solid floor).
    if magnets:
        pk = _magnet_pockets(-0.01, (ring_ir + ring_or) / 2.0, n=3)
        if pk is not None:
            body = body.cut(pk)

    # Soften the top funnel lip.
    try:
        body = body.edges(">Z").fillet(min(wall * 0.4, 0.8))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_leveler_base():
    """A low base disc with a basket-locating skirt and a central bore — a
    leveling / distribution reference that sits on the basket. The skirt slips
    over the rim (shares the interface); the disc top is flat for a leveler."""
    disc_h = wall + 2.0
    skirt_h = ring_h
    base_or = ring_or + 4.0

    # Top disc.
    disc = cq.Workplane("XY").circle(base_or).extrude(disc_h).translate((0, 0, skirt_h))
    # Locating skirt (a ring below the disc that slips over the basket rim).
    skirt = _ring_blank(skirt_h)
    body = skirt.union(disc)

    # Central bore through the disc so grounds/air pass and it self-centers.
    bore_r = ring_ir * 0.55
    bore = (
        cq.Workplane("XY")
        .circle(bore_r)
        .extrude(disc_h + skirt_h + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(bore)

    # Grip bead in the skirt bore.
    bead = _grip_bead(ring_ir, skirt_h * 0.5)
    if bead is not None:
        body = body.union(bead)

    try:
        body = body.edges(">Z").fillet(min(wall * 0.4, 0.8))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "dosing_ring":
    result = build_dosing_ring()
elif target_part == "leveler_base":
    result = build_leveler_base()
else:
    result = build_dosing_funnel()
