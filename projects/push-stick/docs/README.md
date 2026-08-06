# Push Stick / Push Block

A safety pusher generated with **CadQuery** (B-Rep) that keeps hands away from a
table-saw blade or jointer cutter. A rear heel notch hooks the trailing end of
the stock to push it through; the grip keeps the hand above and behind the cut.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Push Stick** | `push_stick` | A long tapered stick with a rear heel notch and a hand grip. |
| **Push Block** | `push_block` | A broad flat block with a downward heel lip and a raised top handle, for jointers and wide stock. |
| **Straddle Gripper** | `gripper` | A compact centred-grip pusher with front and rear heels to push on both sides of the cut. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Size | `length` | 260.0 mm | Overall length — longer keeps hands further back. |
| Size | `body_h` | 90.0 mm | Height that stands the grip off the table. |
| Size | `thick` | 18.0 mm | Material thickness of the body. |
| Size | `block_w` | 80.0 mm | Push-block / gripper foot width. |
| Grip & Heel | `heel` | 12.0 mm | Depth of stock the heel catches. |
| Grip & Heel | `grip_dia` | 32.0 mm | Finger aperture of the hand grip. |

## Presets

- **Table-Saw Push Stick** — a 300 mm tapered stick with a heel and grip.
- **Jointer Push Block** — a broad block with a heel lip for face jointing.
- **Narrow-Rip Gripper** — a compact straddle gripper for narrow rips.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Push Heel** (`profile`, internal) — the rear notch defined by `heel`,
    `thick`, `length`; catches the trailing end of any stock thinner than the
    grip stand-off.
  - **Hand Grip** (`socket`, internal) — `grip_dia`, `body_h`; the finger
    aperture that stands the hand clear of the cut.
- **Material awareness:** `recycled_material_toggle` — a disposable safety tool
  that prints happily in recycled filament.
- **Societal benefit:** a five-minute print that prevents the most common shop
  injury — fingers stay clear of the blade on every rip cut and jointer pass.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**.
