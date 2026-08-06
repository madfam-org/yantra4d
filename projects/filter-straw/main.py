"""
Water Filter / Straw Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Threaded adapters that connect a personal filter straw, a sport spout, or a hose
to a standard 28 mm PET bottle neck. The 28 mm bottle finish is the near-universal
soda / water-bottle thread (28-410, and the lightweight carbonated PCO-1881 with a
27.4 mm OD and 2.7 mm pitch). This cartridge is a HOUSING / INTERFACE only — it
carries and couples a filter element; it is NOT itself a filter and does not make
water safe. See the README safety note.

  - straw_adapter : a 28 mm screw cap with a top spout tube that holds a personal
                    filter straw — thread onto a bottle, insert the straw, sip.
  - bottle_cap    : a 28 mm screw cap with a sport / bite-valve spout nipple and a
                    through bore — a drink-through cap for a bottle.
  - inline_coupler: a 28 mm screw cap on one end and a stepped hose barb on the
                    other, with a through bore — plumb a bottle to a hose or a
                    gravity-fed filter line.

Real dimensions (28 mm bottle finish):
  - major thread diameter : 28.0 mm (28-410 nominal / PCO-1881 class)
  - thread pitch          : 2.7 mm  (PCO-1881; 28-410 is ~2.82 mm / 9 TPI)

Watertight strategy:
  Every part is ONE solid. The 28 mm thread is a HELICAL RIB — a small profile
  swept along a `makeHelix` path and UNIONED into the wall with a 0.6 mm embed so
  the union overlaps (never tangent, never a cut groove — a cut/revolved groove
  yields a non-watertight mesh). The cap is a cup whose bore opens to the bottom
  face (vents); spouts and barbs are tubes with through bores (vent both ends).
  Fillets clean blanks BEFORE cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else default. `except Exception`
    catches the NameError the sandbox raises for an unbound parameter name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters (28 mm bottle finish) ─────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "straw_adapter"))
# "straw_adapter" | "bottle_cap" | "inline_coupler"

thread_d = float(PARAM(lambda: thread_d, 28.0))    # 28 mm bottle major diameter
pitch = float(PARAM(lambda: pitch, 2.7))           # thread pitch (PCO-1881 2.7 mm)
turns = float(PARAM(lambda: turns, 3.5))           # number of thread turns
wall = float(PARAM(lambda: wall, 2.6))             # cap / tube wall thickness (mm)
cap_h = float(PARAM(lambda: cap_h, 15.0))          # screw-cap skirt height (mm)
straw_d = float(PARAM(lambda: straw_d, 8.0))       # filter-straw / spout bore (mm)
barb_d = float(PARAM(lambda: barb_d, 10.0))        # hose barb outer diameter (mm)
fit = float(PARAM(lambda: fit, 0.3))               # straw press-fit clearance (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
thread_d = max(20.0, min(thread_d, 40.0))
pitch = max(2.0, min(pitch, 3.5))
turns = max(2.0, min(turns, 5.0))
wall = max(1.6, min(wall, 4.5))
cap_h = max(9.0, min(cap_h, 24.0))
straw_d = max(4.0, min(straw_d, 16.0))
barb_d = max(6.0, min(barb_d, 20.0))
fit = max(0.1, min(fit, 0.8))

cap_od = thread_d + 2.0 * wall + 1.6               # knurl-less cap outer diameter


# ── Shared helpers ───────────────────────────────────────────────────────────
def _fillet_z(solid, r):
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


def _internal_thread(major_d, thr_pitch, thr_turns, z_start):
    """A helical INTERNAL thread rib: a triangular profile swept along a helix on
    the bore radius and returned as a solid to UNION into a cap wall. The profile
    embeds 0.6 mm OUTWARD (into the wall) so the union overlaps — not tangent."""
    radius = major_d / 2.0
    height = thr_pitch * thr_turns
    depth = thr_pitch * 0.5
    embed = 0.6
    helix = cq.Wire.makeHelix(pitch=thr_pitch, height=height, radius=radius)
    path = cq.Workplane(obj=helix)
    thread = (
        cq.Workplane("XZ")
        .center(radius, 0)
        .polyline([
            (embed, -thr_pitch * 0.5),
            (embed, thr_pitch * 0.5),
            (-depth, 0.0),
        ]).close()
        .sweep(path, isFrenet=True)
    )
    return thread.translate((0, 0, z_start))


def _screw_cap():
    """The common 28 mm screw cap: a cup with a top floor and an internal helical
    thread. The bore opens to the BOTTOM face (vents); the thread is fused in."""
    body = (
        cq.Workplane("XY")
        .circle(cap_od / 2.0)
        .extrude(cap_h)
    )
    try:
        body = body.faces(">Z").edges().fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    # bore up from the bottom face, leaving a top floor of `wall` (opens down).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(thread_d / 2.0)
        .extrude(cap_h - wall + 0.5)
    )
    body = body.cut(bore)
    # fuse the helical thread starting a little above the mouth.
    body = body.union(_internal_thread(thread_d, pitch, turns, 1.5))
    # shallow grip flutes: unioned bosses around the skirt (solid, no voids).
    n = 12
    for i in range(n):
        ang = 360.0 / n * i
        boss = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, 0),
                         rotate=cq.Vector(0, 0, ang))
            .center(cap_od / 2.0, 0)
            .circle(0.9)
            .extrude(cap_h)
        )
        body = body.union(boss)
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_straw_adapter():
    """A 28 mm screw cap with a top spout tube that holds a personal filter straw.
    The straw press-fits into the spout bore; a through bore in the cap floor lets
    water pass from the bottle up the straw. One solid; all bores vent."""
    body = _screw_cap()
    # spout tube on top (overlaps the cap floor → solid weld).
    spout_od = straw_d + 2.0 * wall
    spout_h = 16.0
    spout = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h - 0.01))
        .circle(spout_od / 2.0)
        .extrude(spout_h)
    )
    try:
        spout = spout.edges(">Z").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    body = body.union(spout)
    # straw bore: from the TOP of the spout all the way through the cap floor
    # (opens to both the top spout face and the bottle side → vents).
    through = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle((straw_d + fit) / 2.0)
        .extrude(cap_h + spout_h + 1.0)
    )
    body = body.cut(through)
    return body


def build_bottle_cap():
    """A 28 mm screw cap with a sport / bite-valve spout nipple and a through
    bore — a drink-through cap. The nipple is a tapered tube; the bore vents from
    the nipple tip through the bottle side. One solid."""
    body = _screw_cap()
    # tapered sport nipple on top via a loft from a wide base to a narrow tip.
    base_od = straw_d + 2.0 * wall
    tip_od = straw_d * 0.8 + 1.2
    nip_h = 14.0
    nipple = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, cap_h - 0.01))
        .circle(base_od / 2.0)
        .workplane(offset=nip_h)
        .circle(tip_od / 2.0)
        .loft(combine=True)
    )
    body = body.union(nipple)
    # drink bore through the nipple and cap floor (vents tip + bottle side).
    through = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(max(2.0, (straw_d * 0.55)))
        .extrude(cap_h + nip_h + 1.0)
    )
    body = body.cut(through)
    return body


def build_inline_coupler():
    """A 28 mm screw cap on one end and a stepped hose barb on the other, with a
    through bore — plumb a bottle to a hose. The barb is two stacked frusta
    (loft) whose ridges grip the hose; the bore vents from the barb tip through
    the bottle side. One solid."""
    body = _screw_cap()
    # barb stack on top of the cap.
    z0 = cap_h - 0.01
    stem_od = barb_d - 1.5
    seg_h = 6.0
    n_barb = 2
    z = z0
    for i in range(n_barb):
        seg = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z))
            .circle(barb_d / 2.0)                 # wide ridge (bottom of segment)
            .workplane(offset=seg_h)
            .circle(stem_od / 2.0)                # narrow neck (top of segment)
            .loft(combine=True)
        )
        body = body.union(seg)
        z += seg_h
    # a short straight stem cap on top so the last neck isn't a knife edge.
    stem = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z - 0.01))
        .circle(stem_od / 2.0)
        .extrude(3.0)
    )
    body = body.union(stem)
    # through bore (vents barb tip + bottle side). Keep the bore strictly inside
    # the narrowest part of the barb (the stem neck) with a min 0.8 mm wall, so
    # the stem never severs into a separate body at small barb diameters.
    bore_r = min((barb_d - 2.0 * wall) / 2.0, stem_od / 2.0 - 0.8)
    bore_r = max(1.5, bore_r)
    through = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(bore_r)
        .extrude(cap_h + n_barb * seg_h + 3.0 + 1.0)
    )
    body = body.cut(through)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bottle_cap":
    result = build_bottle_cap()
elif target_part == "inline_coupler":
    result = build_inline_coupler()
else:
    result = build_straw_adapter()
