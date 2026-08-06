# Molecule / Atom Model Kit

A **ball-and-stick** molecular modelling set, generated with **CadQuery**
(B-Rep). Atoms are faceted balls bored with bond sockets at the **real VSEPR
bond angles**; bonds are struts that plug into any matching socket, so any atom
of a given geometry connects to any bond.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Atom** | `atom` | A ball with *N* bond sockets at a chosen geometry: tetrahedral (109.5°, 4), trigonal-planar (120°, 3), linear (180°, 2), bent (104.5°, 2) or octahedral (90°, 6). |
| **Single Bond** | `bond` | A straight strut with a reduced-diameter plug at each end that press-fits the socket. |
| **Double Bond** | `double_bond` | Two parallel plug struts joined by a central web — the π-bond / double-bond connector for C=C, C=O, etc. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Atom | `geometry` | tetrahedral | VSEPR geometry (socket count + angles). |
| Atom | `atom_dia` | 18.0 mm | Ball diameter. |
| Bond Socket | `socket_dia` | 4.0 mm | Bore the plug enters — the shared connector diameter. |
| Bond Socket | `socket_depth` | 6.0 mm | Socket depth (auto-capped to keep a solid core). |
| Bond | `bond_len` | 30.0 mm | Overall bond length (sets atom spacing). |
| Bond | `bond_dia` | 6.0 mm | Bond body strut diameter. |
| Bond | `plug_fit` / `plug_len` | 0.3 / 5.5 mm | Plug press-fit undersize and length. |
| Bond | `double_gap` | 7.0 mm | Twin-strut spacing of a double bond. |

## The interface (why every atom fits every bond)

The whole kit hinges on one **Common Denominator Geometry**: a cylindrical bond
socket of `socket_dia`. Every bond plug is turned to `socket_dia − plug_fit`, a
press fit, so any bond enters any socket. The atom's socket *directions* encode
the real chemistry — the tetrahedral set uses the four cube-diagonal directions
(exactly 109.47°), trigonal uses 120° in a plane, octahedral uses the six
±axis directions (90°), and so on — so a built molecule shows the correct shape.
Because the socket diameter is shared and material-tunable, a class grows one
compatible set indefinitely.

The atom is a **faceted ball** (a subdivided icosahedron), not a smooth sphere,
so that a socket bored at any oblique bond angle meets planar faces and stays
watertight — an oblique cylinder cut into a true sphere leaves a degenerate
sliver at the tangency point, which the faceted ball avoids entirely.

## Presets

- **Carbon sp³ (Tetrahedral)** — a 4-socket carbon atom.
- **Standard Single Bond** — the default strut.
- **C=C Double Bond** — a twin-strut double bond.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **Bond Plug / Socket** (`socket`, *internal bond socket*) — the cylindrical
    connector defined by `socket_dia`, `socket_depth`, `plug_fit`, `plug_len`;
    every atom accepts every bond.
  - **VSEPR Bond Angles** (`custom`, *VSEPR 109.5 / 120 / 180 / 90°*) — the
    socket *directions* selected by `geometry`, encoding real molecular shape.
- **Material awareness:** `tolerance_by_material` is declared — `socket_dia` and
  `plug_fit` are exposed so the friction fit tunes per material / printer.
- **Societal benefit:** physical ball-and-stick models make VSEPR angles,
  isomerism and chirality tangible; a shared socket lets a class build an
  unlimited compatible set from open files, and gives blind or low-vision
  students a tactile model of molecular structure.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Atoms are built as a subdivided-icosahedron polyhedron; sockets are oblique
  cylinder cuts that vent to the surface (open mouth) and stop short of centre
  (depth auto-capped) so opposite sockets never share a cavity. Bonds are solid
  cylinders with unioned plug tips; the double bond unions two struts to a
  central web. All shipped geometries and extreme-parameter cases render
  **watertight**, single-body.
