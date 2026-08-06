"""
Parametric Vase — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A generative vase whose silhouette is a polar radius function sampled to a closed
polyline and extruded, optionally twisting as it rises. Pick a profile family — round,
faceted (N-gon), lobed/twisted, or superformula — and dial base diameter, height, wall,
twist, and lobe count. The result is a hollow vessel with a closed floor.

Three parts (dispatched via `target_part`):
  * "vase"         — the base vessel using the chosen `profile` family (no forced twist).
  * "twisted_vase" — the profile spun about Z as it rises (a spiral vase); great in vase mode.
  * "faceted_vase" — a crisp low-count N-gon prism vessel (facets read as flat panels).

The profile is built as a polar function r(θ) sampled to a closed polyline; the wall is a
second, inward-offset profile cut from the top down, leaving a solid floor. Twist is
applied with CadQuery's `twistExtrude` so the whole shell rotates coherently (watertight).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `base_dia`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import math

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
target_part = str(PARAM(lambda: target_part, "vase"))     # vase|twisted_vase|faceted_vase
profile     = str(PARAM(lambda: profile,     "round"))    # round|faceted|twisted|superformula

base_dia = float(PARAM(lambda: base_dia, 90.0))    # base outer diameter (mm)
height   = float(PARAM(lambda: height,  150.0))    # vase height (mm)
wall     = float(PARAM(lambda: wall,      3.0))    # wall thickness (mm)
twist    = float(PARAM(lambda: twist,    60.0))    # total twist over the height (deg)
lobes    = int(  PARAM(lambda: lobes,       6))    # lobe / facet count
lobe_amp = float(PARAM(lambda: lobe_amp,  0.14))   # lobe amplitude (fraction of radius)
floor_t  = float(PARAM(lambda: floor_t,   4.0))    # closed floor thickness (mm)

# Clamp inputs to sane ranges so extreme UI values still build watertight.
base_dia = max(40.0, min(base_dia, 220.0))
height   = max(50.0, min(height, 320.0))
wall     = max(1.6, min(wall, 8.0))
twist    = max(0.0, min(twist, 360.0))
lobes    = max(3, min(lobes, 16))
lobe_amp = max(0.0, min(lobe_amp, 0.4))
floor_t  = max(1.6, min(floor_t, 12.0))

base_r = base_dia / 2.0
# Keep the wall from consuming the whole radius.
wall = min(wall, base_r * 0.4)


# ── Polar profile families (r as a function of angle) ────────────────────────
def _superformula_r(a, m, n1, n2, n3, scale):
    """Gielis superformula radius. Guarded against div-by-zero; returns a smooth closed
    curve for the given symmetry `m`."""
    t1 = abs(math.cos(m * a / 4.0)) ** n2
    t2 = abs(math.sin(m * a / 4.0)) ** n3
    denom = (t1 + t2)
    if denom < 1e-9:
        denom = 1e-9
    r = (denom) ** (-1.0 / n1)
    return scale * r


def _radius(a, r0, fam):
    """r(θ) for the chosen family at nominal radius r0."""
    if fam == "faceted":
        # Regular N-gon: radius to the polygon edge for a straight-panel facet.
        half = math.pi / lobes
        # angle within one facet sector
        local = ((a + half) % (2.0 * half)) - half
        return r0 * math.cos(half) / max(1e-6, math.cos(local))
    if fam == "superformula":
        base = _superformula_r(a, lobes, 1.0, 1.7, 1.7, 1.0)
        # normalise so the mean radius ≈ r0
        return r0 * base
    # round / twisted share a smooth lobed profile (twist is applied at extrude time)
    return r0 * (1.0 + lobe_amp * math.cos(lobes * a))


def _profile_wire(r0, fam, n):
    """A closed polyline wire sampled from r(θ)."""
    pts = []
    for i in range(n):
        a = 2.0 * math.pi * i / n
        r = max(2.0, _radius(a, r0, fam))
        pts.append((r * math.cos(a), r * math.sin(a)))
    return cq.Workplane("XY").polyline(pts).close()


def _sample_count(fam):
    if fam == "faceted":
        return lobes            # exact N-gon vertices
    if fam == "superformula":
        return 180
    return 160


# ── Vessel builder ────────────────────────────────────────────────────────────
def _annular_wp(wp, r0, fam, n, rot):
    """Push an OUTER wire and an inward-offset INNER wire (both rotated by `rot`) onto
    `wp`. An extrude/loft over this annular cross-section makes the wall shell directly —
    boolean-free, far cheaper than cutting two solid prisms."""
    outer = []
    inner = []
    ri = r0 - wall
    for k in range(n):
        a = 2.0 * math.pi * k / n
        ro = max(2.0, _radius(a - rot, r0, fam))
        rin = _radius(a - rot, ri, fam)
        rin = min(rin, ro - max(1.2, wall * 0.5))   # keep inner strictly inside outer
        rin = max(1.0, rin)
        outer.append((ro * math.cos(a), ro * math.sin(a)))
        inner.append((rin * math.cos(a), rin * math.sin(a)))
    return wp.polyline(outer).close().polyline(inner).close()


def _build_vessel(fam, do_twist):
    """Build a hollow vessel with a closed floor and NO expensive cut between two lofted
    prisms. For a straight vessel, extrude one annular cross-section. For a twisted
    vessel, LOFT through a few rotated annular sections (twistExtrude is far too slow in
    OCC). The floor is a short full-profile disk fused on (a cheap boolean)."""
    tw = twist if do_twist else 0.0
    twisting = abs(tw) > 0.5 and fam != "faceted"
    # Twisted lofts multiply cost by the level count, so sample the profile more coarsely.
    n = min(_sample_count(fam), 72) if twisting else _sample_count(fam)
    if twisting:
        levels = 6
        wp = cq.Workplane("XY")
        for k in range(levels):
            dz = (height / (levels - 1)) if k > 0 else 0.0
            rot = math.radians(tw) * k / (levels - 1)
            wp = _annular_wp(wp.workplane(offset=dz), base_r, fam, n, rot)
        walls = wp.loft(combine=True, ruled=True)
    else:
        walls = _annular_wp(cq.Workplane("XY"), base_r, fam, n, 0.0).extrude(height)
    floor = _profile_wire(base_r, fam, n).extrude(floor_t)
    return walls.union(floor)


# ── Part builders ─────────────────────────────────────────────────────────────
def build_vase():
    """The chosen profile family, twisting only if the profile itself is 'twisted'."""
    fam = profile
    do_twist = (profile == "twisted")
    return _build_vessel(fam, do_twist)


def build_twisted_vase():
    """A spiral vessel: the lobed profile spun about Z as it rises (forces twist on)."""
    fam = "superformula" if profile == "superformula" else "round"
    return _build_vessel(fam, do_twist=True)


def build_faceted_vase():
    """A crisp N-gon prism vessel — flat panels, no twist."""
    return _build_vessel("faceted", do_twist=False)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "twisted_vase":
    result = build_twisted_vase()
elif target_part == "faceted_vase":
    result = build_faceted_vase()
else:
    result = build_vase()
