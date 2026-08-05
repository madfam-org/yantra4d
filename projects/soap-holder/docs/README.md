# Soap / Sponge Holder

A draining dish generated with **CadQuery** (B-Rep) for a bar of soap or a sponge.
The floor carries a lattice of drain holes so water runs out instead of pooling,
an optional front spout tips runoff toward the sink, and a wall-mount variant adds
a hook clip plus a suction-cup boss.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Dish** | `dish` | Freestanding drain tray. |
| **Wall Dish** | `wall_dish` | The tray with a hook clip and a suction-cup boss to hang on a rail. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Tray Size | `width` / `depth` / `height` | 100 / 75 / 22 mm | Tray X / Y / Z. |
| Tray Size | `wall` | 2.4 mm | Side wall + floor thickness. |
| Drainage | `drain_density` | 1.0 | Higher = more, smaller holes (0.5 sparse … 2.0 dense). |
| Drainage | `spout` | on | Notch the front rim to drain toward the sink. |
| Mounting | `mount` | freestanding | `freestanding` / `wall_clip` (dish mode). |

## Presets

- **Kitchen Sponge Tray** — 130×90×20, denser drainage, spout.
- **Bar Soap Dish** — 95×65×18, standard drainage, spout.
- **Shower Wall Dish** — 110×80×26 wall dish, dense drainage.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Drainage Lattice** (`surface`, internal) — the floor drain-hole field,
    defined by `drain_density`, `width`, `depth`, `wall`.
- **Material awareness:** `tolerance_by_material` declared.
- **Societal benefit:** keeps soap and sponges dry so they last longer and grow
  less mildew, replacing a cheap disposable dish with a right-sized printable one
  that drains where you want it.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Watertight by design:** the tray is a solid block hollowed to a bowl (floor
  intact), then drain holes are bored *completely through* the floor. Full
  through-cuts stay manifold — every preset and extreme renders watertight.
