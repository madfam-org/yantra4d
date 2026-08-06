import cadquery as cq


# ─── Sandbox-safe parameter access ───────────────────────────────────────────
def PARAM(getter, default):
    try:
        return getter()
    except Exception:
        return default


target_part = PARAM(lambda: target_part, "barrel_clamp")
syringe = str(PARAM(lambda: syringe, "10mL"))
leadscrew = str(PARAM(lambda: leadscrew, "T8"))
clearance = float(PARAM(lambda: clearance, 0.35))
block_w = float(PARAM(lambda: block_w, 40.0))
mount_bolt = float(PARAM(lambda: mount_bolt, 4.4))

# ─── Real-world reference dimensions (cited in manifest CDG standards) ─────────
# Standard Luer syringe barrel outer diameters (BD/Terumo convention, mm):
#   1 mL ~6.6, 3 mL ~9.7, 5 mL ~12.5, 10 mL ~15.9, 20 mL ~20.1.
# Leadscrew drives: T8 trapezoidal (major Ø 8, lead 8, pitch 2) and
#   M8 metric (major Ø 8, pitch 1.25) — the common 3D-printer / pump leadscrews.
SYRINGE_BARREL_D = {
    "1mL": 6.6, "3mL": 9.7, "5mL": 12.5, "10mL": 15.9, "20mL": 20.1,
}
LEADSCREW_SPECS = {
    "T8": {"major_d": 8.0, "pitch": 2.0},
    "M8": {"major_d": 8.0, "pitch": 1.25},
}
THREAD_TURNS = 3.5   # half-integer → well-conditioned helical sweep


def _barrel_d(name):
    return SYRINGE_BARREL_D.get(str(name).strip(), SYRINGE_BARREL_D["10mL"])


def _lead_spec(name):
    return LEADSCREW_SPECS.get(str(name).strip().upper(), LEADSCREW_SPECS["T8"])


def _fillet_safe(wp, sel, r):
    try:
        return wp.edges(sel).fillet(r)
    except Exception:
        return wp


# ── Inlined thread primitive (repo-lib imports blocked in sandbox) ────────────
def _helix_path(pitch, height):
    return cq.Wire.makeHelix(pitch=pitch, height=height, radius=1e-6)


def female_thread(bore_r, pitch, thread_h, thr_depth, overlap):
    """Internal helical rib fused into a bore wall; crest points inward to grip
    the leadscrew. Half-integer turns keep the sweep well-conditioned."""
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


def _bolt_ears(block_len, block_h, ear_z, hole_d, span):
    """Two through bolt holes down the block for mounting to the pump frame."""
    holes = (
        cq.Workplane("XY")
        .pushPoints([(-span / 2.0, 0), (span / 2.0, 0)])
        .circle(hole_d / 2.0)
        .extrude(block_h + 2.0)
        .translate((0, ear_z, -1.0))
    )
    return holes


# ─── Mode 1: barrel clamp saddle ──────────────────────────────────────────────
def build_barrel_clamp():
    """A saddle block that cradles a syringe barrel in a semicircular channel and
    bolts to the pump bed. The barrel channel is a half-cylinder groove open to the
    top (drop-in), so nothing is a sealed void; two bolt holes pass through."""
    bd = _barrel_d(syringe) + 2.0 * clearance
    w = max(block_w, bd + 16.0)
    depth = bd + 12.0
    h = bd * 0.65 + 8.0

    block = cq.Workplane("XY").box(w, depth, h, centered=(True, True, False))
    block = _fillet_safe(block, "|Z", 2.0)

    # Semicircular barrel channel along Y, open to the top face.
    chan = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h, -depth / 2.0 - 1.0))
        .circle(bd / 2.0)
        .extrude(depth + 2.0)
    )
    block = block.cut(chan)

    holes = _bolt_ears(w, h, 0.0, mount_bolt, w - bd - 6.0)
    block = block.cut(holes)
    return block


# ─── Mode 2: plunger pusher (leadscrew carriage) ──────────────────────────────
def build_plunger_pusher():
    """The moving carriage: a body with a female-threaded leadscrew nut bore
    (fused helical rib, half-integer turns) and a slotted flange cradle that
    captures the syringe plunger's thumb flange to push it. The nut bore opens to
    both ends (a through nut); the plunger slot opens to the top and front → no
    trapped void."""
    g = _lead_spec(leadscrew)
    pitch = g["pitch"]
    bore_r = (g["major_d"] + 2.0 * clearance) / 2.0
    thr_depth = 0.55 * pitch
    overlap = 0.45
    thread_h = pitch * THREAD_TURNS

    bd = _barrel_d(syringe)
    w = max(block_w, bd + 20.0)
    h = max(bd + 14.0, g["major_d"] + 16.0)
    depth = thread_h + 10.0

    body = cq.Workplane("XY").box(w, depth, h, centered=(True, True, False))
    body = _fillet_safe(body, "|Z", 2.0)

    # Leadscrew nut: a through bore along Y at mid height, with a fused female thread.
    nut_bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h / 2.0, -depth / 2.0 - 1.0))
        .circle(bore_r)
        .extrude(depth + 2.0)
    )
    body = body.cut(nut_bore)
    # Thread runs along Y; build it on Z then rotate to lie along Y.
    thr = female_thread(bore_r, pitch, thread_h, thr_depth, overlap)
    thr = thr.rotate((0, 0, 0), (1, 0, 0), -90.0)
    thr = thr.translate((0, -depth / 2.0 + (depth - thread_h) / 2.0, h / 2.0))
    body = body.union(thr)

    # Plunger flange slot: a vertical slot at the top front to capture the thumb flange.
    slot_w = 3.0 + 2.0 * clearance
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, depth / 2.0, h - (h * 0.45)))
        .box(bd + 6.0, slot_w, h, centered=(True, True, False))
    )
    body = body.cut(slot)
    return body


# ─── Mode 3: barrel retainer block (flange stop) ──────────────────────────────
def build_barrel_block():
    """A retainer block with a full barrel bore through it plus a drop-in slot for
    the barrel's finger flange, so the barrel end is captured against the pump's
    fixed end. The bore is open at both ends; the flange slot opens to the top →
    watertight."""
    bd = _barrel_d(syringe) + 2.0 * clearance
    w = max(block_w, bd + 16.0)
    h = bd + 14.0
    depth = 14.0

    block = cq.Workplane("XY").box(w, depth, h, centered=(True, True, False))
    block = _fillet_safe(block, "|Z", 2.0)

    bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, h / 2.0, -depth / 2.0 - 1.0))
        .circle(bd / 2.0)
        .extrude(depth + 2.0)
    )
    block = block.cut(bore)

    # Drop-in flange slot from the top down to the bore centre.
    flange_slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, h / 2.0))
        .box(bd + 8.0, depth * 0.5, h, centered=(True, True, False))
    )
    block = block.cut(flange_slot)

    holes = _bolt_ears(w, h, 0.0, mount_bolt, w - bd - 6.0)
    block = block.cut(holes)
    return block


# ─── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "barrel_clamp":
    result = build_barrel_clamp()
elif target_part == "plunger_pusher":
    result = build_plunger_pusher()
elif target_part == "barrel_block":
    result = build_barrel_block()
else:
    result = build_barrel_clamp()
