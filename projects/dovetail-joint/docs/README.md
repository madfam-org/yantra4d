# Dovetail / Slide Joint

A **male + female dovetail slide connection** generated with **CadQuery** (B-Rep)
for joining modular parts. The male is a trapezoidal rail — wider at its flare
than its neck, so it cannot pull straight out — and the female is a matching
socket cut into a block. Because the socket is the **same trapezoid inflated by
the print clearance**, the two halves slide together and mate every time.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Parts

| Part | Description |
| :--- | :--- |
| **Male Rail** (`male`) | The trapezoidal dovetail rail on a backing plate. |
| **Female Socket** (`female`) | A block with the matching dovetail groove cut through it. |
| **Matched Pair** (`pair`) | Both, laid side by side to show the fit. |

The studio dispatches the active part via `target_part`.

## Joint types (`joint_type`)

| Type | Behaviour |
| :--- | :--- |
| `straight_slide` | Open-ended groove; the rail slides fully through. |
| `locking` | A detent bump on the rail plus a stop in the socket, so the rail clicks in near the far end and resists sliding back out. |

## How the halves mate

The male tail and the female cavity are the **same trapezoid**, the cavity simply
inflated by `clearance` on every face. At the defaults (20 mm flare, 15° flanks,
0.2 mm clearance):

- Male tail: neck 15.7 mm → flare 20.0 mm (flare > neck ⇒ an **undercut** that
  cannot lift straight out).
- Female cavity: neck 16.1 mm → flare 20.4 mm.
- Result: a **0.2 mm per-flank gap** on every face — a printable slip fit. A
  boolean check of the male tail against the female solid returns **0 %
  interference**: the tail sits cleanly inside the cavity.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Dovetail | `dt_width` | 20.0 mm | Widest (flare) width of the tail. |
| Dovetail | `dt_depth` | 8.0 mm | Rail height / groove depth. |
| Dovetail | `angle` | 15° | Flank undercut angle (0 = square rail). |
| Dovetail | `length` | 40.0 mm | Slide length along the rail axis. |
| Fit & Type | `joint_type` | `straight_slide` | Straight slide or locking detent. |
| Fit & Type | `clearance` | 0.2 mm | Per-flank printed fit gap. |
| Body | `plate_thick` | 4.0 mm | Backing plate / socket floor thickness. |
| Body | `block_extra` | 8.0 mm | Material each side of the dovetail. |

## Presets

- **Modular Rail 20 mm** — the standard straight-slide 20 mm dovetail pair.
- **Locking Tab Joint** — a 24 mm detent joint that clicks shut.
- **Fine Slide Rail (male)** — a slim 12 mm rail for delicate slides.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Dovetail Slide** (`profile`, internal) — the slide profile, defined by
    `dt_width`, `dt_depth`, `angle`, `length`, `clearance`, `joint_type`. Any male
    and female generated at the same width + angle + clearance interlock.
- **Material awareness:** the fit clearance is exposed (`clearance`) so the slide
  tunes per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a shared dovetail profile turns any two printed parts into
  a strong, tool-free, reconfigurable joint — the basis of modular fixtures, tool
  walls, furniture, and grid systems.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Male and female are generated from a single shared trapezoid so they are
  guaranteed to mate; every shipped preset, part, and extreme renders **watertight**.
