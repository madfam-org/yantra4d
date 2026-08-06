"""
Pipe / Bar Clamp Jaws — Yantra4D Hyperobject Cartridge (CadQuery / B-Rep).

Printed jaws and feet that turn a length of black pipe into a bar clamp. A bore
sized to the pipe OD (1/2 in or 3/4 in nominal) slides the jaw onto the pipe; a
tall pad presses the work. Two jaws plus a threaded rod or the pipe's own thread
make a clamp.

Three modes, dispatched by `target_part`:
  - fixed_jaw    : a jaw pinned at the far end of the pipe with a clamp-screw
                   bore through the pad for a tail screw.
  - sliding_jaw  : a jaw that slides and cams/tips to grip the pipe (a set-screw
                   bore locks it), presenting a broad pad toward the fixed jaw.
  - spreader     : a jaw reversed so the pads face outward, converting the clamp
                   into a spreader that pushes parts apart.

The `pipe` select maps to the pipe OD:
  1/2in -> 21.3 mm, 3/4in -> 26.7 mm (NPS nominal outside diameters).

Sandbox contract (apps/api/services/engine/cq_runner.py):
  - `cq` and `math` are pre-injected globals.
  - Manifest parameters are injected as BARE globals (e.g. `pipe`).
  - Access them via PARAM(lambda: <name>, <default>). Do NOT use globals()/eval/
    getattr — they are not in the sandbox's allowed builtins.
  - Assign the final solid to a top-level name `result`.
"""

import cadquery as cq


# ── Sandbox-safe parameter access ────────────────────────────────────────────
def PARAM(getter, default):
    """Return an injected global if present, else the default."""
    try:
        v = getter()
        return default if v is None else v
    except Exception:
        return default


# ── Parameters ───────────────────────────────────────────────────────────────
pipe        = str(  PARAM(lambda: pipe,   "3/4in"))   # pipe standard (select)
fit         = float(PARAM(lambda: fit,       0.4))    # per-side clearance bore↔pipe
jaw_w       = float(PARAM(lambda: jaw_w,    45.0))    # jaw width
pad_h       = float(PARAM(lambda: pad_h,    55.0))    # clamp pad height (throat)
wall        = float(PARAM(lambda: wall,      8.0))    # wall around the pipe bore
screw_bore  = float(PARAM(lambda: screw_bore, 8.0))   # tail-screw / set-screw bore
depth       = float(PARAM(lambda: depth,    40.0))    # jaw depth along the pipe

target_part = str(PARAM(lambda: target_part, "fixed_jaw"))

# Map the pipe standard to nominal OD, then bore = OD + clearance per side.
_PIPE = {"1/2in": 21.3, "3/4in": 26.7}
pipe_od = _PIPE.get(pipe, 26.7)
bore = pipe_od + 2.0 * max(0.0, fit)
bore_r = bore / 2.0
# Body must wrap the bore with `wall` all round.
body_dia = bore + 2.0 * wall


# ── Helpers ──────────────────────────────────────────────────────────────────
def block(w, d, h, cx=True, cy=True):
    return cq.Workplane("XY").box(w, d, h, centered=(cx, cy, False))


def bore_y(dia, length, at):
    return (
        cq.Workplane("XZ")
        .circle(dia / 2.0)
        .extrude(length + 2.0)
        .translate((at[0], -length / 2.0 - 1.0, at[1]))
    )


def bore_z(dia, length, at):
    return (
        cq.Workplane("XY")
        .circle(dia / 2.0)
        .extrude(length + 2.0)
        .translate((at[0], at[1], -1.0))
    )


def collar_and_pad(collar_h):
    """Common jaw stem: a rectangular collar wrapping the pipe, bored through in
    Y. The pipe axis runs in +Y and passes through the collar mid-height; the pad
    rises in +Z above the collar in each jaw builder."""
    collar = block(max(jaw_w, body_dia), collar_h, body_dia)
    bore_cut = (
        cq.Workplane("XZ")
        .circle(bore_r)
        .extrude(collar_h + 2.0)
        .translate((0, -1.0, body_dia / 2.0))
    )
    return collar.cut(bore_cut)


# ── Fixed jaw (tail-screw jaw) ───────────────────────────────────────────────
def build_fixed_jaw():
    """A collar on the pipe with a tall pad; a tail-screw bore runs along the
    pipe axis through the pad so a screw can bear against the pipe end / a nut."""
    collar_h = depth
    collar = collar_and_pad(collar_h)
    # Pad rising above the collar toward the work.
    pad = block(max(jaw_w, body_dia), collar_h, pad_h).translate((0, 0, body_dia))
    body = collar.union(pad)
    # Tail-screw bore along the pipe axis (Y) through the pad, above the pipe.
    body = body.cut(bore_y(screw_bore, collar_h, (0.0, body_dia + pad_h * 0.5)))
    try:
        body = body.edges("|Y").fillet(min(wall * 0.4, 3.0))
    except Exception:
        pass
    return body


# ── Sliding jaw (set-screw grip) ─────────────────────────────────────────────
def build_sliding_jaw():
    """A taller collar that tips to grip the pipe; a set-screw bore from the top
    locks it, and a broad pad faces the fixed jaw."""
    collar_h = depth * 1.3
    collar = collar_and_pad(collar_h)
    pad = block(max(jaw_w, body_dia), collar_h * 0.7, pad_h).translate(
        (0, collar_h / 2.0 - collar_h * 0.35, body_dia)
    )
    body = collar.union(pad)
    # Vertical set-screw bore from the top into the collar body, beside the pipe.
    body = body.cut(bore_z(screw_bore, body_dia, (body_dia * 0.32, collar_h / 2.0 - collar_h * 0.35)))
    try:
        body = body.edges("|Y").fillet(min(wall * 0.35, 2.5))
    except Exception:
        pass
    return body


# ── Spreader (reversed pad) ──────────────────────────────────────────────────
def build_spreader():
    """A jaw whose pad faces OUTWARD (away from the pipe centre) so a pair pushes
    parts apart instead of together."""
    collar_h = depth
    collar = collar_and_pad(collar_h)
    # Pad hangs on the outboard face, projecting beyond the collar end.
    pad = block(max(jaw_w, body_dia), 10.0, pad_h).translate(
        (0, collar_h / 2.0 + 5.0, body_dia)
    )
    arm = block(max(jaw_w, body_dia), collar_h * 0.5 + 5.0, body_dia * 0.6).translate(
        (0, collar_h / 2.0 - collar_h * 0.25, body_dia)
    )
    body = collar.union(arm).union(pad)
    body = body.cut(bore_z(screw_bore, body_dia, (body_dia * 0.32, -collar_h * 0.25)))
    try:
        body = body.edges("|Y").fillet(min(wall * 0.35, 2.5))
    except Exception:
        pass
    return body


# ── Dispatch ─────────────────────────────────────────────────────────────────
if target_part == "sliding_jaw":
    result = build_sliding_jaw()
elif target_part == "spreader":
    result = build_spreader()
else:
    result = build_fixed_jaw()
