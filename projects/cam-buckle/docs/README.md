# Cam Buckle

The printable **lever-cam strap lock** — generated with **CadQuery** (B-Rep). The tape runs
under a toothed cam lever and over a fixed anvil bar: pull the tape and the cam rides up
and lets it through, let go and the load rotates the cam down onto the tape and locks it.
Squeeze the lever to release. Two parts on one pin. Fashion Cabinet's `cam-buckle` notion
owns the fashion semantics (strap routing and dead-end placement) and bridges to **this**
solid for the hardware.

Distinct from its shelf siblings: `ladder-lock` and `tri-glide-slider` are friction
adjusters that hold by wrap alone; **this** one grips harder as the load rises, which is
what a tie-down needs.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Buckle Set (body + cam)** | `set` | Both pieces laid side by side with a print gap — two separate solids on one plate. |
| **Body (frame + anvil)** | `body` | Two side cheeks, the anvil bar, the webbing tail slot, and the pin bores. |
| **Cam Lever** | `cam` | The hub with its through bore, the eccentric ribbed lobe, and the thumb lever. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Webbing | `webbing_w` | 25.0 mm | 15–50 | Nominal tape width. The throat spans this + 1.5 mm. |
| Webbing | `webbing_t` | 1.6 mm | 0.8–4.0 | Tape thickness; sets the throat height and the tail slot. |
| Body | `cheek_t` | 3.0 mm | 2.0–6.0 | Side cheek thickness. The cheeks carry the pin — the first thing to fail if thin. |
| Cam | `pin_dia` | 3.0 mm | 2.0–6.0 | Pivot pin diameter. A printed rod, a cut nail or an M3 screw all work. |
| Cam | `cam_throw` | 3.0 mm | 1.2–6.0 | Lobe eccentricity — how far the cam swings toward the anvil. |
| Cam | `pin_clear` | 0.35 mm | 0.15–0.8 | Bore running clearance. Raise it if the lever binds after printing. |

## Presets

- **Tie-Down** — the 25 mm default.
- **Roof-Rack Strap** — 50 mm heavy section on a 5 mm pin.
- **Camera Sling** — 20 mm fine section on a 2.5 mm pin.

## Assembly

The two parts are **not** print-in-place — they meet on a separate pin. Print both, drop
the cam between the cheeks with its lobe facing the anvil, and push a 3 mm rod (printed,
a cut nail, or an M3 screw with a nut) through the aligned bores. The cam must swing
completely freely; if it drags, ream the cam bore rather than the cheek bores, since the
cheeks are what hold the pin captive.

## Print notes

Print **both parts flat on the bed** as they lie in `set` mode. The body's throat opens out
through both X ends, so nothing bridges. The cam prints on a flat cheek with its bore
horizontal — this is the correct orientation, because the lobe's grip load pushes across
the layers rather than peeling them apart. Nylon or PETG for anything load-bearing; a cam
buckle in PLA will shear its lobe ribs off the first time it takes a real tie-down load.
Five perimeters, 50 % infill, 0.15 mm layers.

Every mode exports watertight. The throat is an open-ended pocket (never a sealed void),
the anvil bar's centre is sunk below the throat floor so its union is a real overlap rather
than a tangent touch, and the cam's grip ribs are round-sectioned cylinders sunk into the
lobe — deliberately blunt, so they bite the weave without cutting the tape.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Webbing Throat** (`flange`, internal) — **the threaded tape edge for the dimensional
    handshake**: the channel between the cheeks the webbing runs through, plus the tail
    slot. Defined by `webbing_w`, `webbing_t`, `cheek_t`.
  - **Cam Pivot Bore** (`socket`, internal) — the pin joint between the two parts, defined
    by `pin_dia`, `pin_clear`.
  - **Cam Bite Face** (`profile`, internal) — the eccentric grip surface, defined by
    `cam_throw`, `webbing_t`.

## Fashion Cabinet bridge

FC garments and notions that consume this object: **luggage and pack compression straps**,
**detachable bag straps** whose length is reset with one hand, **apron and utility-belt
cinches**, and **outerwear waist and hem drawstring** notions built on flat tape rather
than cord.

FC-side `hardware_ref` block on the `cam-buckle` notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "cam-buckle",
      "linked": true,
      "params_map": {
        "webbing_w": "strap_width_mm",
        "webbing_t": "strap_thickness_mm",
        "cheek_t": "max(2.4, strap_width_mm * 0.12)",
        "pin_dia": "max(2.5, strap_width_mm * 0.12)",
        "cam_throw": "max(2.0, strap_thickness_mm * 1.8)",
        "pin_clear": "0.35"
      }
    }
  }
}
```

The garment drives the hardware twice over: the finished strap width flows into
`webbing_w` to size the throat, and the strap **thickness** flows into `cam_throw`, because
a thicker tape needs a longer cam swing to reach it. `webbing_throat` is the interface FC
uses for the dimensional handshake when routing the tape.

`CERN-OHL-W-2.0`.
