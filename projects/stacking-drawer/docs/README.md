# Stackable Drawer System

A small modular drawer unit generated with **CadQuery** (B-Rep). The carcass is
an open-front shell with side rails and a corner stacking interlock; the drawer
slides in on those rails with clearance on every side and carries a front handle.
Both parts are driven by the **drawer interior** dimensions plus the shared
clearance and rail geometry, so **the drawer that prints from this file always
fits the carcass that prints from it**.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Carcass** | `carcass` | Open shell: interior pocket, side rails, stacking pegs (top) + sockets (base). |
| **Drawer** | `drawer` | Sliding drawer sized to the pocket with `clear` per side, side grooves, front handle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Drawer Interior | `inner_w` / `inner_d` / `inner_h` | 100 / 120 / 45 mm | Usable drawer interior X / Y / Z. |
| Drawer Interior | `wall` | 2.0 mm | Wall thickness for both parts. |
| Slide & Fit | `clear` | 0.4 mm | Per-side gap between drawer and carcass. |
| Slide & Fit | `rail` | 3.0 mm | Side-rail size and matching drawer-groove size. |
| Stacking | `interlock` | 4.0 mm | Corner peg/socket size (0 = flat, no stacking). |

## Fit contract

The carcass interior pocket is derived as the drawer's **outer envelope**
(`inner + 2·wall`) plus `clear` on each side, with rail headroom above. The
drawer's sliding walls (width and height) and its body depth therefore always sit
inside the pocket by exactly the clearance. The oversized front face and handle
intentionally sit **outside** the opening — that is the drawer front. Verified by
bounding-box comparison across default / wide / loose / tight parameter sets:
the drawer sliding envelope clears the carcass pocket in width, depth and height
in every case.

## Presets

- **Desk Tray Drawer** — 120×150×35 shallow drawer.
- **Parts Cabinet Unit** — 80×100×50 carcass with stacking pegs.
- **Deep Drawer** — 140×180×100 with a larger rail.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Drawer Slide + Stack Interlock** (`rail`, internal) — the double interface.
    `inner_*`, `wall`, `clear` and `rail` define the slide (carcass rails ⇄ drawer
    grooves); `interlock` defines the top-peg / bottom-socket that lets carcasses
    stack and lock. Any drawer and carcass built at the same values interoperate.
- **Material awareness:** `tolerance_by_material` is declared so the slide
  clearance can be tuned per material/printer for a smooth but non-sloppy slide.
- **Societal benefit:** a printed-to-fit modular drawer system that stacks and
  locks — build exactly the small-parts cabinet a space needs, unit by unit.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- Both parts are closed solids; all shipped modes and presets export
  **watertight**.
