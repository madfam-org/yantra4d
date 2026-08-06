# Yarn / Cone Guide

Guides and tensioners that **feed yarn smoothly off a cone or ball** for
knitting, crochet and weaving, generated with **CadQuery** (B-Rep). The
functional interface is a cone-base **socket** plus a smooth-lipped **eyelet**.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cone Stand** | `cone_stand` | A tapered cone seat on a disc foot with a tall arm carrying a top eyelet — yarn draws off the cone tip up through the eyelet. |
| **Tension Gate** | `tension_gate` | A flat wall/table plate with a row of eyelets and a pinch slot; threading through the eyelets evens the feed tension. |
| **Table Eyelet** | `table_eyelet` | A low bracket with one large flared eyelet that redirects yarn at a table edge without friction. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Cone Seat | `base_dia` | 50.0 mm | Yarn-cone base diameter — the seat is sized to it. |
| Cone Seat | `taper` | 6° | Seat-wall taper to match the cone flare. |
| Eyelet | `eyelet_d` | 8.0 mm | Bore of the smooth eyelet the yarn threads through. |
| Cone Seat | `arm_h` | 90.0 mm | Height of the eyelet arm above the cone. |
| Body | `wall` | 4.0 mm | Plate / seat / body wall thickness. |
| Eyelet | `eyelets` | 4 | Eyelet count across the tension gate. |

## How it works

Yarn drawn straight off a cone twists and pulls unevenly. The **cone seat**
cradles the cone by its base taper; yarn peels off the **tip** and rises to an
**eyelet** directly above the centre, so it never rubs the cone edge. The eyelet
lip is chamfered so plied and fuzzy yarns glide through. The tension gate strings
several eyelets in series (an amateur creel) to hold steady feed tension, and the
table eyelet is a single flared redirect for a cone parked beside the work.

## Presets

- **Small Cone Stand** — sized for a 50 mm hobby cone.
- **4-Eyelet Tension Gate** — a wall-mounted even-feed guide.
- **Table-Edge Redirect** — a single flared eyelet at the table edge.

## Hyperobject Profile

- **Domain:** household
- **CDG interface:** **Cone Seat + Yarn Eyelet** (`socket`, *internal*) — the
  tapered cone seat and eyelet bore, defined by `base_dia`, `taper`, `eyelet_d`.
- **Material awareness:** none declared — the guide is friction-only geometry with
  no material-dependent fit.
- **Societal benefit:** yarn fed straight off a cone tangles and pulls unevenly;
  a printed stand and eyelet feed it under even tension, sized to whatever cone or
  ball the maker owns.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- The cone seat is a **blind pocket** bored from the open top (vented); eyelets
  are **through-holes** with chamfered/flared lips; the arm is a **solid** post
  unioned into the foot. No trapped voids. All modes render **watertight** and
  single-body.
