# Boot / Glove Dryer Manifold

Splits airflow from a fan, vent, or hair-dryer into several branches that push warm
air down into wet boots and gloves, generated with **CadQuery** (B-Rep). One inlet
leads into a plenum that fans out to N branch tubes; the ends can be plain open
tubes, flattened boot-shaped outlets, or the whole thing can carry a wall-mount plate.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Manifold** | `manifold` | Inlet + plenum + N open branch tubes. |
| **Boot Tree** | `boot_tree` | Branch tips flattened toward oval boot outlets. |
| **Wall-Mount** | `wall_mount` | Manifold on a flat back plate with screw holes. |

Each mode's `parts[]` id equals the `target_part` the code dispatches on.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Inlet | `inlet_dia` | 60 mm | Fan / duct diameter the inlet slips over. |
| Inlet | `inlet_depth` | 20 mm | Inlet socket engagement depth. |
| Branches | `branches` | 2 | Number of outlet tubes (2 = one pair of boots). |
| Branches | `branch_dia` | 38 mm | Outlet tube diameter. |
| Branches | `branch_len` | 70 mm | Outlet tube length. |
| Branches | `branch_ang` | 35° | Splay angle from vertical. |
| Shell | `wall` | 3.0 mm | Manifold shell wall thickness. |

## Presets

- **One Pair of Boots** — a 2-branch dryer for a single pair.
- **Boot Tree (flat)** — flattened outlets that seat inside boot shafts.
- **4-Glove Wall Rack** — 4 branches on a wall plate for gloves.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Duct Branch Manifold** (`socket`, internal) — the inlet-to-branches split,
    defined by `inlet_dia`, `branches`, `branch_dia`, `inlet_depth`. The inlet socket
    mates a standard fan/duct; branches mate boot/glove shafts.
- **Material awareness:** `wall` and inlet clearance tune per material/printer;
  `tolerance_by_material` is declared.
- **Societal benefit:** dry gear, warm hands — turns any small fan into a boot-and-
  glove dryer, preventing trench foot, blisters, and mildew in wet, cold climates.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- **Hollow-manifold method:** the plenum and inlet collar are built as one solid, N
  branch cylinders are unioned on (each rooted into the plenum with an `overlap` for a
  volumetric join), then a single combined interior void (plenum cavity + inlet bore +
  all branch bores) is cut **once**, so the whole shell exports **watertight**.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  final solid assigned to `result`.
