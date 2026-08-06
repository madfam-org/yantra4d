# Robot Sensor Mount

A **tilt-adjustable bracket for a small robot sensor board**, generated with
**CadQuery** (B-Rep). The board plate carries the **exact mounting-hole pattern**
of the sensor plus a window that clears the sensor / lens, on a pillar with an
adjustment slot so the board can be angled and locked.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Sensor table

| Sensor | Board | Holes | Window |
| :--- | :--- | :--- | :--- |
| VL53L0X ToF | 13 x 25 mm | 2 × M2 (0, ±9.5) | 5 x 5 mm aperture |
| MPU6050 IMU | 21 x 15 mm | 2 × M3 (±8.5, 0) | — |
| Pi Camera | 25 x 24 mm | 4 × M2 (±10.5 × ±6.25) | 9 x 9 mm lens |

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **ToF Mount** | `tof_mount` | A VL53L0X time-of-flight board plate (2 holes, small aperture) on the tilt pillar. |
| **IMU Mount** | `imu_mount` | An MPU6050 IMU board plate (2 holes) on the tilt pillar. |
| **Camera Mount** | `cam_mount` | A Raspberry Pi camera board plate (4 holes on 21 x 12.5 mm) with a lens window, on the tilt pillar. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Sensor | `sensor` | VL53L0X | Echoes the mode's board footprint. |
| Plate | `plate_t` | 3.0 mm | Board-plate thickness. |
| Plate | `margin` | 4.0 mm | Material margin around the holes. |
| Tilt | `tilt_deg` | 20° | Board rake angle. |
| Tilt | `ear_h` | 22 mm | Pillar height. |
| Tilt | `base_len` / `base_t` | 30 / 4 mm | Base foot length / thickness. |
| Tilt | `mount_d` | 4.5 mm | Base surface bolt (M4). |
| Tilt | `pivot_d` | 3.4 mm | Tilt / adjustment-slot bolt (M3). |

## The board footprint (why it fits)

Each sensor breakout has its own **mounting-hole pattern** — 2 holes for the
VL53L0X and MPU6050, 4 holes on 21 x 12.5 mm for the Pi camera — and the ToF /
camera also need an unobstructed **window** for the emitter/lens. The board plate
cuts the exact hole pattern and window for the mode's sensor, so the module bolts
straight on and can see. The plate mounts to a central pillar (both centred on
Y=0 so they bond into one solid) that carries a vertical **adjustment slot**; the
plate is raked by `tilt_deg`. The base foot is filleted **as a clean blank before**
its holes are cut, so every mode is watertight by construction.

## Presets

- **VL53L0X Tilted** — rangefinder aimed slightly down.
- **MPU6050 Upright** — IMU held flat/vertical.
- **Pi Cam 30°** — camera raked for a forward-down view.

## Hyperobject Profile

- **Domain:** industrial
- **CDG interfaces:**
  - **Sensor Board Mount** (`bolt_pattern`, *VL53/MPU6050/Pi-cam*) — the board
    hole pattern + window, defined by `sensor`, `margin`. Matches the module's PCB.
  - **Base Mount** (`bolt_pattern`, *internal*) — the base surface / tilt-slot
    holes, defined by `mount_d`, `pivot_d`, `base_len`.
- **Material awareness:** `tolerance_by_material` is declared — hole clearances can
  be tuned per material.
- **Societal benefit:** a printed mount cut to the board's exact hole pattern, with
  a tilt slot, aims any of the common cheap sensor breakouts without a custom
  bracket per build.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name,
  default)`; `target_part` dispatches which part to build (and fixes the sensor);
  the final solid is assigned to `result`. All modes render **watertight**.
