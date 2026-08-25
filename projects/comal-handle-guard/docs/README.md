# Comal Handle Guard

A guard for the bare steel handle of a comal.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

The **comal** is the flat griddle of Mesoamerica. Tortillas are cooked on it, chiles and tomatoes are charred on it for salsa, coffee and cacao are toasted on it. It is the oldest continuously used cooking surface in the region and it is still in daily use in millions of kitchens.

The steel version sold in every market is a plain disc with a flat strap handle welded or riveted to its rim: **one piece of metal, no insulation anywhere, sitting over a flame.** Insulating it would cost more than the pan.

So the handle conducts, and what gets used to grab it is whatever cloth is nearest — a rag, a fold of apron, a towel that may be damp. **A damp cloth is the worst case.** Water conducts far better than the air trapped in a dry one, and it carries heat to the hand faster than the cloth can be dropped.

This guard replaces that improvisation with a part that clamps on and stays on. It is always there, it cannot be picked up wet by mistake, and it does not have to be found in a hurry with full hands.

It is not a novel mechanism and it is not clever. It is a part that costs a few pesos of filament and is simply not sold for the pan most people actually own.

## What it does and does not do

**Printed plastic cannot survive a flame, and this cartridge does not pretend otherwise.**

The guard does **not** insulate a handle sitting *in* the fire. It lives on the **outer portion** of the handle, away from the pan, where a strap handle is already far cooler than at its root. There it puts two things between the steel and the hand:

```
standoff = air_gap_mm  +  wall
```

The **air gap is the better half** of that. Still air insulates far better than any printable polymer, so most of the thermal break is the gap and only the rest is the material. The manifest warns below 1.5 mm of gap, where the guard contacts the steel almost directly and conducts rather than insulating.

### Material class is declared, not assumed

`material_temp_class` states plainly which polymer the geometry assumes, and **raises the minimum wall as a clamp rather than a warning** — a guard that fails silently at temperature would be worse than the rag it replaces.

| Class | Working ceiling | Min wall enforced |
| :--- | ---: | ---: |
| PLA | 55 °C | 4.0 mm — **not recommended** |
| PETG | 70 °C | 3.5 mm |
| ABS / ASA | 90 °C | 3.0 mm |
| Polypropylene | 95 °C | 3.2 mm |
| Nylon (PA) | 110 °C | 3.0 mm |

These are conservative continuous-service numbers for an FDM print, **not datasheet peaks**. A printed part is anisotropic and loses stiffness well below its published heat-deflection temperature.

## Handle stock is the parameterisation

A comal handle is flat strap — the whole family is described by **width × thickness**. Comal handles are shop-made and vary widely, so measure yours; the sliders exist because there is no single right answer.

That same rectangular-stock series is what the commons' other handle cartridges use, so this guard interchanges with `ferro-handle`, `bar-clamp` and `garment-clip` rather than publishing a fourth convention for "a flat handle".

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `guard` | Handle Guard | CadQuery B-Rep | `main.py` |
| `hook_rest` | Wall Hook | CadQuery B-Rep | `main.py` |
| `lid_knob` | Tapadera Knob | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

The **wall hook** is sized to the same strap, because a comal lives on the wall between uses in most kitchens that have one — hanging it by the handle keeps the cooking face off the wall and off the counter. The **tapadera knob** clamps the same flat section, for the lid that covers a comal to steam tortillas soft.

## Hyperobject Profile

- **Domain:** household
- **CDG interfaces:**
  - **Flat Handle Stock** (`profile`, 10–45 mm × 2–12 mm strap series) — compatible with `ferro-handle`, `bar-clamp`, `garment-clip`.
  - **Clamp Jaw Mouth** (`snap`, internal — capped so two retaining legs always survive).
  - **Thermal Standoff** (`profile`, declared air gap + wall with a material-class floor).
- **Material awareness:** shrinkage compensation, tolerance-by-material. **Recycled material is deliberately disabled** — layer adhesion at temperature is the property being relied on, and reground filament has unpredictable interlayer strength.
- **License:** CERN-OHL-W-2.0

## Printing and using it

Print **jaw-down**, 4 perimeters, 40 % infill. The layer lines then run *around* the C rather than across the mouth, so the guard springs instead of splitting on first fitting.

Use **ABS/ASA or nylon** if you have them. PETG is acceptable and is the default. **Do not use PLA** — it is in the list only so the trade-off is visible, and the geometry pushes its wall to 4 mm to say so.

Fit it on the **outer portion** of the handle. The manifest warns above 140 mm of grip length for that reason: a longer guard reaches toward the pan and the flame.

### Scope — read this

**Check it before you trust it, and check it again as it ages.** Warm the comal on a low flame with the guard fitted and feel the guard *before* you rely on it in normal use. A printed part in a kitchen is a part you are responsible for.

This guard does not make a comal safe to handle without attention. It reduces the temperature reaching the hand on the outer handle; it does not make the pan cool, it does not protect against contact with the comal body or the flame, and it will soften and deform if it is put over direct heat. If it ever feels soft, tacky or loose, replace it. Nothing here is a substitute for the ordinary care that cooking over fire requires, and none of these materials is certified for food contact or for high-temperature service by anyone.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode, plus all five material classes — every case `is_watertight == True` with `body_count == 1`. The guard, hook and knob were additionally grid-tested across every handle-width × handle-thickness × wall × material-class combination.

**One failure was found and fixed, and it is a good last lesson for this batch:**

- **The knob's domed head was a `sphere()`, and a sphere is broken at the tessellator.** `sphere(r).cut(box)` produces a solid that OCC reports as **valid and single**, but whose exported mesh comes back non-watertight and split into two bodies — because a sphere's poles are degenerate points where every meridian meets. Isolating the build made it unambiguous: the **head alone** was already two bodies before any union with the stem, so the join was never the problem.

  A profile revolved to a point on the axis has exactly the same defect. The dome is now a revolve ending on a small **flat apex** (`apex_r`), which is the fix the commons' other dome geometry already uses. It is worth stating plainly because it is the most deceptive failure mode in this whole engine: **the kernel says the solid is fine, and it is the mesh that is not.**

Everything else in this cartridge was clean on the first pass, because the rules were already paid for elsewhere in this batch: every cut is bounded inside the blank that must contain it with a full margin; the mouth is capped so two retaining legs always survive; every added feature overlaps the material it grows from rather than touching it face-to-face; no internal void is ever sealed; and no fillet is taken on any edge a slot or bore has touched.

---

## The commons' 500th object

This cartridge is the five hundredth object in the Yantra4D Hyperobjects Commons, published on 25 August 2026.

Five hundred is an arbitrary number and the commons is not finished at it. But it seemed worth marking with something ordinary rather than something impressive. Across the preceding four hundred and ninety-nine cartridges — brackets, threads, lattices, instruments, medical fittings, whole standards families — not one object was rooted in Mexico, which is where this project is written. A comal handle guard is not a technical achievement. It is a piece of plastic that stops a common burn on a pan that has been in daily use here for several thousand years, and it is exactly the kind of small, unglamorous, locally obvious part that a commons exists to hold.
