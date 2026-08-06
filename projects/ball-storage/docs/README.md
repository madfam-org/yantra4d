# Sports Ball Wall Storage

A wall holder that cradles a sports ball off the floor, generated with **CadQuery**
(B-Rep). Sized by the ball diameter so the claw or ring hugs the ball at its
equator.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Claw Holder** | `claw_holder` | Back plate with 2-5 curved prongs cupping the ball. |
| **Ring Holder** | `ring_holder` | A single sloped ring the ball rests in. |
| **Double Holder** | `double_holder` | Two stacked ring cradles for two balls. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ball & Cradle | `ball_dia` | 240 mm | Ball diameter (basketball ≈ 240). |
| Ball & Cradle | `prongs` | 3 | Claw prongs (claw mode). |
| Ball & Cradle | `prong_w` / `prong_t` | 16 / 8 mm | Prong/ring width / thickness. |
| Plate & Mount | `wall` | 6 mm | Back plate thickness. |
| Plate & Mount | `plate_w` | 90 mm | Back plate width. |
| Plate & Mount | `screw_dia` | 5 mm | Wall screw clearance. |

## Presets

- **Basketball Claw** — 3-prong, 240 mm.
- **Soccer Ball Ring** — 220 mm ring.
- **Two-Ball Rack** — stacked double holder.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Ball Claw** (`surface`, internal) — the ball-cradling prong/ring surface,
    defined by `ball_dia`, `prongs`, `prong_w`, `prong_t`.
  - **Wall Mount** (`bolt_pattern`, internal) — the two-screw wall pattern,
    `plate_w`, `wall`, `screw_dia`.
- **Material awareness:** `tolerance_by_material` declared — cradle fit and prong
  stiffness adapt to the printed material.
- **Societal benefit:** balls roll around and get underfoot; a printable claw sized
  to any ball reclaims garage and gym floor space.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Prongs and rings root a few mm inside the back plate so every union is
  volumetric — each part exports as a single connected watertight body.
- Self-contained (sandbox-safe): parameters read via `PARAM(lambda: name, default)`;
  the final solid is assigned to `result`.
- All shipped presets render **watertight**.
