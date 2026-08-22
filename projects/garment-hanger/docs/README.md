# Garment Hanger

The printable **parametric clothes hanger** — generated with **CadQuery** (B-Rep).
A curved shoulder bar cut to a garment's own finished shoulder width, and a rod
hook sized to the rail it actually hangs on.

Shop-bought hangers exist in about two sizes. Everything that is not those two
sizes gets the shoulder bump that eventually retires the garment: a child's shirt
sagging off an adult hanger, a wide-shouldered coat pinched onto a shirt hanger.
This cartridge takes the shoulder span as a parameter, so the tips end just inside
the sleeve head where they belong.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Standard Hanger** | `standard` | Shoulder bar + rod hook. One solid. |
| **Notched** | `notched` | The same, with camisole/lingerie strap notches cut into both shoulders. |
| **Trouser Bar** | `body`, `bar` | Two parts: the notched shoulder body with pin sockets bored into its tips, plus a separate lower bar that plugs into them. |

`trouser_bar` is a genuine two-part mode — the platform renders `body` and `bar`
separately, and `main.py` dispatches on each part id.

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Shoulder | `shoulder_w` | 420 mm | Tip-to-tip span. 420–445 adult jacket, 400 shirt, 280–330 child. |
| Shoulder | `shoulder_t` | 12 mm | Front-to-back thickness. 14–20 mm is a suit hanger that supports a shoulder pad. |
| Shoulder | `shoulder_h` | 16 mm | Section height at the neck; tapers to 68 % of it at the tips. |
| Shoulder | `slope` | 38 mm | Tip drop below the neck. Clamped to 16 % of the span. |
| Hook | `hook_rod` | 32 mm | Rail diameter — 25 mm steel, 32 mm timber dowel. Adds 1.2 mm clearance. |
| Hook | `hook_wire` | 6 mm | Hook section. The whole load path: 6 mm a shirt, 8–10 mm a wet-wool coat. |
| Features | `notch_count` | 2 | Strap notches per shoulder (notched / trouser_bar only). |
| Features | `bar_drop` | 120 mm | How far the trouser bar hangs below the tips (trouser_bar only). |

## Presets

- **Shirt Hanger** — 400 mm, light section.
- **Suit Hanger** — 445 mm, 18 mm thick shoulder for a jacket's pad.
- **Camisole** — 380 mm with two strap notches per shoulder.
- **Child Size 4** — 300 mm.
- **Suit + Trouser Bar** — the two-part mode at suit proportions.

## Print notes — orientation matters here

Print the hanger **flat on its side**: the shoulder bar lies in the XY plane and
the hook lies in that same plane, so the whole part is one flat outline with no
overhang and **no supports**. This is not merely convenient — it is the only
orientation where the layers run along the hook's bending axis. Printed upright,
the hook is a stack of layers loaded in peel and it snaps at the first coat.

PETG or PLA at 4 perimeters and 30 % infill carries a shirt. A coat wants PETG,
ASA or nylon with `hook_wire` raised to 8 mm — the hook root and the neck are the
whole stress path. The trouser bar's pins are printed 0.25 mm under the socket
bore; if they are loose after printing, raise `shoulder_t` rather than reprinting
the bar, since the socket depth follows the shoulder section.

Every mode exports as one watertight solid (the `trouser_bar` mode as two, one
per part).

## Geometry notes

Three defects were found and fixed while authoring this cartridge, all worth
recording because they recur:

1. **Coincident stem and torus.** Placing the hook curl so its inner extreme sits
   exactly on the stem's axis makes the two tubes *coincident*, not overlapping.
   OCCT fuses them into a shape with a crack. The curl is shifted inboard by
   `hook_wire * 0.4` so the stem passes through real material.
2. **Tangent torus quadrants.** Assembling the curl from an upper half and a
   lower quarter has the two meeting along a single tangent circle — again a
   coincident surface. At `hook_wire` 9.5 mm the union came out as two detached
   bodies. The curl is now **one** torus with **one** quadrant cut away.
3. **Order-sensitive fuse.** `bar.union(stem).union(curl)` is watertight;
   `bar.union(stem.union(curl))` — identical geometry, pre-fused hook — is not.
   `_hook_pieces()` therefore returns the pieces unfused and `_add_hook()` folds
   them in one at a time.

The shoulder bar is a single `loft` over a chain of rounded-rect sections rather
than a stack of unions, and a strap notch is skipped automatically wherever the
shoulder slope leaves no safe land beneath it.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Shoulder Seat** (`profile`, internal) — the line the garment hangs on;
    defined by `shoulder_w`, `shoulder_t`, `shoulder_h`, `slope`.
  - **Rod Hook** (`custom`, internal) — the closet-rail engagement; defined by
    `hook_rod`, `hook_wire`.
  - **Strap Notch** (`pocket`, internal) — camisole strap capture; defined by
    `notch_count`, `shoulder_h`, `hook_wire`.
  - **Bar Socket** (`socket`, internal) — the tip pin joint carrying the trouser
    bar; defined by `shoulder_w`, `shoulder_t`, `bar_drop`.

None of these is a sewn edge, so none is declared as a flange-style edge
interface — a hanger is not stitched to anything. The garment couples to it
through the **Shoulder Seat** profile instead.

## Fashion Cabinet bridge

FC garments that consume this object: any **jacket**, **shirt**, **coat**,
**camisole** or **trouser** record — the hanger is display hardware for the whole
outerwear and top-weight shelf rather than for one notion.

FC-side `hardware_ref` block on the garment record:

```json
{
  "garment": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "garment-hanger",
      "linked": true,
      "params_map": {
        "shoulder_w": "shoulder_width_mm + sleeve_head_ease_mm",
        "slope": "shoulder_slope_deg * shoulder_width_mm / 90",
        "shoulder_t": "max(9, shoulder_pad_thickness_mm * 2.5)",
        "hook_wire": "min(10, 4 + garment_weight_g / 400)"
      }
    }
  }
}
```

The garment drives the hardware: FC's finished **shoulder width** sets
`shoulder_w` through the `shoulder_seat` interface, its **shoulder slope** sets
`slope`, and its **shoulder pad thickness** sets `shoulder_t` so the bar fills the
sleeve head instead of denting it. `bar_socket` is the interface FC uses when a
suit record wants its trousers hung with the jacket.

`CERN-OHL-W-2.0`.
