# Snap Electrode Carrier

A printable **carrier disc for a standard 10 mm ECG/EMG snap stud** used as a textile
electrode contact. Generated with **CadQuery** (B-Rep).

A sensing garment — a chest strap, an EMG sleeve, a biofeedback vest — needs its snap to
sit on a rigid, flat, sewable island. Without one the stud tilts against skin every time
the lead is tugged and the conductive-fabric patch under it loses even contact, which shows
up as baseline wander in the signal. This carrier is that island: a shallow disc with a
sew-hole ring, a central bored boss, and an underside pocket that seats the fabric patch.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Bridge to the `sew-on-snap` family

`sew-on-snap` prints the **snap itself** — a stud disc and a socket disc that close a
placket. This cartridge prints **no snap at all**. It prints the carrier that a bought
**metal** 10 mm snap stud is set into, because a sensing contact has to be metal: printed
plastic cannot carry a biosignal, and the whole clinical snap-lead ecosystem is built on
the 10 mm flange. So the two cartridges are complements, not alternatives:

- Need a **closure**? Print `sew-on-snap` and you are done — no bought hardware.
- Need a **contact**? Print this carrier, buy a 10 mm stud, set it through the bore.

`stud_flange` (default 10.0 mm) is the parameter that keeps this carrier compatible with
the standard lead. Change it only if you are matching a non-standard stud.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Carrier Disc** | `carrier` | The disc alone: bored boss, fabric pocket, stitch ring. |
| **Carrier + Retaining Ring** | `carrier_lid` | Carrier plus the annulus that traps the fabric patch edge — two bodies. |
| **Electrode Pair Set** | `set` | Two carriers and two rings on one plate; a bipolar channel needs a pair. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Disc | `disc_dia` | 22.0 mm | 14–45 | Disc OD. Auto-raised to `stud_flange + 8` so a sewing rim survives. 20–24 mm chest strap, 30 mm+ EMG sleeve. |
| Disc | `disc_t` | 2.4 mm | 1.4–5.0 | Disc thickness. Thicker resists stud tilt under a snapped-on lead. |
| Snap Stud | `stud_shank` | 4.2 mm | 2.0–8.0 | Shank diameter — sets the through bore. A standard 10 mm medical stud is 3.9–4.3 mm. |
| Snap Stud | `stud_flange` | 10.0 mm | 6.0–16.0 | Flange diameter — sets the counterbore so the flange sits flush. **10 mm is the standard.** |
| Snap Stud | `boss_h` | 2.0 mm | 0.8–5.0 | Boss height above the disc face; lifts the snap clear of a thick shell. |
| Sewing | `sew_holes` | 6 | 4–10 | Stitch holes on the rim ring. |
| Sewing | `hole_dia` | 1.6 mm | 1.0–2.5 | Stitch hole diameter; auto-clamped to the rim band. |

## Assembly

1. Print the carrier (and the ring, if you want the patch retained mechanically).
2. Cut a conductive-fabric patch to the **pocket diameter** — silver-plated knit or
   stainless-blend jersey both work and both survive a wash.
3. Lay the patch into the underside pocket, push the metal snap stud's shank up through
   the patch and the carrier bore, and set the stud against its counterbore with a snap
   press or a hand setter.
4. Drop the retaining ring into the pocket over the patch edge if you printed one, then
   sew the carrier onto the garment through the rim holes with the patch facing skin.

## Print notes

Print **flat, boss up** — no supports. The underside pocket bridges over open air across
`pocket_dia` and prints fine at 0.2 mm layers; the fabric patch hides the bridge anyway.
PETG at 0.15 mm layers, 4 perimeters, 40 % infill. Avoid PLA if the garment gets washed
warm — the boss is the part that creeps. Every mode exports watertight: the shank bore and
the counterbore both overshoot their faces, the pocket opens downward and drains, and the
disc is chamfered on a clean blank before any cut.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Sewn Rim Face** (`flange`, internal) — **the sewn flange for the dimensional
    handshake**: the stitch ring that lands on the garment, defined by `disc_dia`,
    `sew_holes`, `hole_dia`.
  - **10 mm Snap Stud Bore** (`socket`, internal) — the bought-hardware interface, defined
    by `stud_shank`, `stud_flange`, `boss_h`.
  - **Conductive-Fabric Pocket** (`pocket`, internal) — the patch seat, defined by
    `stud_flange`, `disc_dia`, `disc_t`.

## Fashion Cabinet bridge

Expected FC consumers: **chest straps** and **heart-rate bands**, **EMG sleeves** and
**compression sensing garments**, **biofeedback vests**, and any FC garment whose electrode
notion needs a contact island rather than a closure.

FC-side `hardware_ref` block on the electrode notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "snap-electrode-carrier",
      "linked": true,
      "params_map": {
        "disc_dia": "electrode_contact_dia_mm + 8",
        "disc_t": "shell_fabric_thickness_mm + 1.6",
        "stud_shank": "4.2",
        "stud_flange": "10.0",
        "boss_h": "shell_fabric_thickness_mm + 1.0",
        "sew_holes": "6",
        "hole_dia": "1.6"
      }
    }
  }
}
```

The mating geometry is sized by **`disc_dia`** together with **`sew_holes` and `hole_dia`**
— that is the footprint and stitch pattern FC's notion places on the garment panel. The
garment's intended electrode contact area is the driving dimension. `stud_shank` and
`stud_flange` come from the bought snap standard and should stay at 10 mm, not be driven by
the garment.

`CERN-OHL-W-2.0`.
