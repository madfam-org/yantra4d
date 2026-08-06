"""
Fermentation Airlock Grommet & Fitting — Yantra4D Hyperobject Cartridge
(CadQuery / B-Rep).

The gas-management interface of a fermenter: a printed grommet that seals an
airlock stem into a carboy/bucket bore, a simple printable bubbler-style airlock
body, and a blow-off adapter for vigorous fermentation. All share one CDG
interface — the carboy/bucket bore the grommet seats into.

  * "grommet"         — a bore GROMMET. A double-flanged waist that snaps into a
                        drilled bucket-lid / carboy hole, with a stepped through-
                        hole that grips a standard airlock stem.
  * "airlock_body"    — a simple printable BUBBLER airlock: an outer moat chamber
                        with a central inlet standpipe and a splash hood, all as
                        one watertight body (the classic twin-wall bubbler shape,
                        simplified so it prints without supports and holds a CO2
                        water seal).
  * "blowoff_adapter" — a BLOW-OFF ADAPTER: seats in the grommet like the airlock
                        stem, then steps up to a hose barb for a blow-off tube.

Watertight strategy: solids with pockets CUT in (hollow-by-cut). The grommet's
snap groove is a revolved bead fused to the body (volumetric, like the cup-lid
grip bead). The bubbler moat and centre bore are OPEN at the top — never sealed —
so no internal void is trapped. Fillets are applied to clean blanks before
through-holes are cut. No sphere-tangent unions.

FOOD-CONTACT NOTE: this contacts fermenting must / gas. Geometry only — food-safe
filament, sanitation, and a proper liquid seal are the maker's responsibility
(see README).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; parameters injected as bare globals.
  - Access params via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval.
  - Assign the final solid to a top-level name `result`.
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
bore_dia   = float(PARAM(lambda: bore_dia,    12.5))  # carboy/bucket bore diameter (mm)
stem_dia   = float(PARAM(lambda: stem_dia,     9.5))  # airlock stem OD to grip (mm)
wall       = float(PARAM(lambda: wall,         3.0))  # body wall thickness (mm)
flange_dia = float(PARAM(lambda: flange_dia,  20.0))  # grommet flange diameter (mm)
groove_w   = float(PARAM(lambda: groove_w,     3.0))  # snap-groove width = lid thickness (mm)
clearance  = float(PARAM(lambda: clearance,    0.3))  # printed-fit slop (per side, mm)
barb_dia   = float(PARAM(lambda: barb_dia,     9.0))  # blow-off hose barb OD (mm)

target_part = str( PARAM(lambda: target_part, "grommet"))  # grommet|airlock_body|blowoff_adapter

# ── Clamps ───────────────────────────────────────────────────────────────────
bore_dia   = max(8.0,  min(bore_dia, 40.0))
stem_dia   = max(4.0,  min(stem_dia, min(bore_dia - 1.0, 30.0)))
wall       = max(2.0,  min(wall, 6.0))
flange_dia = max(bore_dia + 4.0, min(flange_dia, bore_dia + 30.0))
groove_w   = max(1.5,  min(groove_w, 8.0))
clearance  = max(0.1,  min(clearance, 0.8))
barb_dia   = max(4.0,  min(barb_dia, 16.0))

bore_r = bore_dia / 2.0
stem_r = stem_dia / 2.0


# ── Part builders ────────────────────────────────────────────────────────────
def build_grommet():
    """A snap-in bore grommet. A cylindrical waist sized to the bore carries a
    top flange and a bottom retaining bead; the groove between them (width =
    `groove_w`, the lid thickness) snaps over the drilled hole. A stepped through-
    hole grips the airlock stem."""
    waist_r = bore_r - clearance                 # waist slips into the bore
    total_h = groove_w + 2.0 * wall              # flange + groove + bottom lip
    # Core body: a cylinder the height of the whole grommet.
    body = cq.Workplane("XY").circle(waist_r).extrude(total_h)

    # Top flange: a disk that sits ON the lid (can't pull through).
    flange = cq.Workplane("XY").circle(flange_dia / 2.0).extrude(wall)
    body = body.union(flange.translate((0, 0, total_h - wall)))

    # Bottom retaining bead: a revolved lip flaring past the bore so the grommet
    # can't pop out. Built as a revolved profile fused volumetrically.
    lip_r = bore_r + max(1.0, wall * 0.6)
    try:
        prof = (
            cq.Workplane("XZ")
            .polyline([
                (waist_r - 0.2, 0.0),
                (lip_r, 0.0),
                (waist_r - 0.2, wall),
            ])
            .close()
        )
        bead = prof.revolve(360, (0, 0, 0), (0, 1, 0))
        body = body.union(bead)
    except Exception:
        pass

    # Stepped stem through-hole: grips a standard airlock stem with clearance.
    hole_r = stem_r + clearance
    hole = cq.Workplane("XY").circle(hole_r).extrude(total_h + 4.0).translate((0, 0, -2.0))
    body = body.cut(hole)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_airlock_body():
    """A simple printable bubbler airlock as one watertight body.

    Concentric twin-wall cup: an outer chamber wall and an inner standpipe rise
    from a common floor. CO2 enters up the central standpipe, bubbles out under
    the standpipe rim into the water-filled outer moat, and escapes past the
    outer wall — the classic bubbler action. Everything opens UP (moat + centre
    bore) so no void is trapped; a printed splash hood is a separate concern left
    to a snap cap, keeping this a support-free single print."""
    # Sizes derived from the stem the airlock plugs into (bottom spigot).
    spigot_r = stem_r                             # matches the grommet stem grip
    inner_r = spigot_r + 2.0                      # central standpipe bore radius
    inner_wall = wall * 0.7
    moat_r = inner_r + inner_wall + 6.0           # outer chamber inner radius
    outer_r = moat_r + wall
    floor = wall
    height = 34.0

    # Solid outer cylinder blank; fillet the top rim on the clean blank BEFORE
    # cutting cavities.
    body = cq.Workplane("XY").circle(outer_r).extrude(height)
    try:
        body = body.edges(">Z").fillet(min(2.0, wall * 0.6))
    except Exception:
        pass

    # Outer moat: an annular channel cut from the top down to the floor (open at
    # top). Cut a full inner cylinder, then add the central standpipe back.
    moat = (
        cq.Workplane("XY")
        .circle(moat_r)
        .extrude(height - floor + 1.0)
        .translate((0, 0, floor))
    )
    body = body.cut(moat)

    # Central standpipe: a tube rising from the floor, its bore open through the
    # bottom spigot. Its rim stops below the top so gas can spill into the moat.
    pipe_h = height - 6.0
    pipe = (
        cq.Workplane("XY")
        .circle(inner_r + inner_wall)
        .extrude(pipe_h)
        .translate((0, 0, floor - 0.01))
    )
    body = body.union(pipe)

    # Bore the standpipe + bottom spigot as one through-channel (open both ends).
    channel = (
        cq.Workplane("XY")
        .circle(inner_r)
        .extrude(pipe_h + floor + 2.0)
        .translate((0, 0, -1.0))
    )
    body = body.cut(channel)

    # Bottom spigot: a short reduced tube under the floor that plugs the grommet.
    spigot_or = spigot_r + inner_wall
    spigot_h = 8.0
    spigot = (
        cq.Workplane("XY")
        .circle(spigot_or)
        .extrude(spigot_h)
        .translate((0, 0, -spigot_h + 0.01))
    )
    body = body.union(spigot)
    # Extend the central bore down through the spigot (still one open channel).
    spg_bore = (
        cq.Workplane("XY")
        .circle(spigot_r)
        .extrude(spigot_h + 1.0)
        .translate((0, 0, -spigot_h))
    )
    body = body.cut(spg_bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_blowoff_adapter():
    """Seats in the grommet like the airlock stem, then steps up to a hose barb
    for a blow-off tube during vigorous fermentation."""
    stem_grip_r = stem_r                          # matches the grommet stem grip
    stem_h = 14.0
    barb_r = barb_dia / 2.0
    barb_h = 20.0
    transition = 4.0

    # Lower stem plug (solid blank), then the barb column, then bore straight
    # through — the whole thing is one open tube.
    stem = cq.Workplane("XY").circle(stem_grip_r).extrude(stem_h)

    # Transition shoulder (a small collar so it seats to a stop on the grommet).
    collar = (
        cq.Workplane("XY")
        .circle(barb_r + 1.5)
        .extrude(transition)
        .translate((0, 0, stem_h))
    )

    # Barb column: a plain tube with two ring ridges for hose grip (each a
    # revolved bead fused volumetrically → watertight).
    col = (
        cq.Workplane("XY")
        .circle(barb_r)
        .extrude(barb_h)
        .translate((0, 0, stem_h + transition))
    )
    body = stem.union(collar).union(col)

    for frac in (0.35, 0.7):
        rz = stem_h + transition + barb_h * frac
        try:
            ridge = (
                cq.Workplane("XZ")
                .polyline([
                    (barb_r - 0.2, rz - 1.4),
                    (barb_r + 1.2, rz),
                    (barb_r - 0.2, rz + 1.4),
                ])
                .close()
                .revolve(360, (0, 0, 0), (0, 1, 0))
            )
            body = body.union(ridge)
        except Exception:
            pass

    # Through-bore: open at both ends (blow-off gas path).
    inner_r = max(1.5, barb_r - 2.0)
    bore = (
        cq.Workplane("XY")
        .circle(inner_r)
        .extrude(stem_h + transition + barb_h + 4.0)
        .translate((0, 0, -2.0))
    )
    body = body.cut(bore)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "airlock_body":
    result = build_airlock_body()
elif target_part == "blowoff_adapter":
    result = build_blowoff_adapter()
else:
    result = build_grommet()
