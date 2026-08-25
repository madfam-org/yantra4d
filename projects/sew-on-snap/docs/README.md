# Sew-On Snap

A printable **sew-on snap fastener** — the stud-and-socket disc pair stitched through
rim holes onto baby-bodysuit crotch plackets, varsity plackets, and lightweight closures.
Generated with **CadQuery** (B-Rep). Fashion Cabinet's `sew-on-snap` notion owns the
fashion semantics (placket placement and spacing) and bridges to **this** solid for the
hardware.

Distinct from `snap-fit`, which is an engineering cantilever snap, not a garment finding.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Snap Set (stud + socket)** | `set` | Both discs laid out side by side with a computed gap. |
| **Stud Disc** | `stud` | The disc carrying the central boss. |
| **Socket Disc** | `socket` | The disc with the central recess and entry chamfer. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Disc | `snap_dia` | 12.0 mm | 7–30 | Disc outside diameter. 9–12 mm bodysuit, 15–20 mm varsity. |
| Disc | `disc_t` | 2.0 mm | 1.2–4.0 | Flat disc body thickness. |
| Engagement | `stud_dia` | 4.0 mm | 2.5–8.0 | Central boss diameter; clamped to `snap_dia − 4` so a sewing rim survives. |
| Engagement | `engage_clear` | 0.3 mm | 0.1–0.6 | Diametral stud/socket gap. Raise it for stiff filaments. |
| Sewing | `sew_holes` | 4 | 3–8 | Stitch holes on the polar rim ring. Four is the industry standard. |
| Sewing | `hole_dia` | 1.5 mm | 1.0–2.5 | Stitch hole diameter; auto-clamped to fit the rim band. |

## Print notes

Print **flat on the disc face**, stud up — no supports needed. PETG or recycled PETG
holds the snap action best; PLA works but the stud crown wears after repeated cycles.
0.15 mm layers, 4 perimeters, 40 % infill. If the pair engages too tightly after
printing, reprint the socket with `engage_clear` one step higher rather than filing the
stud. Every mode exports watertight; sew holes cut clean through both faces.

## Fashion Cabinet bridge

The FC-side notion carries:

```json
"hardware_ref": {
  "platform": "yantra4d",
  "project_slug": "sew-on-snap",
  "linked": true,
  "params_map": {
    "snap_dia": "placket_width_mm * 0.55",
    "disc_t": "shell_fabric_thickness_mm + 1.2",
    "stud_dia": "placket_width_mm * 0.20",
    "engage_clear": "0.3",
    "sew_holes": "4",
    "hole_dia": "1.5"
  }
}
```

The **`sew_face`** CDG interface (`flange`, parameters `snap_dia`, `sew_holes`,
`hole_dia`) is the sewn/set flange for the dimensional handshake — FC drives the finished
placket dimension into `snap_dia` and the stitch pattern follows. The **`stud_engage`**
interface (`snap`, parameters `stud_dia`, `engage_clear`) is the internal mating contract
between the two discs and is not FC-driven beyond material tolerance.

`CERN-OHL-W-2.0`.
