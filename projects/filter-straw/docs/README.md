# Water Filter / Straw Adapter

Threaded adapters that connect a personal filter straw, a sport spout, or a hose
to a standard **28 mm PET bottle neck**, generated with **CadQuery** (B-Rep). The
28 mm bottle finish is the near-universal soda / water-bottle thread — **28-410**,
and the lightweight carbonated **PCO-1881** (27.4 mm OD, **2.7 mm pitch**). One
28 mm thread interface builds a straw-holding screw cap, a bite-valve drink cap,
and an inline hose coupler.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

> ## ⚠️ Safety — this is NOT a water filter
>
> These parts are a **housing / interface only**. They **carry and couple** a
> filter element, spout or hose to a bottle — they do **not** filter, purify, or
> disinfect water, and they contain no filter media. Nothing here makes unsafe
> water safe to drink. Use them **only** with a certified filter element (for
> example a [faircap](https://app.yantra4d.com) cartridge or a commercial filter
> straw) rated for your water source, and follow that filter's instructions. Do
> not rely on a printed adapter for potable-water safety. FDM prints are porous
> and hard to fully sanitize; treat them as non-food-safe unless you have
> qualified the material and process yourself.

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Filter Straw Cap** | `straw_adapter` | A 28 mm screw cap with a top spout tube that holds a personal filter straw and a through bore so water passes from the bottle up the straw. |
| **Sport Bite-Valve Cap** | `bottle_cap` | A 28 mm screw cap with a tapered sport / bite-valve spout nipple and a drink-through bore. |
| **Inline Hose Coupler** | `inline_coupler` | A 28 mm screw cap on one end and a stepped hose barb on the other, with a through bore — plumb a bottle to a hose or gravity-fed line. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| 28 mm Bottle Thread | `thread_d` | 28.0 mm | Bottle neck major diameter. Standard soda/water is 28 mm. |
| 28 mm Bottle Thread | `pitch` | 2.7 mm | Thread pitch. PCO-1881 is 2.7 mm; 28-410 is ~2.82 mm. |
| 28 mm Bottle Thread | `turns` | 3.5 | Number of thread turns engaged. |
| Cap | `wall` | 2.6 mm | Cap and tube wall thickness. |
| Cap | `cap_h` | 15.0 mm | Screw-cap skirt height. |
| Straw / Barb Port | `straw_d` | 8.0 mm | Filter-straw / sport-spout bore (`straw_adapter`, `bottle_cap`). |
| Straw / Barb Port | `barb_d` | 10.0 mm | Stepped hose-barb outer diameter (`inline_coupler`). |
| Straw / Barb Port | `fit` | 0.3 mm | Added to the straw bore for a press fit (`straw_adapter`). |

## The 28 mm thread (why it is the interface, and how it is built)

Almost every discarded soda and water bottle carries the same 28 mm neck finish,
so an adapter threaded to that finish mates to bottles people already have. The
thread is modeled as a **fused helical rib**: a small triangular profile is swept
along a `makeHelix` path on the bore radius and **unioned** into the cap wall with
a 0.6 mm embed, so the union overlaps the wall material. This is deliberate — a
thread cut or revolved as a *groove* produces a multi-component, non-watertight
mesh, whereas a fused rib stays a single solid. Set `pitch` to 2.7 mm for PCO-1881
or ~2.82 mm for 28-410.

## Presets

- **PCO-1881 Straw Cap** — a straw-holding cap at the lightweight bottle pitch.
- **28 mm Sport Cap** — a bite-valve drink cap.
- **28 mm Hose Coupler** — a bottle-to-hose barb coupler.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **28 mm Bottle Thread** (`thread`, *28mm/bottle (28-410 / PCO-1881)*) — the
    screw thread, defined by `thread_d`, `pitch`, `turns`. Any cap built to this
    finish threads a standard 28 mm PET bottle.
  - **Filter Straw Port** (`socket`, *internal*) — the straw / spout bore,
    defined by `straw_d`, `fit`.
- **Material awareness:** `tolerance_by_material` is declared — `pitch`, `fit`
  and wall dimensions are exposed so the thread and straw fit tune per material
  and printer.
- **Societal benefit:** the 28 mm PET bottle neck is the most abundant reusable
  container fitting on earth; printable adapters let a filter straw, spout or hose
  mate to any bottle, so a filter element works with containers people already
  have instead of a proprietary bottle. This part is a housing only and never
  replaces a certified filter.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard; `target_part` dispatches the part; the final solid is `result`.
- Each part is **one solid**. The 28 mm thread is a **helical rib** swept along a
  `makeHelix` path and **fused** (unioned) into the wall with a wall embed — never
  a cut/revolved groove (which would yield a non-watertight, multi-body mesh). The
  cap bore opens to the bottom face; spouts, nipple and barb are tubes with
  through bores that vent both ends; the barb bore is constrained to stay inside
  the stem so it never severs a body at small diameters. Fillets are applied to
  clean blanks before feature cuts and wrapped in try/except. All shipped modes
  and presets — and the parameter extremes — render **watertight**
  (`body_count == 1`); a threaded part takes up to ~30 s on the server.
