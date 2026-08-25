"""
Knurled Thumb Screw — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Printable hand-turned fasteners: a thumb screw, a thumb nut, and a wing screw,
all on real ISO metric threads (M5 or M6). The FUNCTIONAL interface is a genuine
single-start helical thread — VOLUMETRIC fused ribs swept along a true makeHelix
path, NOT boolean-cut grooves — so a printed thumb screw threads into the same
tapped hole or heat-set insert as a bought M5/M6 screw, and the thumb nut runs on
the same shaft. That makes these fasteners mate the iso-m6 family (the M6 bolt
circle of the sentinel-gripper flange, ISO 9409-1-50-4-M6).

  - thumb_screw : a knurled disc head on a male-threaded shaft. Tighten flexure
                  clamps, jigs and covers by hand.
  - thumb_nut   : a knurled female-threaded knob (a hand-turned nut) that runs on
                  an M5/M6 shaft — the mate for the thumb screw.
  - wing_screw  : a two-wing head on the same male-threaded shaft, for higher
                  hand-torque than a knurled disc.

Thread strategy (the #1 trap: turn count MUST be a half-integer):
  Threads are built as volumetric ribs — a trapezoidal profile swept along a
  `makeHelix` path and UNIONED into the shaft/bore (the rib root is pushed a small
  `overlap` into the surrounding material so the boolean is a clean volumetric
  fuse, not a fragile tangent kiss). The swept turn count is snapped to a
  HALF-INTEGER (floor(n)+0.5): an INTEGER turn count degenerates the OCCT helical
  sweep — the profile closes back on itself, the orientation flips, and the union
  yields a NEGATIVE-volume / null body. A half-integer is well-conditioned and far
  faster. Real hand-fasteners engage only a few turns, so the cap costs nothing.

Thread stock (nominal major diameter × pitch, mm — ISO 261 / ISO 965 coarse):
    M5 → 5.0 × 0.8     M6 → 6.0 × 1.0
Cited as the CDG `standard` = "M5/M6".

Watertight strategy:
  Male shaft = a solid cylinder with additive helical ribs unioned on (subtractive
  grooves would leave an unsealed spiral crest at long lengths — the additive rib
  at a half-integer turn count is watertight here because the shaft is short). The
  thumb nut is a knurled disc with a female rib unioned into a THROUGH bore, then
  the plain-diameter clearance kept so it is watertight (the rib crest is the only
  thing narrowing the bore). Heads/knurls are single polar-array cuts on the clean
  blank. No revolve-of-cut profiles.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals; params arrive as BARE globals.
  - Read each via PARAM(lambda: name, default); worker injects target_part.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq
import math


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Thread stock (nominal major diameter × pitch, mm) ────────────────────────
THREADS = {
    "M5": {"major_d": 5.0, "pitch": 0.8},
    "M6": {"major_d": 6.0, "pitch": 1.0},
}


def thread_geo(name):
    return THREADS.get(name, THREADS["M6"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "thumb_screw"))
# "thumb_screw" | "thumb_nut" | "wing_screw"

thread_size = str(PARAM(lambda: thread_size, "M6"))    # M5 | M6
clearance = float(PARAM(lambda: clearance, 0.35))      # printed-thread fit slop (per side, mm)
shaft_len = float(PARAM(lambda: shaft_len, 16.0))      # threaded shaft length (mm)
head_dia = float(PARAM(lambda: head_dia, 20.0))        # knurled head diameter (mm)
head_h = float(PARAM(lambda: head_h, 6.0))             # head thickness (mm)
knurl_teeth = int(PARAM(lambda: knurl_teeth, 24))      # grip flutes around the head
engage_turns = float(PARAM(lambda: engage_turns, 3.5))  # thread engagement (half-integer capped)

# ── Clamp inputs so extreme UI values still build watertight ─────────────────
clearance = max(0.0, min(clearance, 0.8))
shaft_len = max(6.0, min(shaft_len, 40.0))
head_dia = max(10.0, min(head_dia, 40.0))
head_h = max(3.0, min(head_h, 14.0))
knurl_teeth = max(8, min(knurl_teeth, 48))
engage_turns = max(1.5, min(engage_turns, 4.5))

g = thread_geo(thread_size)
major_d = g["major_d"]
pitch = g["pitch"]
thr_depth = 0.55 * pitch                   # radial thread depth
# Ceiling turn count so the shaft/bore thread never exceeds a validated half-int.
max_turns_shaft = min(engage_turns, (shaft_len - 1.0) / pitch)
max_turns_shaft = max(1.5, max_turns_shaft)


def _half_integer(n):
    """Snap a turn count to floor(n)+0.5 — a half-integer is well-conditioned for
    the OCCT helical sweep; an integer degenerates it into a null/negative body."""
    return math.floor(n) + 0.5


def _helix_path(p, height):
    """A helical wire centred on Z (radius ~0 → the swept profile, already at the
    target radius in its own plane, traces the true helix)."""
    return cq.Wire.makeHelix(pitch=p, height=height, radius=1e-6)


def male_thread(shaft_r, p, thread_h):
    """External (male) helical rib. Root bites `overlap` into the shaft surface
    (clean volumetric union); crest sticks out to shaft_r + thr_depth."""
    overlap = 0.35
    root_r = max(0.4, shaft_r - overlap)
    crest_r = shaft_r + thr_depth
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -p * 0.32),
            (crest_r, -p * 0.14),
            (crest_r, p * 0.14),
            (root_r, p * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(p, thread_h), isFrenet=True)
    return rib.translate((0, 0, p * 0.5))


def female_thread(bore_r, p, thread_h):
    """Internal (female) helical rib pointing INWARD from the bore wall. Root at
    bore_r + overlap (bites the wall); crest at bore_r - thr_depth."""
    overlap = 0.4
    root_r = bore_r + overlap
    crest_r = max(0.4, bore_r - thr_depth)
    prof = (
        cq.Workplane("XZ")
        .polyline([
            (root_r, -p * 0.32),
            (crest_r, -p * 0.14),
            (crest_r, p * 0.14),
            (root_r, p * 0.32),
        ])
        .close()
    )
    rib = prof.sweep(_helix_path(p, thread_h), isFrenet=True)
    return rib.translate((0, 0, p * 0.5))


def _threaded_shaft():
    """A male-threaded shaft rising from z=0. Returns (solid, shaft_top_z)."""
    # Male major diameter is nominal minus clearance per side (printed screws are
    # cut a touch thin so they run in a nominal tapped hole / insert).
    shaft_r = major_d / 2.0 - clearance
    shaft_r = max(0.8, shaft_r)
    turns = _half_integer(max_turns_shaft)
    thread_h = pitch * turns
    thread_h = min(thread_h, shaft_len - pitch * 0.6)
    thread_h = max(pitch * 1.5, thread_h)

    core = cq.Workplane("XY").circle(shaft_r).extrude(shaft_len)
    core = core.union(male_thread(shaft_r, pitch, thread_h))
    # Chamfer the free end so it starts into a hole. Cut a small cone off the tip.
    tip = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, shaft_len))
        .circle(shaft_r + thr_depth + 0.5)
        .workplane(offset=-1.2)
        .circle(shaft_r - 0.4)
        .loft(combine=False)
    )
    core = core.cut(tip)
    return core, shaft_len


def _knurled_disc(dia, h, teeth):
    """A cylindrical knob with shallow vertical grip flutes cut as one polar array
    on the clean blank (single boolean → cheap and watertight)."""
    r = dia / 2.0
    disc = cq.Workplane("XY").circle(r).extrude(h)
    try:
        disc = disc.edges(">Z or <Z").fillet(min(1.0, h * 0.2))
    except Exception:
        pass
    try:
        flute = (
            cq.Workplane("XY")
            .polarArray(radius=r, startAngle=0, angle=360, count=teeth)
            .rect(0.9, 2.4)
            .extrude(h + 2.0)
            .translate((0, 0, -1.0))
        )
        disc = disc.cut(flute)
    except Exception:
        pass  # knurl is cosmetic — never fatal
    return disc


# ── Part builders ────────────────────────────────────────────────────────────
def build_thumb_screw():
    """A knurled disc head on a male-threaded shaft."""
    head = _knurled_disc(head_dia, head_h, knurl_teeth)
    shaft, s_top = _threaded_shaft()
    # Lift the shaft to sit on top of the head, overlapping into it for a fused union.
    shaft = shaft.translate((0, 0, head_h - 0.01))
    body = head.union(shaft)
    return body


def build_wing_screw():
    """A two-wing head on the same male-threaded shaft (higher hand torque)."""
    # Wing head: a central hub with two flat wings (a rounded rectangular slab).
    hub_r = major_d / 2.0 + 3.0
    wing_len = head_dia
    wing_w = max(5.0, head_dia * 0.28)
    slab = cq.Workplane("XY").box(wing_len, wing_w, head_h, centered=(True, True, False))
    try:
        slab = slab.edges("|Z").fillet(min(wing_w * 0.45, 3.0))
    except Exception:
        pass
    hub = cq.Workplane("XY").circle(hub_r).extrude(head_h)
    head = slab.union(hub)

    shaft, s_top = _threaded_shaft()
    shaft = shaft.translate((0, 0, head_h - 0.01))
    body = head.union(shaft)
    return body


def build_thumb_nut():
    """A knurled female-threaded knob (a hand-turned nut) running on an M5/M6
    shaft. The female rib is unioned into a THROUGH bore; the bore vents both
    faces so the part is watertight (only the rib crest narrows it)."""
    disc = _knurled_disc(head_dia * 0.8, head_h + 1.5, knurl_teeth)
    h = head_h + 1.5

    # Female bore = major diameter plus clearance per side.
    bore_r = major_d / 2.0 + clearance
    turns = _half_integer(min(engage_turns, (h - 0.8) / pitch))
    thread_h = pitch * turns
    thread_h = min(thread_h, h - pitch * 0.6)
    thread_h = max(pitch * 1.5, thread_h)

    # Cut the through clearance bore (vents both faces).
    thru = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -1.0))
        .circle(bore_r)
        .extrude(h + 2.0)
    )
    body = disc.cut(thru)
    # Add the internal thread rib (nudged up so it does not start at the open rim).
    rib = female_thread(bore_r, pitch, thread_h).translate((0, 0, 0.4))
    body = body.union(rib)
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "thumb_nut":
    result = build_thumb_nut()
elif target_part == "wing_screw":
    result = build_wing_screw()
else:  # "thumb_screw" (default)
    result = build_thumb_screw()
