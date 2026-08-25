import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
# globals()/eval/NameError are NOT reliable in-sandbox; read every param via PARAM.
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "nosepiece")
thread_standard = str(PARAM(lambda: thread_standard, "RMS"))
port_count = int(PARAM(lambda: port_count, 4))
clearance = float(PARAM(lambda: clearance, 0.25))
pivot_bore = float(PARAM(lambda: pivot_bore, 6.0))
turret_thick = float(PARAM(lambda: turret_thick, 12.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# RMS (Royal Microscopical Society) objective thread: W 0.800 in x 36 TPI,
#   major Ø 20.32 mm, pitch 25.4/36 = 0.7056 mm (DIN 58888 / ISO 8038 / BS 7012).
#   Shared with the `objective-case` cartridge so objectives interchange.
# M25 x 0.75 objective thread (newer standard): major Ø 25.0 mm, pitch 0.75 mm.
THREAD_SPECS = {
    "RMS": {"major_d": 20.32, "pitch": 0.7056},
    "M25": {"major_d": 25.0, "pitch": 0.75},
}
# Fixed thread engagement (half-integer turns → well-conditioned helical sweep).
THREAD_TURNS = 3.5


def _spec(name):
    return THREAD_SPECS.get(str(name).strip().upper(), THREAD_SPECS["RMS"])


def _fillet_safe(wp, edges_selector, radius):
    """Fillet the blank BEFORE cutting features; fall back gracefully."""
    try:
        return wp.edges(edges_selector).fillet(radius)
    except Exception:
        return wp


# ── Thread primitives (inlined — imports of repo libs are blocked in sandbox) ─
def _helix_path(pitch, height):
    """A helical wire centered on Z. Radius ~0 so the swept profile (already at
    the target radius in its own plane) traces the true helix."""
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal (female) helical rib fused into a bore wall. Root radius =
    bore_r + overlap so the rib bites into the wall (clean, watertight union);
    crest points INWARD to bore_r - thr_depth to grab the male objective."""
    root_r = bore_r + overlap
    crest_r = max(0.5, bore_r - thr_depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h), isFrenet=True)
    return rib.translate((0, 0, pitch * 0.5))


def male_thread(shaft_r, pitch, thread_h, thr_depth, overlap):
    """External (male) helical rib fused onto a shaft. Root bites in by overlap;
    crest sticks OUT to shaft_r + thr_depth."""
    root_r = max(0.5, shaft_r - overlap)
    crest_r = shaft_r + thr_depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -pitch * 0.32),
            (crest_r, -pitch * 0.14),
            (crest_r, pitch * 0.14),
            (root_r, pitch * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(pitch, thread_h), isFrenet=True)
    return rib.translate((0, 0, pitch * 0.5))


def _thread_geometry(name):
    """Common derived thread numbers for the selected standard.

    Thread ENGAGEMENT is fixed at a half-integer number of turns (see THREAD_TURNS).
    An integer turn count degenerates the helical sweep — the profile closes on
    itself and OCCT flips the solid's orientation, yielding a negative-volume /
    null boolean. A half-integer count keeps the rib's ends open and non-coincident
    so it always fuses cleanly into the wall, and keeps the fine-pitch boolean fast.
    The true pitch and major diameter are preserved for real thread compatibility.
    """
    g = _spec(name)
    pitch = g["pitch"]
    turns = THREAD_TURNS
    thr_major = g["major_d"] + 2.0 * clearance     # female bore = major + clearance/side
    bore_r = thr_major / 2.0
    thr_depth = 0.55 * pitch
    overlap = 0.45
    thread_h = pitch * turns
    return pitch, bore_r, thr_depth, overlap, thread_h, thr_major


def _knurl(solid, outer_d, height, teeth=32, depth=0.6):
    """Shallow vertical grip flutes as one polar-array boolean (cheap, watertight)."""
    r = outer_d / 2.0
    try:
        cutter = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(depth, depth * 3.0)
            .extrude(height + 2.0)
            .translate((0, 0, -1.0))
        )
        solid = solid.cut(cutter)
    except Exception:
        pass  # knurl is cosmetic — never fatal
    return solid


def _port_ring_radius(thr_major, n):
    """Pitch radius of the objective-port ring: pack N bores of the given major
    diameter around the disc with a comfortable gap between neighbouring bores."""
    wall_between = 4.0
    seg = thr_major + wall_between
    import math
    # chord = 2 R sin(pi/n) must clear one bore + wall
    if n <= 1:
        return 0.0
    return max(seg, seg / (2.0 * math.sin(math.pi / n)))


# ─── Mode 1: rotating 4-objective nosepiece (turret disc) ─────────────────────
def build_nosepiece():
    """A rotating nosepiece disc carrying N female-threaded objective ports around
    a central pivot bore. Each port is a female RMS/M25 thread (fused helical rib)
    that opens through the disc, so an objective screws into any port exactly as on
    a factory turret. The central pivot bore opens through both faces (a through
    hole, not a trapped void); the disc is otherwise solid."""
    pitch, bore_r, thr_depth, overlap, thread_h, thr_major = _thread_geometry(thread_standard)
    n = max(2, port_count)
    th = max(thread_h + 3.0, turret_thick)

    ring_r = _port_ring_radius(thr_major, n)
    rim = 6.0
    disc_r = ring_r + thr_major / 2.0 + rim

    disc = cq.Workplane("XY").circle(disc_r).extrude(th)
    disc = _fillet_safe(disc, "|Z", 2.0)
    disc = _knurl(disc, disc_r * 2.0, th)

    import math
    for i in range(n):
        ang = 2.0 * math.pi * i / n
        cx = ring_r * math.cos(ang)
        cy = ring_r * math.sin(ang)
        # Through bore for this objective port (open to both faces → no trapped void).
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, cy, th / 2.0))
            .cylinder(th + 2.0, bore_r)
        )
        disc = disc.cut(bore)
        # Fuse the female thread near the BOTTOM opening (objective enters from below).
        thr = female_thread(bore_r, pitch, thread_h, thr_depth, overlap)
        thr = thr.translate((cx, cy, 0.5))
        disc = disc.union(thr)

    # Central pivot: a through hole for the turret axle (open both faces).
    pv = max(2.0, pivot_bore)
    pivot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, th / 2.0))
        .cylinder(th + 2.0, pv / 2.0)
    )
    disc = disc.cut(pivot)
    return disc


# ─── Mode 2: male objective stub / bench adapter ──────────────────────────────
def build_male_stub():
    """A male-threaded stub: an RMS/M25 male thread on a short shaft rising from a
    knurled base disc. Screwed into a female port it lets an objective (or a C-mount
    optic on the flat base) hang on the bench or a stand outside the scope. Solid
    shaft + open-faced base → no trapped void."""
    pitch, bore_r, thr_depth, overlap, thread_h, thr_major = _thread_geometry(thread_standard)
    shaft_r = bore_r - thr_depth - 0.05
    base_d = thr_major + 12.0
    base_h = 6.0
    stub_h = thread_h + 2.0

    base = cq.Workplane("XY").circle(base_d / 2.0).extrude(base_h)
    base = _fillet_safe(base, "|Z", 1.5)
    base = _knurl(base, base_d, base_h)

    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, base_h))
        .circle(shaft_r).extrude(stub_h)
    )
    stub = base.union(shaft)

    thr = male_thread(shaft_r, pitch, thread_h, thr_depth, overlap)
    thr = thr.translate((0, 0, base_h + 1.0))
    stub = stub.union(thr)
    return stub


# ─── Mode 3: threaded port dust plug ──────────────────────────────────────────
def build_dust_plug():
    """A male-threaded plug with a low knurled head that screws into an empty
    turret port to seal it against dust. Male thread = fused helical rib on a solid
    shaft; head is open-faced. No trapped void."""
    pitch, bore_r, thr_depth, overlap, thread_h, thr_major = _thread_geometry(thread_standard)
    shaft_r = bore_r - thr_depth - 0.05
    head_d = thr_major + 6.0
    head_h = 4.0
    plug_h = thread_h + 1.5

    head = cq.Workplane("XY").circle(head_d / 2.0).extrude(head_h)
    head = _fillet_safe(head, ">Z", 1.0)
    head = _knurl(head, head_d, head_h)

    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, head_h))
        .circle(shaft_r).extrude(plug_h)
    )
    plug = head.union(shaft)

    thr = male_thread(shaft_r, pitch, thread_h, thr_depth, overlap)
    thr = thr.translate((0, 0, head_h + 0.75))
    plug = plug.union(thr)
    return plug


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "nosepiece":
    result = build_nosepiece()
elif target_part == "male_stub":
    result = build_male_stub()
elif target_part == "dust_plug":
    result = build_dust_plug()
else:
    result = build_nosepiece()
