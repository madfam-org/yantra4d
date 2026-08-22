# Size Marker Ring

The printable **rack size divider** — generated with **CadQuery** (B-Rep). A
C-ring that springs over a closet or shop rail and carries a size label on a tab
below it.

A rail of mixed stock reads at a glance with dividers on it, and goes back in
order after a customer has been through it. Without them it is a rail people give
up on — which is how second-hand and repaired clothing loses to new.

The label is **debossed**, cut into the tab, never raised. A proud character on a
rack divider catches knitwear, and a rack divider that snags a jumper is worse
than no divider.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Labelled Divider** | `ring` | One divider with the selected size cut into both faces of the tab. |
| **Blank Divider** | `blank` | The same ring with no text — for hand-marking, or for a size the select list does not carry. |
| **Set of Three** | `set` | Three dividers on one plate, so a size run prints in one job. Three separate bodies. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Rail | `rod_dia` | 32 mm | Rail outside diameter. **19** and **25 mm** are shop hanging rails, **32 mm** a timber closet dowel. Bore adds 0.5 mm clearance. |
| Rail | `mouth_pct` | 62 % | Snap-mouth width as a fraction of the rail. 60–70 % holds firmly in PETG; above 85 % it slips off, below 50 % a printed ring cracks going on. |
| Ring | `ring_t` | 5.0 mm | Radial wall — this is what springs. Thinner opens easily but fatigues; thicker grips harder but can crack on a tight mouth. |
| Ring | `ring_w` | 10 mm | Width along the rail. Wider keeps the divider square instead of cocking under the tab's weight. |
| Label | `tab_h` | 24 mm | Paddle drop below the rail. Must clear the shoulders of the hangers either side. |
| Label | `size_label` | `M` | Select: alpha **XXS–4XL**, US numeric **0–20**, waist/EU numeric **28–46**. |
| Label | `text_depth` | 0.9 mm | Deboss depth. Clamped to 40 % of `ring_t` so the tab never perforates. |

## Presets

- **Shop Rail 25 mm — M**
- **Closet Dowel 32 mm — L**
- **Waist Run (32) ×3** — the set mode.
- **Blank (hand-marked)**

## Print notes

Print **flat on the bed**, the ring lying in the XY plane with the tab beside it.
The mouth opening is the only overhang and it faces sideways in this
orientation — **no supports**. The tab's faces are the top and bottom surfaces, so
the debossed characters come out crisp with no bridging.

PETG. The ring is a spring: it has to open past the rail every time it is fitted,
and PLA at that strain snaps rather than springs. 0.15 mm layers, 3 perimeters,
25 % infill.

The mouth as printed is `mouth_pct` of the rail diameter. If a divider will not go
on, do not force it — raise `mouth_pct` by 5 and reprint, because a cracked C-ring
usually cracks at the tab root and takes the label with it. If dividers slide too
freely along the rail, that is normal and wanted: a divider should slide as stock
is added.

Fill the debossed characters with a paint pen for a rail read from across a shop
floor. At `text_depth` 1.0 mm and above the fill holds without a mask.

## Geometry notes

**Text is guarded.** Every deboss operation is wrapped in `try/except` with a
plain-ring fallback, and a label outside the allowed list is treated as blank
before it ever reaches a text operation. A font that fails to render must degrade
to a usable blank divider, never to a failed render. A cut that would remove
everything is also rejected.

Two defects were found and fixed while authoring this cartridge:

1. **Hand-built rounded-rect revolve profile.** Building the ring section from
   `threePointArc` segments with mid-points that were not actually on the arc gave
   a non-closed wire, and `revolve` returned a **zero-volume shell** rather than
   raising. The section is now a plain rectangle, with the rims softened by a
   guarded `.fillet()` on the **clean blank** — before the mouth cut, the tab
   union and the deboss, which is the only safe place for one.
2. **`revolve` axis frame.** The revolve axis is expressed in the *workplane's*
   frame, not the global one. A profile drawn on `"XZ"` and revolved about
   `(0, 0, 1)` silently produced the same zero-volume shell. The profile is now
   drawn on `"XY"`, revolved about the in-plane Y axis, and the resulting ring is
   rotated so its hole axis is Z.

The mouth is one oversized box cut placed entirely at Y > 0, so only the +Y arc is
opened and the −Y arc carrying the tab survives intact. The tab's top edge is
buried `ring_t * 1.2` inside the ring rather than butted to its inner face.
`set` combines the three dividers as a `cq.Compound`.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Rail Snap** (`snap`, internal) — the C-ring mouth springing onto the rod;
    defined by `rod_dia`, `mouth_pct`, `ring_t`.
  - **Label Face** (`surface`, internal) — the debossed size tab; defined by
    `size_label`, `tab_h`, `text_depth`.
  - **Rail Seat** (`socket`, internal) — the bore riding the rod; defined by
    `rod_dia`, `ring_w`.

The divider is **clipped** onto a rod, not sewn or threaded along an edge, so it
declares `snap` and `socket` rather than a flange-style edge interface — the same
distinction `sew-on-snap` draws between its stitched face and its snap
engagement.

## Fashion Cabinet bridge

FC records that consume this object: the **size-run** and **grading** records —
any FC garment carrying a `size_system` and a set of graded sizes — plus the
**retail-display** record that describes a shop's rails.

FC-side `hardware_ref` block on the size-run record:

```json
{
  "size_run": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "size-marker-ring",
      "linked": true,
      "per_size": true,
      "params_map": {
        "size_label": "size_code",
        "rod_dia": "display.rail_diameter_mm",
        "tab_h": "max(16, display.hanger_shoulder_drop_mm + 8)",
        "ring_w": "max(6, display.rail_diameter_mm * 0.3)"
      }
    }
  }
}
```

This is the one object on the shelf that FC drives **per size** rather than per
garment: `size_label` is bound to FC's own `size_code`, so a graded run in FC —
alpha or numeric, whichever `size_system` the record uses — emits one divider per
size with no hand-typing. `rail_diameter_mm` from FC's display record sizes the
`rail_snap` and `rail_seat` interfaces, and the hanger shoulder drop sets `tab_h`
so the tab hangs below the garments rather than behind them.

`CERN-OHL-W-2.0`.
