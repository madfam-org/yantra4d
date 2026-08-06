# Firestarter / Ferro Handle

Ergonomic handles and striker holders for **bare ferrocerium fire rods**,
generated with **CadQuery** (B-Rep). Bare ferro rods ship as plain metal in two
common diameters — **6 mm** and **8 mm** — with no grip. One rod-diameter
interface sockets the rod into a comfortable ribbed handle, a flat scraper/striker
holder that stores rod and striker as one tool, or a compact keychain toggle.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Ferro Rod Handle** | `rod_handle` | A round ribbed grip that sockets the rod in its top end (blind bore from the end face), with a lanyard hole through the base and a grub-screw hole that locks the rod. |
| **Striker / Scraper Holder** | `striker_holder` | A flat grip that clamps a striker (a 90°-spine scraper or hacksaw blade) in an obround end slot, with a ferro-rod socket on the opposite end so rod and striker store together. |
| **Keychain Fire Toggle** | `combo_toggle` | A compact barrel that sockets a short ferro rod and carries a cross lanyard bore — a zipper-pull / keychain fire bit. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Ferro Rod & Fit | `rod_d` | 8.0 mm | Ferro rod diameter. Common sizes are 6 mm and 8 mm. |
| Ferro Rod & Fit | `fit` | 0.3 mm | Added to the rod diameter for a press / grub-screw fit. |
| Ferro Rod & Fit | `socket_depth` | 20.0 mm | How deep the rod seats into the socket. |
| Grip | `wall` | 4.0 mm | Wall around the rod socket. |
| Grip | `grip_len` | 75.0 mm | Overall handle length (`rod_handle`, `striker_holder`). |
| Holes & Locks | `grub_d` | 3.2 mm | Cross hole to lock the rod / striker (M3 ~3.2 mm). |
| Holes & Locks | `lanyard_d` | 5.0 mm | Through hole for a lanyard or cord. |

## Why the rod diameter is the interface

The socket is bored `rod_d + fit`, so a single rod-diameter value fits genuine
6 mm or 8 mm ferro rods across all three parts. Set `fit` low for a friction
press-fit or leave it at 0.3 mm and lock the rod with an M3 grub screw through the
`grub_d` cross hole. The socket is a blind bore drilled from an exterior **end
face**, so it opens to that face (it vents — no trapped void) while leaving a
solid floor behind the rod.

## Presets

- **8 mm Rod Handle** — the common survival rod in a full 75 mm grip.
- **6 mm Striker Holder** — a scraper handle for the smaller rod, rod + striker in one.
- **Keychain Fire Toggle** — a short 6 mm toggle for a zipper pull.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Ferro Rod Socket** (`socket`, *6/8mm ferro rod*) — the rod grip interface,
    defined by `rod_d`, `fit`, `socket_depth`. Any part built to the same rod
    diameter shares rods across the kit.
  - **Grub-Screw Lock** (`bolt_pattern`, *ISO 4026 M3 set screw*) — the cross
    hole that locks the rod, defined by `grub_d`.
- **Material awareness:** `tolerance_by_material` is declared — `fit` and the
  socket dimensions are exposed so the rod fit tunes per material and printer.
- **Societal benefit:** a ferro rod is the most reliable flame-free fire source,
  but bare rods have no grip and are dropped or lost with cold hands. A printable
  handle sized to the 6 mm / 8 mm rod standard restores control and stores the
  rod with its striker, keeping a fire kit usable and repairable anywhere.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Each part is **one solid**: the rod socket is a blind bore from an exterior end
  face (open to that face → vented); the lanyard, grub-screw and striker-clamp
  holes are through-bores; the striker slot is an obround (`slot2D`) through cut;
  finger ribs are unioned rings. Fillets are applied to clean blanks before
  feature cuts and wrapped in try/except. All shipped modes and presets — and the
  parameter extremes — render **watertight** (`body_count == 1`) in well under
  20 s.
