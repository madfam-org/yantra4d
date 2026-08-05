# Bike Accessory Mount

A two-piece handlebar bolt clamp with a swappable accessory interface, generated
with **CadQuery** (B-Rep). The saddle is sized to the standard bar diameters and
the accessory side mates the ubiquitous action-cam / camera / strap interfaces.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **GoPro Mount** | `gopro_mount` | Clamp + a GoPro-style two-finger clevis (3.0 mm fingers, 5 mm pivot). |
| **1/4-20 Camera Mount** | `quarter20_mount` | Clamp + a 1/4-20 camera pad (cosmetic ~5.5 mm socket bore for a 6.35 mm screw). |
| **Strap / Tab Mount** | `strap_mount` | Clamp + a strap loop or a flat tab (`interface`). |

Each mode emits the clamp **base half plus its matching cap half** side by side, so
the whole clamp downloads as one printable pair joined by two bolts.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Handlebar | `bar_dia` | 22.2 | 22.2 / 25.4 / 31.8 mm saddle. |
| Accessory | `interface` | light | Strap loop or flat tab (Strap mode). |
| Accessory | `phone_w` | 70 mm | Flat-tab width. |
| Clamp | `clamp_w` | 16 mm | Grip width along the bar. |
| Clamp | `wall` | 4.0 mm | Material around the saddle. |
| Clamp | `bolt_dia` | 4.3 mm | Clamp bolt clearance (≈ M4). |
| Clamp | `grip_pad` | 0.3 mm | Saddle undersize for a firm clamp. |

## Interfaces (dimensional)

- **GoPro fingers:** thickness ~3.0 mm, gap ~3.2 mm, 5 mm pivot hole.
- **1/4-20 pad:** 6.35 mm nominal, printed as a cosmetic ~5.5 mm bore (no slow helix).
- **Strap loop / tab:** a thread-through slot or a flat mounting tab.

## Presets

- **Action-Cam on Grip Bar (22.2)** — GoPro clevis on a standard grip.
- **Camera on Oversized Bar (31.8)** — 1/4-20 pad on a 31.8 mm bar.
- **Light Strap Loop (25.4)** — a strap loop for a bike light.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interface:** **Handlebar Clamp** (`socket`, *ISO handlebar Ø 22.2/25.4/31.8*)
  — defined by `bar_dia` and `interface`. The clamp saddle mates any bar of the
  chosen diameter; the accessory interface mates standard camera/action-cam gear.
- **Material awareness:** `tolerance_by_material` — the clamp fit and `grip_pad`
  should be tuned per filament for a firm, non-slip grip.
- **Societal benefit:** mount any camera, light, phone, or gadget to any bike on
  demand instead of buying a proprietary bracket per device.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; final solid assigned to `result`.
- All shipped presets and defaults render **watertight**.
