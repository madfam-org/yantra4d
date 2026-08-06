# Featherboard

An anti-kickback featherboard generated with **CadQuery** (B-Rep): a bank of
angled, flexible fingers that press a workpiece against a fence or table and act
as a one-way ratchet — the stock feeds forward freely but is gripped if it tries
to kick back. The mount varies by machine.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **T-Slot / Track** | `tslot_feather` | Body with two knob slots and a 19 mm runner rib that seats in a T-track. |
| **Miter-Slot Bar** | `miter_feather` | Body with a 3/4in × 3/8in miter bar underneath for a saw/router table slot. |
| **Clamp-On** | `clamp_feather` | Plain body with open-ended clamp slots to fix to any surface. |

Each mode's part id equals the `target_part` the code dispatches on, so every
mode renders its own distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Feather Fingers | `feather_n` | 12 | Number of flexible fingers. |
| Feather Fingers | `kerf` | 1.6 mm | Slot width between fingers — controls flex. |
| Feather Fingers | `finger_ang` | 30° | Finger rake — the one-way grip direction. |
| Feather Fingers | `finger_len` | 35.0 mm | Length of the flexing fingers. |
| Body | `body_w` / `body_len` | 90 / 70 mm | Bank width and mounting-body length. |
| Body | `thick` | 9.0 mm | Board thickness. |

## Presets

- **Table-Saw Fence (T-Slot)** — a 12-finger board with a T-track runner.
- **Router Table Miter Bar** — a 14-finger board with a 3/4in miter bar.
- **Band-Saw Clamp-On** — a 10-finger clamp-on board.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Featherboard Fingers** (`profile`, standard *T-slot / 3/4in miter*) — the
    raked finger comb defined by `feather_n`, `kerf`, `finger_ang`, `finger_len`,
    `thick`. The finger pitch and rake set the grip.
  - **Machine Mount** (`rail`, standard *3/4in × 3/8in miter slot; 19mm T-track*)
    — the underside runner/bar that indexes the board to the machine.
- **Material awareness:** `tolerance_by_material` — kerf can be tuned so fingers
  flex correctly in the chosen filament.
- **Societal benefit:** cheap, replaceable machine safety — printable fingers
  hold stock down and stop kickback, keeping hands out of the blade.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- All shipped presets and defaults render **watertight**. `math` is used for the
  finger rake trigonometry.
