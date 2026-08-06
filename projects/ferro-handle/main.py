"""
Firestarter / Ferro Handle — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Handles and holders for bare ferrocerium (ferro) fire rods. Bare ferro rods ship
as plain metal rods in two common diameters — 6 mm and 8 mm — with no grip. This
cartridge gives each a printable, ergonomic grip that sockets the rod and a
matching striker/scraper holder, all sized to the same rod-diameter interface.

  - rod_handle    : an ergonomic ribbed grip that sockets the ferro rod in one end
                    (blind bore from the end face) with a lanyard hole; a cross
                    grub-screw hole locks the rod.
  - striker_holder: a flat scraper/striker handle — a comfortable grip that clamps
                    a striker (a 90°-spine scraper blade or hacksaw blade) in an
                    end slot, with a ferro-rod socket on the opposite end so rod
                    and striker store as one tool.
  - combo_toggle  : a compact barrel toggle that sockets a short ferro rod and
                    carries a lanyard bore — a keychain / zipper-pull fire bit.

Real dimensions:
  - ferro rod diameters: 6 mm and 8 mm (default rod_d = 8 mm, the common survival
    size); the socket is bored `rod_d + fit` so a rod press- or grub-screw-fits.

Watertight strategy:
  Every part is ONE solid. The rod socket is a blind bore drilled from an exterior
  END face (open to that face → it vents, not a trapped void). The lanyard hole
  and grub-screw hole are through-bores. The striker slot is an obround through
  cut. Grip ribs are unioned bosses (solid). Fillets clean the blank BEFORE
  feature cuts, wrapped in try/except.

Sandbox contract (apps/api/services/engine/cq_runner.py):
  `cq` and `math` are pre-injected globals; manifest parameters arrive as bare
  globals (e.g. `target_part`). Read them via PARAM(lambda: name, default).
  Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else default. `except Exception`
    catches the NameError the sandbox raises for an unbound parameter name."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
target_part = str(PARAM(lambda: target_part, "rod_handle"))
# "rod_handle" | "striker_holder" | "combo_toggle"

rod_d = float(PARAM(lambda: rod_d, 8.0))          # ferro rod diameter (6 or 8 mm)
fit = float(PARAM(lambda: fit, 0.3))              # per-diameter socket clearance
wall = float(PARAM(lambda: wall, 4.0))            # wall around the socket (mm)
grip_len = float(PARAM(lambda: grip_len, 75.0))   # handle grip length (mm)
socket_depth = float(PARAM(lambda: socket_depth, 20.0))  # rod insertion depth (mm)
grub_d = float(PARAM(lambda: grub_d, 3.2))        # cross grub-screw hole (M3 ~3.2)
lanyard_d = float(PARAM(lambda: lanyard_d, 5.0))  # lanyard / cord hole (mm)

# Clamp to sane ranges so extreme UI values never crash the kernel.
rod_d = max(4.0, min(rod_d, 12.0))
fit = max(0.1, min(fit, 0.8))
wall = max(2.5, min(wall, 8.0))
grip_len = max(45.0, min(grip_len, 140.0))
socket_depth = max(10.0, min(socket_depth, grip_len - 8.0))
grub_d = max(2.0, min(grub_d, 5.0))
lanyard_d = max(3.0, min(lanyard_d, 8.0))

bore_d = rod_d + fit
grip_d = bore_d + 2.0 * wall                      # round grip outer diameter


# ── Shared helpers ───────────────────────────────────────────────────────────
def _end_socket(diameter, depth, z_top):
    """A cutting cylinder for a blind socket bored DOWN from the top end face at
    z_top (so it opens to that exterior face → vents). Over-cuts 0.5 past the
    face; leaves a solid floor `depth` below."""
    return (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, z_top - depth))
        .circle(diameter / 2.0)
        .extrude(depth + 0.5)
    )


def _cross_hole(diameter, through_w, z):
    """A through-hole across X at height z (vents both sides)."""
    return (
        cq.Workplane("YZ")
        .transformed(offset=cq.Vector(0, z, 0))
        .circle(diameter / 2.0)
        .extrude(through_w / 2.0 + 1.0, both=True)
    )


# ── Part builders ────────────────────────────────────────────────────────────
def build_rod_handle():
    """An ergonomic round grip standing on +Z. The ferro rod sockets into a blind
    bore from the TOP end face; a lanyard hole passes through the bottom, and a
    grub-screw hole crosses into the socket to lock the rod. Finger ribs are
    unioned rings."""
    body = (
        cq.Workplane("XY")
        .circle(grip_d / 2.0)
        .extrude(grip_len)
    )
    # dome the bottom end a touch, guarded
    try:
        body = body.faces("<Z").edges().fillet(min(3.0, wall * 0.6))
    except Exception:
        pass

    # Finger ribs: shallow rings unioned around the grip (solid, no voids).
    n_ribs = max(3, int(grip_len // 16))
    rib_r = grip_d / 2.0 + 0.8
    for i in range(n_ribs):
        z = 10.0 + i * (grip_len - 20.0) / max(1, n_ribs - 1)
        ring = (
            cq.Workplane("XY")
            .transformed(offset=cq.Vector(0, 0, z - 1.5))
            .circle(rib_r)
            .extrude(3.0)
        )
        body = body.union(ring)
    # Re-round the outer profile lightly, guarded.
    try:
        body = body.faces(">Z").edges().fillet(min(2.0, wall * 0.4))
    except Exception:
        pass

    # Rod socket: blind bore from the TOP face (opens to that face → vents).
    body = body.cut(_end_socket(bore_d, socket_depth, grip_len))

    # Lanyard hole through the bottom stub, below the socket floor.
    lz = min(6.0, (grip_len - socket_depth) * 0.5)
    body = body.cut(_cross_hole(lanyard_d, grip_d, lz))

    # Grub-screw hole crossing into the socket near the mouth.
    gz = grip_len - socket_depth * 0.4
    body = body.cut(_cross_hole(grub_d, grip_d, gz))
    return body


def build_striker_holder():
    """A flat scraper handle: a rounded rectangular grip. One end holds a striker
    (a scraper spine / hacksaw blade) in an obround end slot; the OTHER end
    sockets a ferro rod (blind bore from that end face). Rod + striker travel as
    one tool. A lanyard hole passes through the middle."""
    body_w = grip_d + 4.0
    body_t = rod_d + 2.0 * wall
    body = (
        cq.Workplane("XY")
        .box(body_w, grip_len, body_t, centered=(True, True, False))
    )
    body = _fillet_all_z(body, min(6.0, body_w * 0.3))

    # Striker slot in the +Y end (obround, vents out the end and top/bottom).
    slot_w = max(1.6, wall * 0.5)          # blade thickness slot
    slot_span = body_w * 0.55
    slot_depth = min(16.0, grip_len * 0.28)
    striker = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, grip_len / 2.0 - slot_depth / 2.0 + 0.5, -0.5))
        .slot2D(slot_span, slot_w, angle=0)
        .extrude(body_t + 1.0)
    )
    body = body.cut(striker)
    # pin hole to clamp the striker blade (through the slot region)
    body = body.cut(_cross_hole(grub_d, body_t, body_t * 0.5)
                    .translate((0, grip_len / 2.0 - slot_depth * 0.5, 0)))

    # Ferro-rod socket in the −Y end: bore in from that END face along +Y.
    rod_bore = (
        cq.Workplane("XZ")
        .transformed(offset=cq.Vector(0, body_t / 2.0, grip_len / 2.0 + 0.5))
        .circle(bore_d / 2.0)
        .extrude(socket_depth + 0.5)
    )
    body = body.cut(rod_bore)

    # Lanyard hole through the middle (vents through thickness).
    lan = (
        cq.Workplane("XY")
        .transformed(offset=cq.Vector(0, 0, -0.5))
        .circle(lanyard_d / 2.0)
        .extrude(body_t + 1.0)
    )
    body = body.cut(lan)
    return body


def build_combo_toggle():
    """A compact barrel toggle: sockets a short ferro rod (blind bore from the top
    end face) and carries a cross lanyard bore — a zipper-pull / keychain fire
    bit. Deliberately short and round for a pocket. One solid."""
    tog_len = min(grip_len, socket_depth + wall + 12.0)
    body = (
        cq.Workplane("XY")
        .circle(grip_d / 2.0)
        .extrude(tog_len)
    )
    try:
        body = body.edges("%Circle").fillet(min(2.5, wall * 0.5))
    except Exception:
        pass

    # Rod socket from the top face (vents).
    body = body.cut(_end_socket(bore_d, min(socket_depth, tog_len - wall), tog_len))

    # Cross lanyard bore near the bottom (through, vents both sides).
    lz = min(6.0, (tog_len - socket_depth) * 0.5 + 3.0)
    body = body.cut(_cross_hole(lanyard_d, grip_d, max(3.0, lz)))

    # Grub-screw hole to lock the rod near the mouth.
    gz = tog_len - min(socket_depth, tog_len - wall) * 0.4
    body = body.cut(_cross_hole(grub_d, grip_d, gz))
    return body


def _fillet_all_z(solid, r):
    """Fillet vertical edges of a prism blank, guarded."""
    try:
        return solid.edges("|Z").fillet(r)
    except Exception:
        return solid


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "striker_holder":
    result = build_striker_holder()
elif target_part == "combo_toggle":
    result = build_combo_toggle()
else:
    result = build_rod_handle()
