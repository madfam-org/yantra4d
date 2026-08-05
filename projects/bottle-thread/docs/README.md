# Bottle-Thread Cap & Coupler

Turns any discarded **PET bottle** into infrastructure. Generated with
**CadQuery** (B-Rep), this cartridge produces screw **caps**, bottle-to-bottle
**couplers**, and **spout adapters** whose functional interface is a *real
single-start helical thread* matched to standard bottle-neck finishes. A bottle
is the world's most abundant standardized vessel; the thread is the connector.

This is the **input side of the [Faircap](../faircap-filter) water-filter
ecosystem** — water sovereignty from plastic waste.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Screw Cap** | `cap` | Female thread on the selected neck; flat or domed top; optional grip knurl and vent hole. |
| **Bottle Coupler** | `coupler` | Female thread on **both** ends so two bottles join neck-to-neck. Second end can be a different standard (dissimilar / size-adapter coupler). |
| **Spout Adapter** | `spout_adapter` | Female bottle thread on the bottom, a reduced pour/squeeze nozzle on top — turns a bottle into a squeeze vessel. |

## Neck Standards

The `neck_standard` (and, for the coupler, `neck_standard_b`) select the
bottle-neck finish the part threads onto. Each option sets a dimensionally
sensible nominal major diameter and pitch:

| Standard | Use | Major Ø | Pitch | Nominal turns |
| :--- | :--- | :---: | :---: | :---: |
| **PCO-1881** *(default)* | Soda / water bottles — the most common finish | 27.4 mm | 2.7 mm | ~1 |
| **PCO-1810** | Same neck family, taller thread | 27.4 mm | 2.7 mm | ~1.5 |
| **28-410** | Personal-care / trigger-spray bottles | 28.0 mm | 3.18 mm | ~1.5 |
| **38-400** | Wide-mouth jars / large containers | 38.0 mm | 4.2 mm | ~1.25 |

The female thread bore is the male major diameter **plus `clearance` per side**,
so printed parts screw on despite tolerances.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Neck Standard | `neck_standard` | PCO-1881 | Finish this part threads onto. |
| Neck Standard | `neck_standard_b` | PCO-1881 | Second end of the coupler (set different for a dissimilar coupler). |
| Thread Fit & Walls | `clearance` | 0.4 mm | Per-side thread gap for a printable fit (0.3–0.5 typical). |
| Thread Fit & Walls | `wall` | 2.6 mm | Radial wall around the thread. |
| Thread Fit & Walls | `top_th` | 2.2 mm | Cap top / coupler central web thickness. |
| Thread Fit & Walls | `extra_turns` | 0.0 | Extra engagement turns beyond nominal (deeper grip, slower render). |
| Cap Options | `grip_knurl` | on | Vertical grip flutes around the cap. |
| Cap Options | `domed_top` | off | Rounded (tapered) top instead of flat. |
| Cap Options | `vent_hole` / `vent_dia` | off / 3 mm | Small hole through the cap top (straw / pressure relief). |
| Spout | `spout_dia` / `spout_len` | 9 / 22 mm | Nozzle bore and length. |

## Presets

- **Soda-Bottle Cap (PCO-1881)** — the everyday replacement cap.
- **Wide-Mouth Vented Cap (38-400)** — domed, 8 mm vent.
- **Bottle-to-Bottle Joiner** — same-neck coupler.
- **Size Adapter (PCO-1881 ↔ 38-400)** — dissimilar coupler joining two neck sizes.
- **Squeeze/Pour Spout (PCO-1881)** — bottle → squeeze vessel.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **PET Bottle Neck Thread** (`thread`, *PCO 1881 / SP-400 finish series*) —
    the functional screw interface, defined by `neck_standard`,
    `neck_standard_b`, `clearance`, and `wall`. Declared
    `compatible_with: [faircap-filter]`: a cap, coupler, or spout generated for a
    given neck mates with any Faircap housing (or bottle) of the same finish.
- **Material awareness:** the printed-thread fit is exposed as `clearance` so the
  screw fit can be tuned per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** the discarded PET bottle is the world's most abundant
  standardized vessel — printing to its neck thread lets anyone re-cap, join, or
  re-spout a bottle, the input interface for on-demand water filtration and
  storage without commercial dependency.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- **Threads are real, not cosmetic.** A trapezoidal profile is swept along a
  genuine helical path (`makeHelix`) for the neck's short ~1–2 turns. The rib's
  **root radius is pushed slightly into the surrounding wall material** so the
  boolean union is a clean volumetric merge rather than a fragile tangent kiss —
  which is what keeps the mesh **watertight**. A rib whose root sits exactly on
  the bore surface tessellates into cracks; the overlap fixes that. This keeps a
  default cap render fast (~1.4 s warm; ~5.6 s on the first render of a fresh
  process, which absorbs one-time CadQuery/OCCT initialization). All shipped
  presets and defaults render watertight.
- The **grip knurl** is a single polar-array cut and the **domed top** is a clean
  truncated-cone loft — both chosen over sphere/revolve variants that meshed with
  axis-pole artifacts, so every option stays watertight.
