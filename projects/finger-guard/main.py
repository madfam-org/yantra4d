"""
Finger Guard & Blister Popper — Yantra4D Hyperobject Cartridge (CadQuery).

Small hand-protection and dexterity aids for the kitchen and medicine cabinet: a
blister-pack popper that presses a pill through foil without hurting the thumb, a
cut-resistant finger shield worn while chopping, and a shorter thumb guard.

  * "pill_popper" — a shaped presser with a domed nub that pushes a pill out of a
                    blister pocket, plus a comfortable barrel grip
                    (target_part == "pill_popper").
  * "finger_guard"— a curved shield that slips over a fingertip to keep a knife
                    off the nail while chopping (target_part == "finger_guard").
  * "thumb_guard" — a shorter, wider guard for the thumb
                    (target_part == "thumb_guard").

Watertight strategy: the popper is a solid barrel with a domed nub unioned on
(overlapping into the barrel so the boolean is volumetric); the guards are a
tube (finger bore) intersected with a wider shell so they wrap the finger but
leave the pad open, then trimmed to a shield — always a single manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.

Printable everyday-living AIDS, not certified medical or safety-rated PPE.
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
target_part = str(PARAM(lambda: target_part, "pill_popper"))  # pill_popper | finger_guard | thumb_guard

finger_dia = float(PARAM(lambda: finger_dia, 17.0))   # fingertip diameter (mm)
finger_len = float(PARAM(lambda: finger_len, 30.0))   # guard length over the finger (mm)
blister    = float(PARAM(lambda: blister,     9.0))   # blister pocket diameter (mm)
wall       = float(PARAM(lambda: wall,        2.4))   # shell / barrel wall
clearance  = float(PARAM(lambda: clearance,   0.6))   # finger slip clearance per side

# ── Clamps ───────────────────────────────────────────────────────────────────
finger_dia = max(10.0, min(finger_dia, 28.0))
finger_len = max(15.0, min(finger_len, 55.0))
blister    = max(4.0,  min(blister, 20.0))
wall       = max(1.6,  min(wall, 5.0))
clearance  = max(0.0,  min(clearance, 2.0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_pill_popper():
    """A barrel grip with a domed pressing nub. The nub is smaller than the
    blister pocket so it pushes the pill cleanly through the foil."""
    grip_r = 11.0
    grip_h = 42.0
    body = cq.Workplane("XY").circle(grip_r).extrude(grip_h)

    # Grip flutes (shallow, proven watertight geometry).
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=grip_r, startAngle=0, angle=360, count=14)
            .rect(0.8, 2.4)
            .extrude(grip_h + 2.0)
            .translate((0, 0, -1.0))
        )
        body = body.cut(cutter)
    except Exception:
        pass

    # Pressing nub: a domed cone at the bottom, sized under the blister pocket.
    nub_base_r = min(grip_r * 0.7, blister / 2.0 - 0.4)
    nub_base_r = max(2.0, nub_base_r)
    nub_h = nub_base_r * 1.4
    nub = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, 1.0))       # base sits inside the barrel
        .circle(nub_base_r)
        .workplane(offset=nub_h)
        .circle(nub_base_r * 0.35)
        .loft(combine=True)
        .mirror("XY")                                    # point the nub downward
        .translate((0, 0, nub_h + 1.0))
    )
    body = body.union(nub)
    # Round the top of the grip for the thumb.
    try:
        body = body.faces(">Z").edges().fillet(min(3.0, grip_r * 0.5))
    except Exception:
        pass
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def _guard(bore_dia, length, shield_frac):
    """A finger shield: an outer half-shell that wraps the top and sides of the
    finger, closed at the tip, open at the pad. Built as a capped tube with the
    lower `shield_frac` of the wall removed so the finger pad is exposed."""
    bore_r = bore_dia / 2.0 + clearance
    outer_r = bore_r + wall
    # Capped tube: outer cylinder with a domed closed tip, bored for the finger.
    tube = cq.Workplane("XY").circle(outer_r).extrude(length)
    # Domed tip cap (union a shallow cone at the top so the fingertip is covered).
    cap = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, length - 1.0))
        .circle(outer_r)
        .workplane(offset=outer_r * 0.7 + 1.0)
        .circle(max(1.0, outer_r * 0.2))
        .loft(combine=True)
    )
    body = tube.union(cap)
    # Finger bore (from the open bottom, up to just under the tip).
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(bore_r)
        .extrude(length + outer_r * 0.4)
    )
    body = body.cut(bore)
    # Open the pad side: remove the lower portion of the wall (a chord slab) so
    # the finger's underside is free and only the top/sides are shielded.
    open_h = (bore_r + outer_r) * shield_frac
    opener = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, -outer_r, -1.0))
        .box(outer_r * 3.0, open_h, length + outer_r + 2.0, centered=(True, False, False))
    )
    body = body.cut(opener)
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_finger_guard():
    """Tall narrow shield for an index/middle fingertip. Opens the pad side but
    keeps a wraparound C-shell over the top and sides of the nail."""
    return _guard(finger_dia, finger_len, shield_frac=0.72)


def build_thumb_guard():
    """Shorter, wider guard for the thumb with more wraparound coverage (smaller
    pad opening than the finger guard)."""
    return _guard(finger_dia + 4.0, finger_len * 0.7, shield_frac=0.58)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "finger_guard":
    result = build_finger_guard()
elif target_part == "thumb_guard":
    result = build_thumb_guard()
else:  # "pill_popper"
    result = build_pill_popper()
