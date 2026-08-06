# Hitch Plug Holder

A parametric **trailer-plug holder** generated with **CadQuery** (B-Rep). It
stows a trailer wiring connector when it isn't plugged in, so it doesn't drag on
the ground or corrode. Supports the two dominant **SAE J1128** connectors: the
flat 4-pin and the round 7-pin.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Plug Holder** | `plug_holder` | A bolt-on bracket with a cup that cradles the plug body — its parking spot. |
| **Dust Cap** | `dust_cap` | A shallow cap that slips over the connector to seal the pins, with an optional tether tab. |
| **Socket Mount** | `socket_mount` | A bolt-down panel with a pass-through (and collar) that fixes the vehicle-side socket. |

The studio dispatches the active part via `target_part`; each mode presents the
same plug-body envelope on a distinct body.

## Plug standards

| `plug` | Body | Cupped envelope | Depth |
| :--- | :--- | :--- | :--- |
| `4-pin flat` | flat rectangular | 24 × 10 mm | 22 mm |
| `7-pin round` | cylindrical | Ø 44 mm | 28 mm |

A per-side `clearance` is added to the nominal body so the fit prints cleanly;
`socket_depth` overrides the cup depth (0 = auto from the plug).

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Plug Type | `plug` | `4-pin flat` | 4-pin flat or 7-pin round. |
| Fit & Walls | `wall` | 3.0 mm | Holder / cap wall thickness. |
| Fit & Walls | `clearance` | 0.6 mm | Per-side gap around the plug body. |
| Fit & Walls | `socket_depth` | 0 (auto) | Cup depth; 0 auto-sizes to the plug. |
| Mounting | `bracket_h` | 34.0 mm | Bolt bracket height (Holder mode). |
| Mounting | `bolt_dia` | 6.5 mm | Bolt clearance hole (Holder / Socket). |
| Mounting | `tether_hole` | on | Lanyard hole on a side tab (Cap mode). |

## Presets

- **4-Pin Flat — Holder** — a bolt-on parking cup for the flat connector.
- **7-Pin Round — Dust Cap** — a tethered cap for the round connector.
- **7-Pin Round — Socket Mount** — a panel mount with a collar for the socket.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Trailer Plug Body** (`socket`, SAE J1128 4/7-pin) — the plug-body envelope
    every mode presents, defined by `plug`, `clearance`, `socket_depth`, `wall`.
    The same holder family fits either standard connector.
  - **Hitch Bolt Mount** (`bolt_pattern`, internal) — the bracket bolt holes,
    defined by `bolt_dia`, `bracket_h`.
- **Material awareness:** the seating clearance tunes the plug fit per
  material/printer; `tolerance_by_material` is declared.
- **Societal benefit:** a trailer plug left dangling drags, fills with road grime
  and corrodes its pins; a printable holder, cap, and socket mount sized to the
  two standard SAE connectors keep the connection clean and off the ground for a
  few grams of filament instead of a proprietary bracket kit.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- The script is **self-contained** (sandbox-safe): parameters are read via a
  `PARAM(lambda: name, default)` guard because the render sandbox does not expose
  `globals()` / `eval`. The final solid is assigned to `result`.
- The cup bore overshoots the open face and the bolt bracket **overlaps into the
  cup body** (a solid merge rather than a tangent join), so every mode and preset
  — both plug types — renders **watertight**.
