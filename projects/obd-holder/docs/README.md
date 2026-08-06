# OBD-II / Fuse Tap Holder

Under-dash organisers for vehicle electronics, generated with **CadQuery**
(B-Rep): a cradle that holds an OBD-II diagnostic dongle out of the footwell, a
block that stores spare blade fuses and fuse taps, and a panel bracket with the
trapezoidal SAE J1962 connector opening for relocating the diagnostic port.
Sized to real OBD-II and ATO/ATC/Mini blade-fuse footprints.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> Under-dash parts should be printed in a **heat-tolerant material** (PETG/ASA);
> a car interior gets hot.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Dongle Cradle** | `dongle_holder` | A pocket cradle sized to an ELM327-class OBD-II dongle body, with a strap slot and screw ears. |
| **Fuse Organizer** | `fuse_organizer` | A block with a row of ATO/ATC wells and a row of Mini wells to store spare blade fuses and taps. |
| **OBD Panel Bracket** | `obd_bracket` | A mounting plate with the SAE J1962 trapezoidal connector opening and screw holes, to relocate the OBD-II port. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| OBD Dongle | `dongle_w` | 48.0 mm | Dongle body width (ELM327-class ~48 mm; varies). |
| OBD Dongle | `dongle_h` | 25.0 mm | Dongle body height. |
| OBD Dongle | `dongle_d` | 24.0 mm | Dongle body depth. |
| OBD Dongle | `wall` | 2.6 mm | Cradle / block wall thickness. |
| OBD Dongle | `clearance` | 0.5 mm | Per-side slip gap in the dongle and fuse wells. |
| Mounting | `obd_w` | 25.0 mm | J1962 trapezoid width (~25 mm wide side). |
| Mounting | `obd_h` | 13.0 mm | J1962 trapezoid height (~13 mm). |
| Mounting | `screw_d` | 4.2 mm | Mounting screw clearance (M4). |
| Fuses | `ato_count` | 4 | ATO/ATC wells (body 19.1 mm, blade pitch 9.5 mm). |
| Fuses | `mini_count` | 4 | Mini (APM/ATM) wells (body 10.9 mm, pitch 5.1 mm). |

## Presets

- **ELM327 Dongle Cradle**.
- **ATO + Mini Fuse Box**.
- **OBD-II Relocation Bracket**.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **OBD-II Connector Pocket** (`pocket`, "SAE J1962") — the dongle pocket and
    the connector-face opening, defined by `obd_w`, `obd_h`, `dongle_w`,
    `dongle_d`. Every car since 1996 shares the J1962 connector geometry.
  - **Blade Fuse Pocket** (`pocket`, "ISO 8820-3 ATO/Mini") — the fuse wells,
    defined by `ato_count`, `mini_count`.
- **Material awareness:** `tolerance_by_material` is declared.
- **Societal benefit:** tidies a dangling scan tool and loose spare fuses (a
  footwell hazard) from printed parts and standardises on the OBD-II geometry
  every car already shares.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
- Watertight strategy (the pocket rule): each holder is a solid block with pockets
  cut down from the top face (open to outside → vented, no trapped void). Fuse
  wells overshoot the top on a clean rim and leave a solid floor; the OBD bracket
  is a solid plate with a trapezoidal through-opening and through screw holes.
  The pocket-wall pitch grows with clearance so wide wells never merge.
- All shipped presets and defaults render **watertight**, single-body.
