"""Bag Feet — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The dome studs set into the base of a handbag or a briefcase so the bag stands off the
floor and the leather does not scuff. A foot is a shallow dome on a flange, with a boss
underneath that goes through a punched hole in the base panel; a backing washer inside the
bag spreads the load so the foot does not pull through the leather. This is the rigid hard
good the Fashion Cabinet `bag-feet` notion places and bridges to here for its geometry.

Two boss styles, chosen with `prong_style`:
  * "screw" — a bossed post with a cosmetic sawtooth thread the washer screws onto.
  * "prong" — two flat splayable tabs that fold over the washer, the traditional setting.

Modes (dispatched via `target_part`):
  * "foot"   — the dome with its flange and boss.
  * "washer" — the backing washer for the inside of the base panel.
  * "set"    — one foot and one washer, laid out on one plate as separate bodies.

Geometry: the dome is a REVOLVED profile with a flat crown land — never a cylinder plus a
sphere cap, which is banned in this commons because the sphere pole reads as a crack. The
thread is a stack of revolved sawtooth rings, never a helical sweep.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `foot_dia`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
foot_dia    = float(PARAM(lambda: foot_dia,    14.0))  # dome outside diameter (mm)
foot_h      = float(PARAM(lambda: foot_h,       7.0))  # dome height above the flange (mm)
flange_t    = float(PARAM(lambda: flange_t,     1.6))  # flange thickness under the dome (mm)
boss_dia    = float(PARAM(lambda: boss_dia,     5.0))  # boss diameter through the panel (mm)
panel_t     = float(PARAM(lambda: panel_t,      3.0))  # base-panel thickness the boss spans (mm)
washer_dia  = float(PARAM(lambda: washer_dia,  16.0))  # backing washer outside diameter (mm)
washer_t    = float(PARAM(lambda: washer_t,     1.8))  # backing washer thickness (mm)
prong_style = str(  PARAM(lambda: prong_style, "screw"))  # screw|prong

target_part = str(PARAM(lambda: target_part, "set"))  # foot|washer|set

# ── Safe clamps ──────────────────────────────────────────────────────────────
# Commercial bag feet run 10-20 mm across the dome; luggage studs go to 25 mm.
foot_dia   = max(8.0, min(foot_dia, 30.0))
foot_h     = max(2.0, min(foot_h, foot_dia * 0.75))
flange_t   = max(0.8, min(flange_t, 4.0))
# The boss must leave real flange around it.
boss_dia   = max(2.5, min(boss_dia, foot_dia - 4.0))
panel_t    = max(0.8, min(panel_t, 10.0))
washer_dia = max(boss_dia + 4.0, min(washer_dia, 40.0))
washer_t   = max(0.8, min(washer_t, 5.0))
if prong_style not in ("screw", "prong"):
    prong_style = "screw"

# ── Derived geometry ─────────────────────────────────────────────────────────
flange_dia = foot_dia                    # the flange is the dome's own footprint
boss_len = panel_t + washer_t + 1.6      # through the panel, the washer, plus a set-over
crown_r = max(0.5, foot_dia * 0.16)      # flat crown land radius (no pole singularity)
bore_dia = boss_dia + 0.4                # washer bore: boss plus a slip fit
thread_pitch = max(0.6, min(boss_dia * 0.26, 1.1))
thread_depth = thread_pitch * 0.45
prong_w = max(1.2, boss_dia * 0.42)      # each splayable tab's width
prong_gap = max(0.8, boss_dia * 0.3)     # the slot between the two tabs


def _dome_profile():
    """The foot's revolved section: flange, shoulder, dome flank, flat crown land.

    One closed 2D profile revolved 360 degrees — this is how the house builds domes.
    A cylinder unioned with a sphere cap is banned: the sphere's pole reads as a crack.
    """
    r = foot_dia / 2.0
    return (
        cq.Workplane("XZ")
        .moveTo(0, 0)
        .lineTo(r, 0)                                    # flange underside out to the rim
        .lineTo(r, flange_t)                             # flange rim
        .lineTo(r * 0.94, flange_t + foot_h * 0.30)      # shoulder
        .lineTo(r * 0.74, flange_t + foot_h * 0.68)      # dome flank
        .lineTo(crown_r, flange_t + foot_h)              # crown shoulder
        .lineTo(0, flange_t + foot_h)                    # flat crown land
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )


def _thread_rings(r_ref, z0, length):
    """A cosmetic sawtooth thread: revolved triangular rings, one per turn, no helix."""
    turns = max(1, int(length / thread_pitch))
    solids = None
    for i in range(turns):
        zc = z0 + (i + 0.5) * thread_pitch
        ring = (
            cq.Workplane("XZ")
            .moveTo(r_ref, zc - thread_pitch * 0.5)
            .lineTo(r_ref + thread_depth, zc)
            .lineTo(r_ref, zc + thread_pitch * 0.5)
            .close()
            .revolve(360, (0, 0, 0), (0, 1, 0))
        )
        solids = ring if solids is None else solids.union(ring)
    return solids


def build_foot():
    """Dome + flange + boss, in whichever boss style is selected.

    The dome sits above Z=0 and the boss hangs below it, so the part prints dome-down
    with the flange as a natural brim.
    """
    body = _dome_profile()

    # Boss: a post hanging below the flange, overlapping it by 0.5 mm.
    boss = (
        cq.Workplane("XY")
        .circle(boss_dia / 2.0)
        .extrude(boss_len + 0.5)
        .translate((0, 0, -boss_len))
    )
    body = body.union(boss)

    if prong_style == "screw":
        # Cosmetic external thread over the portion of the boss beyond the panel.
        # It must START ABOVE the tip taper: a thread ring straddling the taper cut
        # gets sliced into a floating sliver (a real second body, caught in
        # verification), so clear the taper zone by 1.2 mm.
        taper_clear = 1.2
        t_z0 = -boss_len + taper_clear
        t_len = max(1.0, boss_len - panel_t - 0.4 - taper_clear)
        teeth = _thread_rings(boss_dia / 2.0 - 0.05, t_z0, t_len)
        if teeth is not None:
            body = body.union(teeth)
        # Lead-in taper at the boss tip: cut a ring minus a cone frustum. Never a
        # .chamfer() after the thread union — that ordering is the segfault trap.
        tip_z = -boss_len
        # The cone must span the FULL height of the ring cutter (and overshoot both
        # ends), otherwise the ring shaves the boss clean through above the cone and
        # severs the tip into a floating body — exactly what verification caught here.
        ring_h = 1.1
        cone = (
            cq.Workplane("XY")
            .circle(boss_dia / 2.0 * 0.6)
            .workplane(offset=ring_h + 0.6)
            .circle(boss_dia / 2.0 + thread_depth + 3.0)
            .loft(ruled=True)
            .translate((0, 0, tip_z - 0.4))
        )
        ring = (
            cq.Workplane("XY")
            .circle(boss_dia / 2.0 + thread_depth + 2.0)
            .extrude(ring_h)
            .translate((0, 0, tip_z - 0.2))
        )
        body = body.cut(ring.cut(cone))
    else:
        # Prong style: split the boss's free end into two flat splayable tabs by cutting
        # a slot across it. The slot opens at the tip and is oversized in every
        # direction, so it is never a sealed internal void.
        slot_depth = max(1.0, boss_len - panel_t * 0.5)
        slot = (
            cq.Workplane("XY")
            .box(boss_dia + 6.0, prong_gap, slot_depth + 2.0)
            .translate((0, 0, -boss_len - 1.0 + (slot_depth + 2.0) / 2.0))
        )
        body = body.cut(slot)
        # Thin the tabs so they actually bend: pare each one to prong_w in plan.
        keep = (
            cq.Workplane("XY")
            .box(prong_w, boss_dia + 6.0, slot_depth + 2.0)
            .translate((0, 0, -boss_len - 1.0 + (slot_depth + 2.0) / 2.0))
        )
        pare = (
            cq.Workplane("XY")
            .box(boss_dia + 8.0, boss_dia + 8.0, slot_depth + 2.0)
            .translate((0, 0, -boss_len - 1.0 + (slot_depth + 2.0) / 2.0))
            .cut(keep)
        )
        body = body.cut(pare)
    return body


def build_washer():
    """Backing washer: a flat disc with a bore, and a matching thread if screw style."""
    disc = cq.Workplane("XY").circle(washer_dia / 2.0).extrude(washer_t)
    try:
        disc = disc.edges(">Z").fillet(min(washer_t * 0.3, 0.5))
    except Exception:
        pass
    if prong_style == "screw":
        # Internal thread built INTO the cutter: bore cylinder unioned with the ring
        # stack, then one single cut. Cutting once is what keeps this watertight.
        cutter = (
            cq.Workplane("XY")
            .circle(bore_dia / 2.0)
            .extrude(washer_t + 4.0)
            .translate((0, 0, -2.0))
        )
        teeth = _thread_rings(bore_dia / 2.0 - 0.05, -0.3, washer_t + 0.6)
        if teeth is not None:
            cutter = cutter.union(teeth)
        return disc.cut(cutter)
    # Prong style: a plain bore, oversized cutter overshooting both faces.
    bore = (
        cq.Workplane("XY")
        .circle(bore_dia / 2.0)
        .extrude(washer_t + 4.0)
        .translate((0, 0, -2.0))
    )
    return disc.cut(bore)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "foot":
    result = build_foot()
elif target_part == "washer":
    result = build_washer()
else:
    gap = max(foot_dia * 0.4, 4.0)
    off = max(foot_dia, washer_dia) / 2.0 + gap / 2.0
    asm = cq.Assembly()
    asm.add(build_foot().translate((-off, 0, 0)), name="foot", color=cq.Color("#8a7a55"))
    asm.add(build_washer().translate((off, 0, 0)), name="washer", color=cq.Color("#a3924c"))
    result = asm
