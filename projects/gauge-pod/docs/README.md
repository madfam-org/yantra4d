# Gauge Pod

A parametric **aftermarket-gauge pod** generated with **CadQuery** (B-Rep). A
round gauge (boost, oil pressure, AFR, voltage…) drops into a standard **52 mm**
or **60 mm** socket; three mounting styles place that socket where the cabin
allows.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Vent Pod** | `vent_pod` | Gauge socket with two barbed clip tabs that spring into an air-vent. |
| **Pillar Pod** | `pillar_pod` | A tall A-pillar body with the gauge face raked toward the driver. |
| **Surface Pod** | `surface_pod` | A low puck on a wide flat flange for adhesive dash/console mounting. |

The studio dispatches the active part via `target_part`; each mode renders a
distinct body around the shared gauge socket.

## Gauge standards

| `gauge_dia` | Socket bore | Typical body depth |
| :--- | :--- | :--- |
| `52mm` | 52.5 mm | 30 mm |
| `60mm` | 60.5 mm | 32 mm |

The bore carries a small printable seating clearance over the nominal diameter,
and a front **bezel ring** (`face_ring`) narrows the opening so the gauge face is
captured instead of falling through.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Gauge Socket | `gauge_dia` | `52mm` | 52 or 60 mm gauge. |
| Gauge Socket | `wall` | 3.0 mm | Wall around the socket. |
| Gauge Socket | `face_ring` | 4.0 mm | Front lip that captures the gauge face. |
| Pod Body | `back_depth` | 34.0 mm | How deep the socket cups the gauge. |
| Vent Clip | `vent_tab_w` / `vent_tab_len` | 18 / 26 mm | Clip tab width / reach (Vent mode). |
| Pillar | `rake_deg` | 22° | Gauge face tilt toward the driver (Pillar mode). |
| Pillar | `pillar_h` | 70.0 mm | A-pillar body height (Pillar mode). |
| Pod Body | `base_pad` | 10.0 mm | Adhesive flange width (Surface mode). |

## Presets

- **52 mm Boost — Vent** — a boost gauge clipped into a vent.
- **60 mm AFR — Pillar** — a 60 mm AFR gauge raked 25° on the A-pillar.
- **52 mm Volt — Surface** — a voltmeter on an adhesive surface puck.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Gauge Bore** (`socket`, 52mm/60mm gauge) — the universal round socket that
    every pod presents, defined by `gauge_dia`, `back_depth`, `face_ring`, `wall`.
    Any standard gauge seats in any mounting style.
  - **Air-Vent Clip** (`snap`, internal) — the sprung barbed tabs of the vent
    pod, defined by `vent_tab_w`, `vent_tab_len`, `wall`.
- **Material awareness:** the seating clearance on the bore tunes the gauge fit
  per material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** aftermarket gauges converge on two socket sizes; a
  printable pod adapts that universal gauge to whatever cabin surface a car
  offers, so a working gauge need not be scrapped when a proprietary pod is
  discontinued.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The socket, bezel ring, clip tabs and flange are unioned solids and the bore
  overshoots the front face, so every shipped preset renders **watertight**.
