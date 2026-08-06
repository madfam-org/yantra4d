# TX Tray Mount

A **tray / stand for an RC transmitter**, generated with **CadQuery** (B-Rep).
The radio's lower body drops into a cradle sized to its footprint; a **neck-strap
loop** takes the weight off your hands, and the whole thing **tilts** for
comfortable viewing.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Hand Tray** | `tray` | The tilted cradle with an optional neck-strap loop — the classic race tray. |
| **Desk Stand** | `desk_stand` | The cradle on a wedge foot so the radio stands angled on a bench for setup / simulator use. |
| **Phone Mount** | `phone_mount` | The tray plus a back post with a C-clip that holds a telemetry / FPV phone above the radio. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Radio | `radio_w` / `radio_d` | 160 / 45 mm | Transmitter body footprint. |
| Radio | `cradle_h` | 30 mm | Cradle wall height. |
| Radio | `wall` | 3.0 mm | Cradle wall thickness. |
| Radio | `radio_clear` | 1.0 mm | Per-side clearance around the radio. |
| Comfort | `tilt` | 20° | Viewing tilt toward the pilot. |
| Comfort | `strap_loop` / `loop_w` | on / 25 mm | Neck-strap loop and opening width. |
| Extras | `stand_depth` | 70 mm | Desk-stand wedge foot depth (desk mode). |
| Extras | `phone_w` / `phone_t` | 78 / 12 mm | Phone the clip grips (phone mode). |

## Interfaces

The **radio cradle** pocket is derived from `radio_w`/`radio_d` (plus
`radio_clear` and `wall`), so a tray generated for a 160×45 radio seats a 160×45
radio. The tray is tilted back about the pitch axis by `tilt` after assembly. In
desk mode a wedge foot (built from an extruded triangular profile) props the
cradle at a bench angle; in phone mode a back post carries a shallow **phone
clip** C-channel sized to `phone_w`/`phone_t`.

## Presets

- **Full-Size Tray** — standard hand tray with a strap loop.
- **Simulator Desk Stand** — angled bench stand for sim / setup.
- **Telemetry Phone Tray** — tray with a phone clip for telemetry / video.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Radio Cradle** (`pocket`, *internal*) — the radio-body pocket, defined by
    `radio_w`, `radio_d`, `radio_clear`, `wall`.
  - **Phone Clip** (`profile`, *internal*) — the phone-gripping C-channel,
    defined by `phone_w`, `phone_t`.
- **Material awareness:** `tolerance_by_material` is declared — the cradle
  clearance and wall are exposed so grip and stiffness can be tuned per material.
- **Societal benefit:** long flying and simulator sessions strain wrists, and
  OEM trays cost more than the plastic they use; an on-demand tray sized to the
  exact radio carries the weight on a strap, angles the screen, and holds a
  telemetry phone.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build; the final solid is
  assigned to `result`. Fillets are clamped and guarded. All modes render
  **watertight** in well under 20 s.
