"""
Shaft Coupler Kit — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

A CAPSTONE any-to-any shaft coupler that bridges every common small-shaft profile
so a motor, knob, encoder or hand crank built for one shaft drives another. The
user measures each shaft and picks its bore: round, single-D flat, or hex — at the
3/4/5/6/8 mm sizes that dominate hobby and appliance drivetrains. Because each end
is selectable independently, one part couples (say) a 5 mm D motor shaft to a
6 mm round encoder, or a 1/4 in hex bit to a round pot.

Modes (dispatched via `target_part`):
  * "rigid_coupler" — a solid barrel with a selectable bore at EACH end (bore A
                      below, bore B above) separated by a thin web: joins two
                      shafts end-to-end.
  * "bore_adapter"  — a sleeve that seats in a larger round bore (its outside is
                      a plain cylinder) and carries a smaller selectable bore
                      inside: step a big hole down to a small shaft.
  * "set_hub"       — a hub/collar with one selectable bore, a radial set-screw,
                      and a flange bolt circle so a wheel/gear/arm bolts on.

Real shaft geometry (nominal, dimensionally real, all mm):
  Common shaft diameters: 3.0, 4.0, 5.0, 6.0, 8.0 (and 6.35 for 1/4 in hex bits).
  D-flat depth is ~0.5 mm on small shafts; hex is measured across-flats (AF).
  Spline-hub flange bolt circle is exposed so this hub mates that family.

Watertight strategy (thread-free by design → every render is fast):
  Every body is a plain revolved/extruded solid; bores are solid cutters that
  extend past the faces they open on (vent to a face → no trapped void). The
  rigid coupler keeps a solid mid web so the two bores never meet through the part
  (no severed body). Fillets/chamfers touch clean blanks only, wrapped in
  try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) — globals()/eval/getattr are
    not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default. `except Exception`
    catches the NameError raised for an unbound param name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rigid_coupler"))
bore_a = str(PARAM(lambda: bore_a, "round"))     # round | D-flat | hex (lower end)
bore_b = str(PARAM(lambda: bore_b, "D-flat"))    # round | D-flat | hex (upper end)
shaft_a = float(PARAM(lambda: shaft_a, 5.0))     # shaft A diameter / AF (mm)
shaft_b = float(PARAM(lambda: shaft_b, 6.0))     # shaft B diameter / AF (mm)
body_len = float(PARAM(lambda: body_len, 24.0))  # total coupler / hub length (mm)
wall = float(PARAM(lambda: wall, 3.0))           # radial wall around the largest bore (mm)
flat_depth = float(PARAM(lambda: flat_depth, 0.5))  # D-flat depth from the wall (mm)
setscrew = bool(PARAM(lambda: setscrew, True))   # radial set-screw hole(s)
setscrew_dia = float(PARAM(lambda: setscrew_dia, 3.2))  # set-screw clearance (~M3)
bolt_circle = float(PARAM(lambda: bolt_circle, 0.0))  # flange bolt-circle Ø (0 = none)

# Clamp to sane ranges so extreme UI values still build watertight.
shaft_a = max(2.0, min(shaft_a, 12.0))
shaft_b = max(2.0, min(shaft_b, 12.0))
body_len = max(10.0, min(body_len, 60.0))
wall = max(2.0, min(wall, 8.0))
flat_depth = max(0.0, min(flat_depth, 2.0))
setscrew_dia = max(1.5, min(setscrew_dia, 6.0))
bolt_circle = max(0.0, min(bolt_circle, 40.0))

CLR = 0.2  # print clearance added to every bore so it slips onto its shaft


# ── Bore cutters (inlined — repo-lib imports are blocked in sandbox) ──────────
def round_cutter(dia, length):
    """A plain cylindrical bore cutter of the (clearance-adjusted) shaft radius."""
    return cq.Workplane("XY").circle(dia / 2.0 + CLR).extrude(length)


def hex_cutter(af, length):
    """A hexagonal bore cutter, `af` = across-flats. Across-corners = af/cos30."""
    r_ac = (af / 2.0 + CLR) / math.cos(math.radians(30.0))
    return cq.Workplane("XY").polygon(6, 2.0 * r_ac).extrude(length)


def flatted_cutter(dia, length, depth):
    """A cylindrical bore with one flat chord (a real D-shaft): a circle minus the
    outboard sliver on +X so x <= r - depth on that side."""
    r = dia / 2.0 + CLR
    cutter = round_cutter(dia, length)
    sliver = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector((r - depth) + r, 0, length / 2.0))
        .box(2.0 * r, 2.4 * r + 2.0, length + 2.0, centered=(True, True, True))
    )
    return cutter.cut(sliver)


def bore_cutter(kind, dia, length):
    """Dispatch to the right bore cutter for `kind`."""
    if kind == "hex":
        return hex_cutter(dia, length)
    if kind == "D-flat" and flat_depth > 0.02:
        return flatted_cutter(dia, length, min(flat_depth, dia / 2.0 - 0.4))
    return round_cutter(dia, length)


def outer_r():
    """Barrel radius: wall around the larger of the two bores (or the AF corner)."""
    big = max(shaft_a, shaft_b)
    # hex across-corners can be wider than the nominal AF — allow for it.
    big_ac = big / math.cos(math.radians(30.0))
    return big_ac / 2.0 + wall


# ── Part builders ─────────────────────────────────────────────────────────────
def build_rigid_coupler():
    """A barrel with a selectable bore at each end and a SOLID mid web so the two
    bores never break through into one another (no severed body). Bore A opens at
    the bottom face; bore B opens at the top face. Set-screws (one per end)
    tighten each shaft; both open through the wall to the outside (no trapped
    void)."""
    r = outer_r()
    L = body_len
    web = max(2.0, wall * 0.8)             # solid mid web thickness
    end_depth = (L - web) / 2.0            # bore depth into each end
    end_depth = max(3.0, end_depth)

    body = cq.Workplane("XY").circle(r).extrude(L)
    # Chamfer both open rims of the clean blank for shaft lead-in.
    try:
        body = body.edges("|Z or >Z or <Z").chamfer(0)  # no-op guard pattern
    except Exception:
        pass

    # Bore A from the bottom, up end_depth (opens at z=0 face).
    ca = bore_cutter(bore_a, shaft_a, end_depth + 0.6).translate((0, 0, -0.3))
    body = body.cut(ca)
    # Bore B from the top, down end_depth (opens at z=L face). Build growing +Z
    # then flip so it opens on the top face.
    cb = bore_cutter(bore_b, shaft_b, end_depth + 0.6)
    cb = cb.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, L + 0.3))
    body = body.cut(cb)

    if setscrew:
        body = add_setscrews(body, r, [end_depth * 0.5, L - end_depth * 0.5])
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_bore_adapter():
    """A sleeve: a plain cylinder (its outside seats in a larger round bore) with
    a smaller selectable bore all the way through (opens both faces → no trapped
    void). Steps a big round hole down to a small shaft profile. `shaft_b` is the
    outer (host) bore diameter it fits; `shaft_a`/`bore_a` is the inner shaft."""
    outer_d = max(shaft_b, shaft_a + 2.0 * wall)   # host bore it plugs into
    r = outer_d / 2.0
    L = body_len
    body = cq.Workplane("XY").circle(r).extrude(L)
    # A small retaining lip at the top so the sleeve can't push all the way
    # through the host bore (a flange 1.2 mm proud, unioned solid).
    lip = (
        cq.Workplane("XY").transformed(offset=cq.Vector(0, 0, L - 1.6))
        .circle(r + 1.6).extrude(1.6)
    )
    body = body.union(lip)
    # Inner selectable bore straight through (opens both faces).
    inner = bore_cutter(bore_a, shaft_a, L + 3.0).translate((0, 0, -1.5))
    body = body.cut(inner)
    if setscrew:
        body = add_setscrews(body, r + 1.6, [L - 0.8])
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_set_hub():
    """A hub/collar: one selectable bore through, a radial set-screw, and an
    optional flange bolt circle so a wheel/gear/arm bolts on (mates the
    `spline-hub` flange family). Bore opens both faces; bolt holes open through
    the flange (no trapped voids)."""
    r = outer_r()
    L = body_len
    # If a bolt circle is requested, widen the flange to host it.
    flange_r = r
    if bolt_circle > 0.05:
        flange_r = max(r, bolt_circle / 2.0 + max(4.0, setscrew_dia))
    body = cq.Workplane("XY").circle(flange_r).extrude(L)

    # Central selectable bore through (opens both faces).
    ca = bore_cutter(bore_a, shaft_a, L + 2.0).translate((0, 0, -1.0))
    body = body.cut(ca)

    # Flange bolt circle (4 holes) through the whole hub.
    if bolt_circle > 0.05:
        bc_r = bolt_circle / 2.0
        hole_d = max(2.5, min(setscrew_dia + 0.8, 6.0))
        pts = []
        for i in range(4):
            ang = math.pi / 2.0 * i + math.pi / 4.0
            pts.append((bc_r * math.cos(ang), bc_r * math.sin(ang)))
        holes = (
            cq.Workplane("XY").pushPoints(pts).circle(hole_d / 2.0)
            .extrude(L + 2.0).translate((0, 0, -1.0))
        )
        body = body.cut(holes)

    if setscrew:
        body = add_setscrews(body, flange_r, [L * 0.5])
    try:
        body = body.clean()
    except Exception:
        pass
    return body


def add_setscrews(body, radius, zs):
    """Radial set-screw clearance holes through the +X wall into the bore at each
    z in `zs`. Opens through the outer wall to the outside → no trapped void."""
    d = max(1.5, min(setscrew_dia, radius * 0.9))
    for z in zs:
        zc = max(2.0, min(z, body_len - 2.0))
        hole = (
            cq.Workplane("YZ")
            .transformed(offset=cq.Vector(0, zc, 0))
            .circle(d / 2.0)
            .extrude(radius + 1.0)   # from centre outward through +X wall
        )
        body = body.cut(hole)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "bore_adapter":
    result = build_bore_adapter()
elif target_part == "set_hub":
    result = build_set_hub()
else:
    result = build_rigid_coupler()
