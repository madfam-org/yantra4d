"""
1/4-20 Camera / Tripod Interface — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

The universal camera/tripod 1/4"-20 UNC screw interface — the base every camera
mount, plate, and adapter bolts onto. Generates parts carrying a 1/4-20 male boss
(the classic tripod screw / quick-plate stud), a 1/4-20 female socket (for plates
and mounts), or a 1/4-to-3/8 adapter with a socket on the bottom and a 1/4-20 or
3/8"-16 stud on top.

Thread standard (nominal envelope, dimensionally real):
  - 1/4"-20 UNC: major dia 6.35 mm (0.25"), 20 TPI -> pitch 1.27 mm,
    pitch dia ~5.524 mm, minor dia ~4.976 mm.
  - 3/8"-16 UNC: major dia 9.525 mm (0.375"), 16 TPI -> pitch 1.5875 mm,
    pitch dia ~8.491 mm, minor dia ~7.749 mm.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `target_part`).
  - Access them via PARAM(lambda: <name>, <default>) so the script also runs
    standalone / with any subset of params. Do NOT use globals()/eval/getattr —
    they are not in the sandbox's allowed builtins.
  - The final solid is assigned to a top-level name `result`.

Thread modelling is FAST by default: `thread_style="cosmetic"` builds the correct
6.35 mm (or 9.525 mm) major-diameter envelope from a handful of stacked chamfered
rings — watertight and quick. `"smooth"` emits a plain pitch-diameter cylinder/hole
for tapping or a heat-set insert. `"real"` sweeps a true helix and is clearly
slower (opt-in only).
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


# ── Thread standard table (nominal UNC envelopes, in mm) ─────────────────────
# major = crest diameter, pitch_dia = flank midline, minor = root diameter.
UNC = {
    "1/4-20": {"major": 6.35,  "pitch": 1.27,   "pitch_dia": 5.524, "minor": 4.976},
    "3/8-16": {"major": 9.525, "pitch": 1.5875, "pitch_dia": 8.491, "minor": 7.749},
}


# ── Parameters ───────────────────────────────────────────────────────────────
target_part  = str(  PARAM(lambda: target_part,  "stud"))    # "stud" | "socket" | "adapter"
thread_style = str(  PARAM(lambda: thread_style,  "cosmetic"))  # "cosmetic" | "smooth" | "real"

base_shape   = str(  PARAM(lambda: base_shape,    "disc"))    # "disc" | "square"
base_size    = float(PARAM(lambda: base_size,      25.0))     # disc dia OR square side (mm)
base_thick   = float(PARAM(lambda: base_thick,      4.0))     # base plate thickness (mm)

thread_len   = float(PARAM(lambda: thread_len,      8.0))     # stud height / socket depth (mm)
adapter_top  = str(  PARAM(lambda: adapter_top,   "3/8-16"))  # adapter top interface: "1/4-20" | "3/8-16"

chamfer_lead = bool( PARAM(lambda: chamfer_lead,   True))     # lead-in chamfer at the free thread end
ring_count   = int(  PARAM(lambda: ring_count,       10))     # cosmetic thread ring detail (higher = finer, slower)

# Clamp to sane ranges so extreme UI values never crash the kernel.
base_size  = max(8.0, min(base_size, 120.0))
base_thick = max(1.5, min(base_thick, 40.0))
thread_len = max(3.0, min(thread_len, 40.0))
ring_count = max(3,   min(ring_count, 40))


# ── Base geometry ────────────────────────────────────────────────────────────
def base_plate(size, thick, shape):
    """A mounting base centered in X/Y with its bottom face on z=0.
    `disc` -> cylinder of diameter `size`; `square` -> box of side `size`,
    with softened vertical edges for a printable, handle-friendly plate."""
    if shape == "square":
        wp = cq.Workplane("XY").box(size, size, thick, centered=(True, True, False))
        r = min(size * 0.12, 4.0)
        if r > 0.4:
            try:
                wp = wp.edges("|Z").fillet(r)
            except Exception:
                pass
    else:
        wp = cq.Workplane("XY").circle(size / 2.0).extrude(thick)
    return wp


# ── Thread envelopes ─────────────────────────────────────────────────────────
def cosmetic_male(spec, length, z0, lead):
    """Male thread envelope as a single solid of revolution. A serrated (sawtooth)
    radial profile — root -> crest -> root each pitch — is revolved 360°, so the
    crests trace the correct 6.35/9.525 mm nominal major diameter while the roots
    sit at the minor diameter. One `revolve` (no per-ring booleans) keeps it fast
    and inherently watertight. Base sits at z=z0, grows +Z. `ring_count` caps the
    tooth count for render speed on long studs."""
    major = spec["major"]
    minor = spec["minor"]
    pitch = spec["pitch"]
    r_maj = major / 2.0
    r_min = minor / 2.0

    # One tooth per pitch, capped by ring_count so long studs stay quick.
    turns = max(1, int(round(length / pitch)))
    n = min(turns, ring_count)
    tooth_h = length / n

    # Build the half-section outline (a closed loop in the XZ half-plane, x>=0),
    # revolved about Z. Walk up the crest edge as a sawtooth, return down the axis.
    pts = [(0.0, 0.0), (r_min, 0.0)]
    for i in range(n):
        z_lo = i * tooth_h
        z_mid = z_lo + tooth_h * 0.5
        z_hi = z_lo + tooth_h
        pts.append((r_maj, z_mid))     # crest at mid-tooth -> major diameter
        pts.append((r_min, z_hi))      # back to root at the tooth boundary
    pts.append((0.0, length))          # close across the top to the axis

    section = cq.Workplane("XZ").polyline(pts).close()
    solid = section.revolve(360, (0, 0, 0), (0, 1, 0))
    solid = solid.translate((0, 0, z0))

    # Lead-in chamfer at the free (top) end for easy thread start.
    if lead:
        try:
            solid = solid.faces(">Z").edges().chamfer(min(pitch * 0.6, r_min - 0.3))
        except Exception:
            pass
    return solid


def smooth_male(spec, length, z0):
    """Plain pitch-diameter stud for tapping / heat-set — a clean cylinder."""
    r = spec["pitch_dia"] / 2.0
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(r)
        .extrude(length)
    )


def real_male(spec, length, z0, lead):
    """True swept UNC helix (opt-in, slower). A 60° triangular thread profile is
    swept along a helix and unioned onto a minor-diameter core so the result is a
    watertight solid at the correct major diameter."""
    major = spec["major"]
    minor = spec["minor"]
    pitch = spec["pitch"]
    r_min = minor / 2.0
    depth = (major - minor) / 2.0

    core = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z0))
        .circle(r_min + 0.05)
        .extrude(length)
    )

    helix = cq.Wire.makeHelix(pitch=pitch, height=length, radius=r_min, lefthand=False)
    # 60° triangular tooth in the plane normal to the helix start tangent.
    half = pitch / 2.0
    profile = (
        cq.Workplane("XZ")
        .polyline([(r_min, 0), (r_min + depth, half * 0.5), (r_min, half)])
        .close()
    )
    try:
        threads = profile.sweep(cq.Workplane(obj=helix), isFrenet=True)
        solid = core.union(threads.translate((0, 0, z0)))
    except Exception:
        # Fall back to the fast cosmetic envelope if the sweep kernel struggles.
        return cosmetic_male(spec, length, z0, lead)

    if lead:
        try:
            solid = solid.faces(">Z").edges().chamfer(min(pitch * 0.6, r_min - 0.3))
        except Exception:
            pass
    return solid


def build_male(spec, length, z0, lead):
    if thread_style == "smooth":
        return smooth_male(spec, length, z0)
    if thread_style == "real":
        return real_male(spec, length, z0, lead)
    return cosmetic_male(spec, length, z0, lead)


def cut_female(body, spec, depth, z_top, lead):
    """Subtract a 1/4-20 (or 3/8-16) socket into `body` from the face at z_top,
    going downward `depth`. The cut hole diameter matches the thread style:
      - cosmetic: minor-ish tapping envelope with relief so a tap/screw engages
      - smooth:   pitch diameter (clean tap / heat-set)
      - real:     minor diameter (a real screw's threads bite the wall)
    A lead-in countersink at the mouth eases screw entry. Body stays watertight
    because the cavity never breaches the opposite face (depth is clamped)."""
    if thread_style == "smooth":
        hole_d = spec["pitch_dia"]
    else:
        hole_d = spec["minor"] + 0.15  # tapping / clearance-ish envelope
    r = hole_d / 2.0

    cavity = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .circle(r)
        .extrude(depth + 0.01)  # nick above the face for a clean boolean
    )
    body = body.cut(cavity)

    if lead:
        cs_r = r + spec["pitch"] * 0.5
        cone = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z_top - spec["pitch"] * 0.9))
            .circle(r)
            .workplane(offset=spec["pitch"] * 0.9 + 0.01)
            .circle(cs_r)
            .loft(combine=True)
        )
        try:
            body = body.cut(cone)
        except Exception:
            pass
    return body


# ── Part builders ────────────────────────────────────────────────────────────
def build_stud():
    """Classic tripod stud / quick-plate screw: a 1/4-20 male boss standing on a
    mounting base disc or plate."""
    base = base_plate(base_size, base_thick, base_shape)
    stud = build_male(UNC["1/4-20"], thread_len, base_thick, chamfer_lead)
    return base.union(stud)


def build_socket():
    """A plate / block carrying a 1/4-20 female socket — the receiver for camera
    mounts, plates, and adapters. Socket depth = thread_len, clamped so the base
    never perforates."""
    base = base_plate(base_size, base_thick, base_shape)
    depth = min(thread_len, base_thick - 1.0)
    depth = max(2.5, depth)
    return cut_female(base, UNC["1/4-20"], depth, base_thick, chamfer_lead)


def build_adapter():
    """The ubiquitous 1/4-to-3/8 tripod adapter: a short body with a 1/4-20 female
    socket in the BOTTOM face and a stud (1/4-20 or 3/8-16, selectable) on TOP."""
    body_h = base_thick
    body = base_plate(base_size, body_h, base_shape)

    # Bottom socket: 1/4-20, cut upward from the bottom face (z=0).
    sock_depth = min(thread_len, body_h - 1.5)
    sock_depth = max(2.5, sock_depth)
    sock = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.01))
        .circle((UNC["1/4-20"]["minor"] + 0.15) / 2.0)
        .extrude(sock_depth + 0.01)
    )
    body = body.cut(sock)
    if chamfer_lead:
        p = UNC["1/4-20"]["pitch"]
        cone = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, -0.01))
            .circle((UNC["1/4-20"]["minor"] + 0.15) / 2.0 + p * 0.5)
            .workplane(offset=p * 0.9)
            .circle((UNC["1/4-20"]["minor"] + 0.15) / 2.0)
            .loft(combine=True)
        )
        try:
            body = body.cut(cone)
        except Exception:
            pass

    # Top stud: selectable interface.
    top_key = adapter_top if adapter_top in UNC else "3/8-16"
    stud = build_male(UNC[top_key], thread_len, body_h, chamfer_lead)
    return body.union(stud)


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "socket":
    result = build_socket()
elif target_part == "adapter":
    result = build_adapter()
else:
    result = build_stud()
