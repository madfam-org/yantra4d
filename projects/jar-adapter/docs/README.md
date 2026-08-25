# Wide-Mouth Jar Adapter

Cross-links the **mason-jar** family with the **PCO-1881** bottle family. Generated
with **CadQuery** (B-Rep). Screw the adapter onto a standard mason jar (70 mm
regular-mouth or ~83 mm wide-mouth continuous thread) and it presents a **PCO-1881
male stub** on top — so any PCO-1881 cap, coupler, or spout now fits a mason jar.
Also generates a plain mason sealing lid and a perforated sifter/shaker lid.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Jar → PCO Adapter** | `jar_to_pco` | Female mason-jar thread on the bottom, a PCO-1881 male stub on top, bored through. Screw onto a jar; screw any PCO-1881 cap/coupler/spout onto the stub. |
| **Mason Sealing Lid** | `jar_cap` | A plain sealed mason-jar lid with a grip skirt — replaces a lost or rusted metal mason lid. |
| **Sifter / Shaker Lid** | `jar_sifter` | A mason-jar lid whose top is perforated with concentric rings of holes, for spices, flour, seeds, or other dry goods. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Jar Thread | `jar_size` | 70mm | 70 mm regular-mouth (G70) or 86 mm wide-mouth (G86). |
| Jar Thread | `jar_turns` | 1.5 | Mason-jar turns (snapped to a half-integer internally). |
| Fit & Walls | `clearance` | 0.5 mm | Per-side jar-thread slop (coarse threads print looser). |
| Fit & Walls | `wall` | 3.0 mm | Radial wall around the jar thread. |
| Fit & Walls | `top_th` | 2.6 mm | Sealed top disk / adapter shoulder thickness. |
| PCO Stub | `pco_turns` | 3.5 | PCO-1881 male-stub turns (snapped to a half-integer internally). |
| PCO Stub | `pco_clearance` | 0.3 mm | Per-side undersize on the male stub so a printed cap threads over it. |
| PCO Stub | `bore_dia` | 18 mm | Transfer bore through the adapter. |
| Sifter Holes | `hole_dia` | 4 mm | Diameter of each sifter hole. |
| Sifter Holes | `hole_rings` | 3 | Concentric rings of holes. |

## Presets

- **Regular Jar → PCO** — the cross-family adapter on a 70 mm jar.
- **Wide-Mouth Sealing Lid** — a plain sealed lid on an 86 mm jar.
- **Regular Spice Sifter** — the perforated shaker lid.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **PCO-1881 Male Stub Thread** (`thread`, PCO 1881) — the male transfer stub,
    defined by `pco_turns`, `pco_clearance`, `bore_dia`. **Compatible with**
    `bottle-thread`, `bird-feeder`, `faircap-filter`, and `pet-dispenser` — any of
    those parts can thread onto the stub, so a mason jar joins the whole PCO family.
  - **Mason Jar Continuous Thread** (`thread`, 70-450 / 86-450 mason CT finish) —
    the coarse female jar thread, defined by `jar_size`, `jar_turns`, `clearance`,
    `wall`. Starts a mason-jar family cluster (no existing Commons member shares it
    yet).
- **Material awareness:** `clearance` / `pco_clearance` are exposed so each printed
  thread fit can be tuned per material and shrinkage; `tolerance_by_material` is
  declared.
- **Societal benefit:** the mason jar and the PET bottle are the two most abundant
  standardized household vessels, but their threads never met; this adapter bridges
  them and replaces lost/rusted mason lids on demand.
- **License:** CERN-OHL-W-2.0

## Food contact & material responsibility

Mason jars are widely used for food and dry goods, and these lids touch that
contents. FDM prints are **not inherently food-safe**: layer lines harbor bacteria
and many filaments and colorants are not food-contact rated. Using these lids with
food is **your responsibility** — choose a certified food-contact filament, print
with a clean nozzle, and note that a printed lid is **not a canning / vacuum-seal
lid** and must not be relied on for preservation.

## Thread modeling notes (watertight + fast)

- Both threads are **volumetric fused helical ribs** swept along a genuine
  `makeHelix` path and unioned into the wall — a coarse mason-jar female thread and
  a PCO-1881 male thread.
- Turn counts are forced to **half-integers** (`floor(n)+0.5`); a whole-integer
  count degenerates the OCCT helical sweep into a null body.
- The mason sockets have a **closed base**; the transfer bore and sifter holes are
  cut through afterward (an open-ended threaded socket tessellates non-watertight).

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters read via a `PARAM(lambda: name,
  default)` guard; the final solid is assigned to `result`. No cross-file imports.
