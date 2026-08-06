import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
# globals()/eval/NameError are NOT reliable in-sandbox; read every param via PARAM.
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "threaded_nest")
thread_standard = str(PARAM(lambda: thread_standard, "RMS"))
clearance = float(PARAM(lambda: clearance, 0.25))
nest_count = int(PARAM(lambda: nest_count, 3))
well_depth = float(PARAM(lambda: well_depth, 10.0))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# RMS (Royal Microscopical Society) objective thread: W 0.800 in x 36 TPI,
#   major Ø 20.32 mm, pitch 25.4/36 = 0.7056 mm (DIN 58888 / ISO 8038 / BS 7012).
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


def _knurl(solid, outer_d, height, teeth=28, depth=0.6):
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


# ─── Mode 1: single threaded objective nest ───────────────────────────────────
def build_threaded_nest():
    """A protective case body with a female-threaded nest: the objective screws
    in by its RMS/M25 thread. The thread is a volumetric helical rib UNIONED into
    the bore wall (not cut grooves); the bore opens at the top, a base seals the
    bottom, so there is no trapped void."""
    pitch, bore_r, thr_depth, overlap, thread_h, thr_major = _thread_geometry(thread_standard)
    wall = 4.0
    base_th = 5.0
    # Room below the thread for the objective's front lens to hang free.
    clearance_well = max(4.0, well_depth)

    outer_d = thr_major + 2.0 * wall
    body_h = thread_h + clearance_well + base_th + 2.0

    body = cq.Workplane("XY").circle(outer_d / 2.0).extrude(body_h)
    body = _fillet_safe(body, "|Z", 1.5)

    # Bore from the top down to the base (open to the top face only).
    bore_depth = thread_h + clearance_well + 1.0
    bore = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, body_h - bore_depth / 2.0))
        .cylinder(bore_depth, bore_r)
    )
    body = body.cut(bore)

    # Fuse the female thread near the top opening (where the objective engages).
    thr = female_thread(bore_r, pitch, thread_h, thr_depth, overlap)
    thr = thr.translate((0, 0, body_h - thread_h - 1.0))
    body = body.union(thr)

    body = _knurl(body, outer_d, body_h)
    return body


# ─── Mode 2: multi-nest storage block ─────────────────────────────────────────
def build_multi_nest_block():
    """A tray block holding N threaded objective nests in a row; each nest is a
    female-threaded bore (fused helical rib) opening to the top face."""
    pitch, bore_r, thr_depth, overlap, thread_h, thr_major = _thread_geometry(thread_standard)
    n = max(1, nest_count)
    wall = 5.0
    base_th = 6.0
    clearance_well = max(4.0, well_depth * 0.8)

    bore_pitch = thr_major + 2.0 * wall
    length = n * bore_pitch + wall
    width = thr_major + 2.0 * wall
    height = thread_h + clearance_well + base_th + 1.5

    block = cq.Workplane("XY").box(length, width, height, centered=(True, True, False))
    block = _fillet_safe(block, "|Z", 3.0)

    x0 = -(n - 1) * bore_pitch / 2.0
    bore_depth = thread_h + clearance_well + 1.0
    for i in range(n):
        cx = x0 + i * bore_pitch
        bore = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(cx, 0, height - bore_depth / 2.0))
            .cylinder(bore_depth, bore_r)
        )
        block = block.cut(bore)
        thr = female_thread(bore_r, pitch, thread_h, thr_depth, overlap)
        thr = thr.translate((cx, 0, height - thread_h - 1.0))
        block = block.union(thr)
    return block


# ─── Mode 3: threaded dust cap / plug ─────────────────────────────────────────
def build_dust_cap():
    """A male-threaded plug that screws INTO a nest to seal the stored objective.
    The external thread is a fused helical rib on the shaft; a knurled head gives
    grip. All geometry is solid + open-faced (no trapped void)."""
    pitch, bore_r, thr_depth, overlap, thread_h, thr_major = _thread_geometry(thread_standard)
    # Male shaft slightly under the female bore so it threads in with the clearance.
    shaft_r = bore_r - thr_depth - 0.05
    head_d = thr_major + 8.0
    head_h = 5.0
    plug_h = thread_h + 2.0

    # Knurled grip head.
    head = cq.Workplane("XY").circle(head_d / 2.0).extrude(head_h)
    head = _fillet_safe(head, ">Z", 1.2)
    head = _knurl(head, head_d, head_h)

    # Solid male plug shaft rising from the head.
    shaft = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, head_h))
        .circle(shaft_r).extrude(plug_h)
    )
    cap = head.union(shaft)

    # Fuse the external thread onto the shaft.
    thr = male_thread(shaft_r, pitch, thread_h, thr_depth, overlap)
    thr = thr.translate((0, 0, head_h + 1.0))
    cap = cap.union(thr)
    return cap


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "threaded_nest":
    result = build_threaded_nest()
elif target_part == "multi_nest_block":
    result = build_multi_nest_block()
elif target_part == "dust_cap":
    result = build_dust_cap()
else:
    result = build_threaded_nest()
