# Solar Light & Path Stake

Replaces the brittle plastic stakes that snap off cheap solar path lights.
Generated with **CadQuery** (B-Rep). A tapered ground spike carries a standardized
**Fixture Socket** that a light head, a reflective marker, or a sign plugs into.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Stake** | `stake` | Tapered ground spike + anti-rotation fins + seating flange + upward fixture socket. |
| **Light Housing** | `light_housing` | A cup that cradles a round solar/LED head, with a male stem that plugs into the stake socket. |
| **Marker Stake** | `marker_stake` | Ground spike + a flat sign paddle for numbers, plant labels, or reflectors. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ground Spike | `spike_len` | 120 mm | Buried spike length. |
| Ground Spike | `spike_dia` | 20 mm | Spike top diameter (tapers to a point). |
| Ground Spike | `fins` | 4 | Anti-rotation fins (0 = smooth). |
| Fixture Socket | `socket_dia` | 22 mm | Bore the fixture stem plugs into. |
| Fixture Socket | `socket_depth` | 25 mm | Plug-in depth. |
| Fixture Socket | `wall` | 3.0 mm | Socket / housing wall. |
| Fixture Socket | `clearance` | 0.4 mm | Per-side plug slop. |
| Head & Sign | `head_dia` | 58 mm | Solar head diameter (light housing). |
| Head & Sign | `head_h` | 30 mm | Head cup depth (light housing). |
| Head & Sign | `sign_w` | 60 mm | Sign paddle width (marker stake). |
| Head & Sign | `sign_h` | 90 mm | Sign paddle height (marker stake). |

## Presets

- **Path-Light Stake** — the durable replacement spike with socket.
- **Solar Head Cup** — the light-head carrier that plugs into it.
- **Plant Label Stake** — a short marker with a writable paddle.

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **Fixture Socket** (`socket`, internal) — the plug interface defined by
    `socket_dia`, `socket_depth`, `wall`, `clearance`. The stake's female socket and
    the light housing's male stem share it, so any fixture stem printed to this
    socket (light, reflector, sign clip) drops into any stake.
- **Material awareness:** `clearance` is exposed so the plug fit can be tuned per
  material and shrinkage; `tolerance_by_material` is declared.
- **Societal benefit:** solar path lights are landfilled en masse when their flimsy
  stakes snap even though the electronics still work — a durable printed stake with
  a shared socket keeps the light in service and doubles as markers and signs for
  shared paths and gardens.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. Fins and fillets are
  wrapped in try/except so extreme inputs still build watertight.
- All shipped presets and every mode render **watertight**.
