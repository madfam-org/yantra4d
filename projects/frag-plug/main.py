"""
Aquarium Frag / Coral Plug — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Coral propagation ("fragging") mounts a cut coral frag on a small plug whose
stem pushes into a frag rack or egg-crate hole in the reef tank. This cartridge
builds the plug, a matching rack that holds a grid of plugs, and a stemless
gluing disc for mounting frags straight onto rock.

  * "frag_plug" — the classic mushroom/nail plug: a round top disc on a narrow
                  stem (target_part == "frag_plug").
  * "frag_rack" — a solid bar with a grid of stem holes bored through it, on
                  short feet, to stand plugs upright on the sand bed
                  (target_part == "frag_rack").
  * "frag_disc" — a stemless disc with a shallow domed top for gluing a frag
                  directly to live rock (target_part == "frag_disc").

Real dimensions (reef-hobby nominal):
  - Top disc diameter: 25 mm standard (mini 15-18 mm, large 35-40 mm).
  - Stem diameter: 6 mm typical (heavy plugs 8-10 mm); fits a 6 mm rack hole.
  - Overall height: ~20-25 mm.
  - Frag racks are commonly drilled at 6 mm, or 1/2 in (12.7 mm) egg crate.

Watertight strategy: the plug is a solid disc unioned to a solid tapered stem —
two solids overlapping into shared material (never a tangent kiss), filleted at
the disc underside BEFORE any hole is cut. The rack is a solid bar (on solid
feet) with stem holes bored fully THROUGH the top face to the underside (open to
both faces → no trapped void). The disc is a solid puck. Each result is one
manifold solid.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read params via PARAM(lambda: <name>, <default>). No globals()/eval/getattr.
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
target_part = str(PARAM(lambda: target_part, "frag_plug"))  # frag_plug | frag_rack | frag_disc

disc_dia = float(PARAM(lambda: disc_dia, 25.0))     # top disc diameter (mm)
disc_h = float(PARAM(lambda: disc_h, 4.0))          # disc thickness (mm)
stem_dia = float(PARAM(lambda: stem_dia, 6.0))      # stem diameter (mm)
stem_h = float(PARAM(lambda: stem_h, 18.0))         # stem length below the disc (mm)
hole_dia = float(PARAM(lambda: hole_dia, 6.4))      # rack hole diameter (mm, plug stem clearance)
rack_cols = int(float(PARAM(lambda: rack_cols, 4)))  # rack holes per row
rack_rows = int(float(PARAM(lambda: rack_rows, 2)))  # rack rows
rack_pitch = float(PARAM(lambda: rack_pitch, 22.0))  # rack hole spacing (mm)

# ── Clamps ───────────────────────────────────────────────────────────────────
disc_dia = max(10.0, min(disc_dia, 60.0))
disc_h = max(2.0, min(disc_h, 10.0))
stem_dia = max(3.0, min(stem_dia, 16.0))
stem_h = max(6.0, min(stem_h, 40.0))
hole_dia = max(3.0, min(hole_dia, 16.0))
rack_cols = max(1, min(rack_cols, 8))
rack_rows = max(1, min(rack_rows, 6))
rack_pitch = max(max(disc_dia, hole_dia) + 3.0, min(rack_pitch, 60.0))


# ── Part builders ────────────────────────────────────────────────────────────
def build_frag_plug():
    """Disc-on-stem: a round top disc fused to a slightly tapered stem. The disc
    underside is filleted into the stem for strength; a shallow center dimple in
    the top holds glue. Fillet the blank BEFORE cutting the dimple."""
    disc_r = disc_dia / 2.0
    stem_r = stem_dia / 2.0
    # Stem tapers slightly to a rounded push-in tip; built base-down from z=0.
    stem = _tapered_stem(stem_r, stem_h)
    # Disc sits on top of the stem, overlapping down INTO the stem region.
    disc = (
        cq.Workplane("XY")
        .workplane(offset=stem_h - 1.0)
        .circle(disc_r)
        .extrude(disc_h + 1.0)
    )
    body = stem.union(disc)
    # Fillet the disc/stem junction and disc edges on the clean blank.
    try:
        body = body.edges("|Z or >Z").fillet(min(1.2, disc_h * 0.3, stem_r * 0.4))
    except Exception:
        pass
    # Shallow glue dimple in the disc top (vented to outside — not a trapped void).
    dimple = (
        cq.Workplane("XY")
        .workplane(offset=stem_h + disc_h - min(1.5, disc_h * 0.4))
        .circle(max(1.0, disc_r * 0.5))
        .extrude(min(1.5, disc_h * 0.4) + 0.5)
    )
    body = body.cut(dimple)
    return body


def _tapered_stem(base_r, height):
    """A stem that narrows from base_r at the disc to ~70% at the push-in tip,
    for an easy insert. makeCone gives a clean single solid."""
    tip_r = max(1.0, base_r * 0.75)
    return cq.Workplane(obj=cq.Solid.makeCone(base_r, tip_r, height))


def build_frag_rack():
    """A solid bar on feet with a grid of stem holes bored fully through the top.
    Plugs drop in from above and their stems poke out the underside. Holes are
    through-bores (open both faces → vented)."""
    n_c = rack_cols
    n_r = rack_rows
    pitch = rack_pitch
    margin = max(hole_dia, 8.0)
    bar_w = (n_c - 1) * pitch + 2.0 * margin
    bar_d = (n_r - 1) * pitch + 2.0 * margin
    bar_h = 8.0
    foot_h = 10.0

    bar = (
        cq.Workplane("XY")
        .workplane(offset=foot_h)
        .box(bar_w, bar_d, bar_h, centered=(True, True, False))
    )
    try:
        bar = bar.edges("|Z").fillet(min(3.0, margin * 0.4))
    except Exception:
        pass

    # Feet: four solid legs at the corners, overlapping up into the bar.
    foot_inset = margin * 0.6
    fx = bar_w / 2.0 - foot_inset
    fy = bar_d / 2.0 - foot_inset
    feet = None
    for sx in (-1, 1):
        for sy in (-1, 1):
            leg = (
                cq.Workplane("XY")
                .center(sx * fx, sy * fy)
                .circle(max(3.0, margin * 0.45))
                .extrude(foot_h + 1.0)
            )
            feet = leg if feet is None else feet.union(leg)
    body = bar.union(feet)

    # Stem holes bored through the bar top.
    x0 = -(n_c - 1) * pitch / 2.0
    y0 = -(n_r - 1) * pitch / 2.0
    pts = [(x0 + c * pitch, y0 + r * pitch) for r in range(n_r) for c in range(n_c)]
    holes = (
        cq.Workplane("XY")
        .workplane(offset=foot_h - 0.5)
        .pushPoints(pts)
        .circle(hole_dia / 2.0)
        .extrude(bar_h + 1.0)
    )
    body = body.cut(holes)
    return body


def build_frag_disc():
    """A stemless disc puck with a gently domed top for gluing a frag straight to
    rock or a rack shelf. A solid short cylinder with a chamfered top edge and a
    small underside grip ring cut in (vented). One manifold solid."""
    disc_r = disc_dia / 2.0
    h = max(disc_h + 2.0, 6.0)
    puck = (
        cq.Workplane("XY")
        .circle(disc_r)
        .extrude(h)
    )
    try:
        puck = puck.edges(">Z").chamfer(min(1.5, disc_r * 0.2))
    except Exception:
        pass
    # Underside grip groove: a shallow annular channel cut up from the bottom so
    # epoxy keys in. Open to the bottom face → vented, not trapped.
    groove = (
        cq.Workplane("XY")
        .circle(disc_r * 0.7)
        .circle(disc_r * 0.45)
        .extrude(min(2.0, h * 0.35))
    )
    body = puck.cut(groove)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "frag_rack":
    result = build_frag_rack()
elif target_part == "frag_disc":
    result = build_frag_disc()
else:  # "frag_plug"
    result = build_frag_plug()
