# Neopixel / LED Matrix Frame

Frames, diffusers, and mounts for **WS2812 / NeoPixel** addressable LED matrices,
generated with **CadQuery** (B-Rep) to the **real grid pitch**: WS2812B panels
use a **~10 mm pixel pitch** (an 8×8 panel is ≈ 80 mm, a 16×16 is ≈ 160 mm; each
5050 LED is ~5×5 mm). Three distinct grid modes.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Bezel Frame** | `bezel_frame` | A picture-frame bezel that surrounds the panel with a front lip (window) and a rear rebate the PCB drops into. |
| **Diffuser Grid** | `diffuser_grid` | An egg-crate: a thin floor + a wall grid with one open cell per pixel, so each LED lights its own diffused square (no bleed). |
| **Panel Mount** | `panel_mount` | A rear mounting plate on the panel footprint with corner screw bosses and a cable slot. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Matrix Grid | `cols` / `rows` | 8 / 8 | Pixel grid (8 or 16 for standard panels). |
| Matrix Grid | `pitch` | 10 mm | Centre-to-centre pixel spacing (WS2812 ~10 mm). |
| Frame & Walls | `wall` | 2 mm | Frame / cell wall thickness. |
| Frame & Walls | `depth` | 8 mm | Frame / grid depth; deeper diffuser cells reduce bleed. |
| Frame & Walls | `lip` | 2.5 mm | Bezel front lip / diffuser floor. |
| Mount | `screw_d` | 3.2 mm | Corner mount screw clearance (M3 ~3.2 mm). |

## Presets

- **8×8 Bezel** / **8×8 Diffuser** / **8×8 Panel Mount** — the common 8×8 panel.
- **16×16 Diffuser** — the larger 256-pixel panel.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **WS2812 Pixel Grid** (`grid`, *WS2812B 8×8 / 16×16, ~10 mm pitch*) — the
    pixel lattice (`cols`, `rows`, `pitch`); the interface that aligns the frame
    / diffuser to the panel.
  - **Corner Screw Mount** (`bolt_pattern`, *ISO 7045 M3*) — the mount bosses.
- **Material awareness:** cell / rebate fit is set by `pitch` and `wall`, tunable
  per printer; `tolerance_by_material` is declared.
- **Societal benefit:** matrices are a commodity but a diffuser or frame that
  matches your exact panel is not; driving all three parts off the real WS2812
  pixel pitch lets anyone print a clean, glare-free matrix display at any size.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained + sandbox-safe: params via `PARAM(lambda: name, default)`, final
  solid assigned to `result`.
- **Watertight by construction:** the border is filleted **before** cutting; the
  diffuser is a solid slab with a grid of **through** cells (each opens
  front→back, no trapped void); the bezel window + rebate open to faces; bosses
  are solid and bored fully through. The whole cell / boss grid is unioned into
  **one** cutter and subtracted once (fast + robust). All three modes and the
  MIN/MAX extremes — up to a 16×16 (330 mm) panel — render watertight, one body.
