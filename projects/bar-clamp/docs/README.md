# Pipe / Bar Clamp Jaws

Printed jaws and feet generated with **CadQuery** (B-Rep) that turn a length of
black pipe into a bar clamp. A bore sized to the pipe OD (1/2 in or 3/4 in
nominal) slides the jaw onto the pipe; a tall pad presses the work. Two jaws plus
a threaded rod or the pipe's own thread make a clamp.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Fixed Jaw** | `fixed_jaw` | A collar pinned at the end of the pipe with a tail-screw bore through the pad. |
| **Sliding Jaw** | `sliding_jaw` | A taller collar that tips to grip the pipe, locked by a top set-screw, presenting a broad pad. |
| **Spreader Jaw** | `spreader` | A jaw with the pad reversed to face outward, converting the clamp into a spreader. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Pipe | `pipe` | 3/4in | Pipe standard (**1/2in → 21.3 mm OD, 3/4in → 26.7 mm OD**). |
| Pipe | `fit` | 0.4 mm | Per-side bore clearance so the jaw slides on the pipe. |
| Jaw | `jaw_w` | 45.0 mm | Jaw / pad width. |
| Jaw | `pad_h` | 55.0 mm | Pad height above the pipe (clamp throat). |
| Jaw | `wall` | 8.0 mm | Material wrapping the pipe bore. |
| Jaw | `depth` | 40.0 mm | Length of the jaw collar along the pipe. |
| Screw | `screw_bore` | 8.0 mm | Tail-screw (fixed) or set-screw (sliding) bore. |

## Presets

- **Panel Glue-Up Fixed (3/4in)** — a fixed jaw for long panel clamps.
- **Light Sliding Jaw (1/2in)** — a lighter sliding jaw on 1/2 in pipe.
- **Cabinet Spreader (3/4in)** — a reversed-pad spreader jaw.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Pipe Clamp Bore** (`socket`, standard *1/2in & 3/4in pipe*) — the pipe
    bore defined by `pipe`, `fit`, `depth`, `wall`. The `pipe` select maps to
    the NPS nominal OD (21.3 / 26.7 mm) so the jaw fits real pipe.
  - **Clamp Screw Bore** (`socket`, internal) — `screw_bore`; the tail- or
    set-screw aperture.
- **Material awareness:** `shrinkage_compensation` + `tolerance_by_material` —
  the bore clearance is exposed so the slide fit is tuned per material/printer.
- **Societal benefit:** a pair of printed jaws plus cheap pipe makes a bar clamp
  of any length — a low-cost alternative to buying long steel clamps.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
