"""
5/8" Spigot Adapter — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The light-stand spigot (a.k.a. "baby pin"): a 5/8" (16 mm) cylindrical stud that
drops into the receiver on every photographic light stand, C-stand and grip
head. This cartridge builds the two workhorse adapters — a 5/8" spigot to a
1/4-20 thread, and a 5/8" spigot to a 3/8-16 thread — plus a double-ended spigot
(a stud on each end) for stacking stands and heads.

Baby-pin / spigot standard (nominal, dimensionally real):
  - stud diameter   = 15.875 mm (5/8"), modelled at 16 mm nominal
  - locking groove  ≈ 1.5 mm deep annular groove the stand's set-screw seats in
  - the receiver end carries a real screw thread:
      1/4-20 UNC  : major 6.35 mm, pitch 1.27 mm (20 TPI)
      3/8-16 UNC  : major 9.525 mm, pitch 1.5875 mm (16 TPI)

Thread strategy — COSMETIC (fit threads): a serrated radial profile revolved
360°, so male crests trace the correct UNC major diameter. One `revolve` per
thread — fast and inherently watertight.

Watertight strategy:
  Stud, threads and body are solids of revolution / overlapping cylinders. The
  locking groove is an OPEN annular relief (revolved cut that opens to the stud
  surface, never a trapped void). A female thread socket is a THROUGH-relief
  clamped so it never breaches the far face. No tangent unions, no post-cut
  fillets on complex features.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
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


# ── UNC thread table (nominal envelopes, in mm) ──────────────────────────────
UNC = {
    "1/4-20": {"major": 6.35,  "pitch": 1.27,   "minor": 4.976},
    "3/8-16": {"major": 9.525, "pitch": 1.5875, "minor": 7.749},
}


# ── Parameters (5/8" baby-pin spigot standard) ───────────────────────────────
target_part = str(PARAM(lambda: target_part, "spigot_to_quarter"))
# "spigot_to_quarter" | "spigot_to_three_eighth" | "double_spigot"

spigot_d = float(PARAM(lambda: spigot_d, 16.0))     # 5/8" stud diameter (mm)
spigot_len = float(PARAM(lambda: spigot_len, 22.0)) # stud protrusion length (mm)
groove_depth = float(PARAM(lambda: groove_depth, 1.5))  # locking-groove depth (mm)
groove_pos = float(PARAM(lambda: groove_pos, 9.0))  # groove centre height up the stud (mm)

hub_d = float(PARAM(lambda: hub_d, 22.0))           # central hex/round hub diameter (mm)
hub_h = float(PARAM(lambda: hub_h, 12.0))           # hub height (mm)
hub_shape = str(PARAM(lambda: hub_shape, "hex"))    # "hex" | "round" wrench hub

thread_len = float(PARAM(lambda: thread_len, 10.0)) # screw stud / socket depth (mm)
thread_style = str(PARAM(lambda: thread_style, "cosmetic"))  # "cosmetic" | "smooth"
thread_form = str(PARAM(lambda: thread_form, "stud"))  # "stud" (male) | "socket" (female)

chamfer_lead = bool(PARAM(lambda: chamfer_lead, True))  # lead chamfer on stud tips

# Clamp to sane ranges so extreme UI values never crash the kernel.
spigot_d = max(10.0, min(spigot_d, 26.0))
spigot_len = max(10.0, min(spigot_len, 45.0))
groove_depth = max(0.5, min(groove_depth, min(3.0, spigot_d / 2.0 - 2.0)))
groove_pos = max(3.0, min(groove_pos, spigot_len - 3.0))
hub_d = max(spigot_d + 3.0, min(hub_d, 45.0))
hub_h = max(6.0, min(hub_h, 30.0))
thread_len = max(4.0, min(thread_len, 30.0))


# ── Hub ──────────────────────────────────────────────────────────────────────
def _hub(dia, height, shape):
    """A central hub (a wrench flat hex, or a round knurled body) centred on the
    axis, base at z=0. Edges softened for print/handling."""
    if shape == "round":
        wp = cq.Workplane("XY").circle(dia / 2.0).extrude(height)
    else:
        # Hexagon across-corners = dia. polygon() takes the circumscribed dia.
        wp = cq.Workplane("XY").polygon(6, dia).extrude(height)
    return wp


# ── Spigot stud (5/8" baby pin) ──────────────────────────────────────────────
def _spigot_stud(dia, length, z0, groove_z, groove_dp, lead):
    """A 5/8" baby-pin stud rising from z=z0 by `length`, with an annular locking
    groove the stand set-screw seats in. Built as a cylinder minus a revolved
    groove (open annular relief) — watertight. `groove_z` is measured from z0."""
    r = dia / 2.0
    stud = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(r)
        .extrude(length)
    )
    # Locking groove: a shallow V/round annular channel around the stud. Cut a
    # revolved ring that opens outward to the stud surface (vents to outside).
    gz = z0 + groove_z
    gr = r - groove_dp
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (r + 0.5, gz - 1.4),
            (gr, gz),
            (r + 0.5, gz + 1.4),
        ])
        .close()
        .revolve(360, (0, 0, 0), (0, 1, 0))
    )
    try:
        stud = stud.cut(prof)
    except Exception:
        pass
    # Lead chamfer on the free tip for easy insertion into the receiver.
    if lead:
        try:
            stud = stud.faces(">Z").edges().chamfer(min(1.4, r - 0.6))
        except Exception:
            pass
    return stud


# ── Cosmetic UNC threads ─────────────────────────────────────────────────────
def cosmetic_male(spec, length, z0, lead):
    """Male UNC thread envelope as a single solid of revolution (serrated
    profile). Base at z=z0, grows +Z. Watertight by construction."""
    major = spec["major"]
    minor = spec["minor"]
    pitch = spec["pitch"]
    r_maj = major / 2.0
    r_min = minor / 2.0
    n = max(1, int(round(length / pitch)))
    tooth = length / n
    pts = [(0.0, 0.0), (r_min, 0.0)]
    for i in range(n):
        z_lo = i * tooth
        pts.append((r_maj, z_lo + tooth * 0.5))
        pts.append((r_min, z_lo + tooth))
    pts.append((0.0, length))
    section = cq.Workplane("XZ").polyline(pts).close()
    solid = section.revolve(360, (0, 0, 0), (0, 1, 0)).translate((0, 0, z0))
    if lead:
        try:
            solid = solid.faces(">Z").edges().chamfer(min(pitch * 0.6, r_min - 0.3))
        except Exception:
            pass
    return solid


def build_male_thread(spec, length, z0, lead):
    if thread_style == "smooth":
        r = (spec["major"] + spec["minor"]) / 4.0  # pitch-ish diameter cylinder
        return (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z0))
            .circle(r)
            .extrude(length)
        )
    return cosmetic_male(spec, length, z0, lead)


def cut_female_socket(body, spec, depth, z_top, lead):
    """Bore a UNC female socket into `body` from the face at z_top, downward
    `depth`. Hole diameter = minor + a little relief (tap/screw envelope). A
    lead-in countersink eases entry. `depth` is clamped by the caller so the
    cavity never breaches the opposite face (stays watertight)."""
    hole_d = spec["minor"] + 0.2
    r = hole_d / 2.0
    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .circle(r)
        .extrude(depth + 0.02)  # nick above the face → clean boolean
    )
    body = body.cut(cavity)
    if lead:
        cs_r = r + spec["pitch"] * 0.5
        try:
            cone = (
                cq.Workplane("XY")
                .transformed(offset=cq.Vector(0, 0, z_top - spec["pitch"] * 0.9))
                .circle(r)
                .workplane(offset=spec["pitch"] * 0.9 + 0.01)
                .circle(cs_r)
                .loft(combine=True)
            )
            body = body.cut(cone)
        except Exception:
            pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def _spigot_to_thread(spec):
    """A hub with a 5/8" spigot stud below (z<0, pointing down into a stand) and
    a UNC thread ABOVE — as a male stud (`thread_form=stud`) or a female socket
    (`thread_form=socket`). The most common studio adapter shape."""
    # Hub occupies z:[0, hub_h].
    body = _hub(hub_d, hub_h, hub_shape)

    # Spigot stud below the hub, pointing DOWN. Build it upward then flip.
    stud = _spigot_stud(spigot_d, spigot_len, 0.0, groove_pos, groove_depth, chamfer_lead)
    stud = stud.rotate((0, 0, 0), (1, 0, 0), 180)  # now points -Z, base at z=0
    # Overlap the stud base into the hub bottom for a solid weld.
    stud = stud.translate((0, 0, 0.01))
    body = body.union(stud)

    # UNC interface above the hub.
    if thread_form == "socket":
        depth = min(thread_len, hub_h - 1.5)
        depth = max(3.0, depth)
        body = cut_female_socket(body, spec, depth, hub_h, chamfer_lead)
    else:
        thr = build_male_thread(spec, thread_len, hub_h - 0.01, chamfer_lead)
        body = body.union(thr)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_spigot_to_quarter():
    """5/8" spigot ↔ 1/4-20: the classic stud-to-camera-screw adapter."""
    return _spigot_to_thread(UNC["1/4-20"])


def build_spigot_to_three_eighth():
    """5/8" spigot ↔ 3/8-16: stud to the larger studio/grip thread."""
    return _spigot_to_thread(UNC["3/8-16"])


def build_double_spigot():
    """A double-ended 5/8" spigot: a hub with a baby-pin stud on BOTH ends, for
    stacking two stand receivers or a receiver and a grip head."""
    body = _hub(hub_d, hub_h, hub_shape)

    # Top stud, pointing UP from the hub top.
    top = _spigot_stud(spigot_d, spigot_len, hub_h - 0.01, groove_pos, groove_depth, chamfer_lead)
    body = body.union(top)

    # Bottom stud, pointing DOWN from the hub bottom (build up, flip, seat).
    bot = _spigot_stud(spigot_d, spigot_len, 0.0, groove_pos, groove_depth, chamfer_lead)
    bot = bot.rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 0, 0.01))
    body = body.union(bot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "spigot_to_three_eighth":
    result = build_spigot_to_three_eighth()
elif target_part == "double_spigot":
    result = build_double_spigot()
else:
    result = build_spigot_to_quarter()
