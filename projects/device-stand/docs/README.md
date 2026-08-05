# Phone / Tablet Stand

An angled desk stand generated with **CadQuery** (B-Rep) that cradles a phone or
tablet in a slot tilted to a comfortable viewing angle. A front lip catches the
device and a bottom cable slot lets it charge while docked.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Stand** | `stand` | A one-piece easel wedge: a solid triangular prism with a tilted device slot and a front catch lip. |
| **Adjustable** | `adjustable` | A two-part set — a base tray with a row of angle notches, plus a separate prop leg whose foot seats in any notch to change the lean. |
| **Dock** | `dock` | A wedge stand with an L-shaped cable channel routed from the back through to the device slot, plus a raised back support wall. |

The studio dispatches the active part via `target_part` (`stand` /
`adjustable` / `dock`); each mode renders distinct geometry.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Device Fit | `device_t` | 11.0 mm | Width of the rest slot the device sits in. |
| Device Fit | `angle` | 60° | Lean from horizontal (35–80°). |
| Device Fit | `width` | 100.0 mm | Width across the device. |
| Device Fit | `lip_h` | 12.0 mm | Front ledge height. |
| Stand Form | `depth` | 75.0 mm | Front-to-back footprint. |
| Stand Form | `height` | 70.0 mm | Height of the resting face. |
| Stand Form | `wall` | 4.0 mm | Body / slot wall thickness. |
| Cable | `cable_slot` | on | Notch under the rest for a charging cable (Stand, Dock). |
| Cable | `cable_w` | 16.0 mm | Cable slot / channel width. |

## Presets

- **Phone (upright 65°)** — a compact 85 mm phone easel with a cable slot.
- **Tablet Easel (55°)** — a wide 190 mm tablet stand at a shallower lean.
- **Charging Dock** — a cased-phone dock with an 18 mm routed cable channel.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Device Rest Slot** (`profile`, internal) — the tilted resting channel,
    defined internally by `device_t`, `angle`, `wall`, and `lip_h`. Any device
    up to `device_t` thick at the chosen `angle` rests in the same slot.
  - **Cable Pass-Through** (`socket`, internal) — `cable_slot`, `cable_w`.
- **Material awareness:** the slot width `device_t` is the raw device thickness;
  add a per-material clearance for a snug or loose fit. `tolerance_by_material`
  is declared.
- **Societal benefit:** a stand is the most-printed phone/tablet accessory;
  sizing the rest slot to the exact device and the lean to the user keeps
  devices propped for calls and reading without a plastic dock per device.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not
  expose `globals()` / `eval`. The final solid is assigned to `result`.
- All cavities are cut with bores that overshoot the body, so every shipped
  preset, default, and mode renders **watertight**.
