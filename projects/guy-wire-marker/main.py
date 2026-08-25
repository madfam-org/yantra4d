"""
Guy Wire Marker — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

High-visibility markers that make the guy wire of a utility pole visible. A guy
anchors a pole against line tension and runs at a shallow angle down to a ground
anchor, straight across a sidewalk, verge or driveway approach. It is thin, unlit,
and at head height for most of its run — it is struck by pedestrians, cyclists and
mowers, and it is the classic reason a utility gets a personal-injury claim.

The commercial answer is a moulded yellow guy guard: a long split tube that snaps
over the wire. It is a per-utility proprietary part, it goes missing, and a small
co-op or a private pole owner often cannot buy one at all.

Modes are dispatched via `target_part`:
  * "shell_pin"    — the pin half of a two-part clamshell guard section.
  * "shell_socket" — the socket half; print one of each and key them on the wire.
  * "snap_shell"   — a one-piece C-section that snaps over the wire without hardware,
                     for retrofitting a run without disturbing the tension.
  * "flag_disc"    — a disc marker that clamps to the wire at eye height, using the
                     same snap bore so it shares the clamshell's wire series.

Standards encoded (mm):
  Guy strand is EHS (extra-high-strength) galvanised steel strand, quoted by
  nominal diameter:
    3/16 in = 4.76,  1/4 in = 6.35,  5/16 in = 7.94,  3/8 in = 9.53,  1/2 in = 12.70
  The wire bore series here spans 4.0-14.0 so it also covers metric strand and a
  wire that has been served or taped. The snap boss pattern is shared with the
  published pv-cable-clip channel convention: a mouth narrower than the bore, sized
  as a fraction of bore Ø, so a printed part clicks on and is retained.

Watertightness strategy (a split shell as a closed manifold):
  Every part is a SOLID blank from which the wire bore is cut. The bore is ALWAYS
  opened to the outside — by the split plane on the clamshell, by the snap mouth on
  the C-section — so it is never a sealed internal void. A clamshell half is made by
  cutting the full shell with a half-space, which yields one connected solid, and the
  two halves are offset along X so they never touch (a tangent kiss between halves
  leaves a zero-area seam and reports as one non-watertight body). Alignment pins and
  their sockets OVERLAP volumetrically into the parent half rather than sitting
  tangent. Fillets are wrapped in try/except so a crashed blend degrades to a sharp
  edge instead of aborting the build.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters arrive as BARE globals; read them via
    PARAM(lambda: <name>, <default>) — never globals()/eval/getattr.
  - Assign the final solid to a top-level name `result`.
  - No cross-file imports: every helper is inlined here.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present and non-None, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Guy strand diameters (mm), EHS galvanised steel strand ───────────────────
STRAND_D = {
    "ehs_3_16": 4.76,    # 3/16 in
    "ehs_1_4": 6.35,     # 1/4 in
    "ehs_5_16": 7.94,    # 5/16 in
    "ehs_3_8": 9.53,     # 3/8 in
    "ehs_1_2": 12.70,    # 1/2 in
}


def strand_d(name):
    """Guy strand nominal diameter (mm), defaulting to 1/4 in EHS."""
    return STRAND_D.get(name, STRAND_D["ehs_1_4"])


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "clamshell"))
strand = str(PARAM(lambda: strand, "ehs_1_4"))          # guy strand spec key
clearance = float(PARAM(lambda: clearance, 0.6))        # bore slop over strand Ø (mm)
wall = float(PARAM(lambda: wall, 4.0))                  # shell wall (mm)
length = float(PARAM(lambda: length, 120.0))            # marker length along the wire (mm)
outer_dia = float(PARAM(lambda: outer_dia, 50.0))       # marker outside Ø (mm)
mouth = float(PARAM(lambda: mouth, 0.62))               # snap mouth as a fraction of bore Ø
disc_dia = float(PARAM(lambda: disc_dia, 150.0))        # flag disc Ø (mm)
disc_t = float(PARAM(lambda: disc_t, 4.0))              # flag disc thickness (mm)
pin_dia = float(PARAM(lambda: pin_dia, 4.0))            # alignment pin Ø (mm)

# Clamp so extreme UI values still build watertight.
clearance = max(0.0, min(clearance, 2.5))
wall = max(2.0, min(wall, 12.0))
length = max(25.0, min(length, 300.0))
outer_dia = max(16.0, min(outer_dia, 120.0))
mouth = max(0.40, min(mouth, 0.85))
disc_dia = max(50.0, min(disc_dia, 300.0))
disc_t = max(2.0, min(disc_t, 12.0))
pin_dia = max(2.0, min(pin_dia, 8.0))


# ── Derived radii ────────────────────────────────────────────────────────────
def _radii():
    """Return (bore_r, out_r): wire bore radius and marker outer radius.

    The outer radius is forced to clear the bore by at least `wall`, so a user who
    dials a large strand into a small outside Ø gets a thicker marker rather than a
    shell with negative wall (which would cut the body into a ring of fragments)."""
    bore_r = strand_d(strand) / 2.0 + clearance
    out_r = max(outer_dia / 2.0, bore_r + wall)
    return bore_r, out_r


# ── Part builders ─────────────────────────────────────────────────────────────
def _clamshell_half(pinned):
    """One half of the split shell: a C of material around the wire bore.

    The half is the full shell cut by a half-space, which leaves ONE connected solid.
    `pinned` selects which mating feature this half carries — bosses (the pin half)
    or sockets (the socket half) — so a printed pair keys together on the wire.

    Each half is its own part/mode rather than two disjoint solids in one body: the
    repo convention (see folding-board) is one printable piece per part, and a body
    containing two separated solids would fail the body_count == 1 contract."""
    bore_r, out_r = _radii()

    shell = cq.Workplane("XY").circle(out_r).extrude(length)
    try:
        shell = shell.edges("%CIRCLE").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass
    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(bore_r).extrude(length + 2.0)
    )
    shell = shell.cut(bore)

    # Cut away everything on +X, keeping the x <= 0 half. The killer box is oversized
    # on every axis so the cut is clean rather than coincident with a face.
    big = 4.0 * out_r + 20.0
    killer = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(big / 2.0, 0, -1.0))
        .box(big, big, length + 2.0, centered=(True, True, False))
    )
    body = shell.cut(killer)

    # Mating features on the split face (the plane x = 0), seated at mid-wall so they
    # are always fully inside material regardless of bore/outer ratio.
    pin_r = min(pin_dia / 2.0, max(0.8, wall * 0.35))
    seat_r = (bore_r + out_r) / 2.0
    pin_len = max(1.5, min(3.0, wall * 0.8))
    ov = min(1.0, wall * 0.4)
    z_pins = [length * 0.22, length * 0.78] if length >= 50.0 else [length * 0.5]

    for zc in z_pins:
        for sy in (-1.0, 1.0):
            cy = sy * seat_r
            if pinned:
                # Boss grows out of the split face; it OVERLAPS back into the half by
                # `ov` so the bond is volumetric, never a tangent kiss.
                boss = (
                    cq.Workplane("YZ")
                    .transformed(offset=cq.Vector(cy, zc, -ov))
                    .circle(pin_r).extrude(pin_len + ov)
                )
                body = body.union(boss)
            else:
                # Matching socket, opened through the split face (never a blind void
                # that could seal: it breaks out onto the flat mating plane).
                sock = (
                    cq.Workplane("YZ")
                    .transformed(offset=cq.Vector(cy, zc, -ov))
                    .circle(pin_r + 0.25).extrude(pin_len + ov + 0.5)
                )
                body = body.cut(sock)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_shell_pin():
    """The pin half of the clamshell guard (print one of each half per section)."""
    return _clamshell_half(pinned=True)


def build_shell_socket():
    """The socket half of the clamshell guard."""
    return _clamshell_half(pinned=False)


def build_snap_shell():
    """A one-piece C-section that snaps over the wire: no hardware, no disassembly
    of the guy. The mouth is narrower than the bore so it grips once sprung on."""
    bore_r, out_r = _radii()

    body = cq.Workplane("XY").circle(out_r).extrude(length)
    try:
        body = body.edges("%CIRCLE").fillet(min(1.5, wall * 0.4))
    except Exception:
        pass

    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(bore_r).extrude(length + 2.0)
    )
    body = body.cut(bore)

    # Snap mouth: a slot from the bore out through the wall, opening +Y.
    mw = max(1.0, 2.0 * bore_r * mouth)
    reach = 2.0 * out_r + 10.0
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
        .box(mw, reach, length + 2.0, centered=(True, False, False))
    )
    body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


def build_flag_disc():
    """A disc marker that clamps to the wire at eye height. The hub carries the same
    snap bore as the shells, so the disc and the guard share one wire series."""
    bore_r, out_r = _radii()
    hub_r = max(out_r, bore_r + wall)
    hub_h = max(disc_t + 6.0, 3.0 * bore_r)
    d_r = max(disc_dia / 2.0, hub_r + 6.0)
    ov = min(1.0, disc_t * 0.4)

    # Disc plate, centered on the hub's mid-height so the hub grips both faces.
    z_disc = (hub_h - disc_t) / 2.0
    disc = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_disc))
        .circle(d_r).extrude(disc_t)
    )
    try:
        disc = disc.edges("%CIRCLE").fillet(min(1.2, disc_t * 0.3))
    except Exception:
        pass

    # Hub cylinder, overlapping the disc volumetrically top and bottom.
    hub = cq.Workplane("XY").circle(hub_r).extrude(hub_h)
    body = hub.union(disc)

    # Wire bore straight through the hub (open both faces).
    bore = (
        cq.Workplane("XY").workplane(offset=-1.0)
        .circle(bore_r).extrude(hub_h + 2.0)
    )
    body = body.cut(bore)

    # Snap mouth through the hub AND the disc, so the whole part springs onto the
    # wire as one piece. Cutting through both keeps a single connected solid.
    mw = max(1.0, 2.0 * bore_r * mouth)
    reach = 2.0 * d_r + 10.0
    slot = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0.0, 0.0, -1.0))
        .box(mw, reach, hub_h + 2.0, centered=(True, False, False))
    )
    body = body.cut(slot)

    try:
        body = body.clean()
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
_dispatch = {
    "shell_pin": build_shell_pin,
    "shell_socket": build_shell_socket,
    "snap_shell": build_snap_shell,
    "flag_disc": build_flag_disc,
}

result = _dispatch.get(target_part, build_shell_pin)()
