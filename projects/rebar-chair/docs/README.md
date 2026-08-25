# Rebar Chair / Spacer

**Concrete cover spacers** — generated with **CadQuery** (B-Rep). A rebar chair does one
job: hold reinforcing steel at its specified distance from the form face while concrete
is poured around it. Get the cover wrong and the steel corrodes, the slab spalls, and
the structure fails decades early. They are bought by the sack in a handful of fixed
heights; the cover a drawing actually calls for is rarely one of them.

The shared interface is the **bar snap saddle**, sized to US bar designations — #3
(9.5 mm), #4 (12.7 mm), #5 (15.9 mm) — and the **cover height** the chair establishes.

Official visualizer and configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Parts | Description |
| :--- | :--- | :--- |
| **Bar Chair (Splayed Legs)** | `chair_saddle` | A snap saddle held at `cover` height by two splayed legs on a base pad. The classic slab chair. |
| **Wheel Spacer** | `chair_wheel` | A lightened disc with a central bar bore — rolls along the bar and sets cover from a vertical form face. |
| **Crossbar Chair** | `chair_crossbar` | Two snap saddles at 90°, holding a mesh intersection where two bars cross. |

## Parameters

| Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- |
| `bar_dia` | 12.7 mm | 8 – 20 | Rebar diameter — 12.7 mm is a #4 bar (1/2 in). |
| `cover` | 40 mm | 20 – 90 | Concrete cover depth, the whole point of the part. |
| `clip_wall` | 3.5 mm | 2.5 – 6 | Saddle wall thickness. |
| `snap_grip` | 0.82 | 0.7 – 0.95 | Saddle mouth width ÷ bar diameter. Lower grips harder. |
| `leg_t` | 6 mm | 4 – 12 | Leg thickness. |
| `base_w` | 38 mm | 28 – 70 | Base pad width — the footprint against the form. |
| `wheel_od` | 80 mm | 40 – 140 | Wheel spacer diameter (wheel mode only). |

## Hyperobject Profile

- **Domain:** construction
- **CDG interfaces:** Rebar Snap Saddle (`snap` — US #3/#4/#5 bar designations),
  Concrete Cover Height (`rail` — slab through footing values).
- **Commons license:** CERN-OHL-W-2.0

## Field note

Cover is a **code-governed** dimension, not a preference. Set it from the structural
drawing and the governing code for the exposure class, never from a default. Printed
chairs are also not a substitute for an engineered spacer where one is specified —
material, creep under load and alkali resistance all matter in concrete, and PLA in
particular has no business in a structural pour.

## Fabrication notes

### Never cut a bore onto its own wall

`chair_crossbar` builds a central column tying the base to both saddles, then re-opens
the two bar channels through that column so the bars can actually seat. The cutter's
radius was written as `bar_dia / 2 + 0.4` — which is **exactly** `_clip_ir`, the saddle's
own inner radius. So the cutting cylinder's wall lands coincident with the saddle bore
wall, and cutting a face onto itself is the classic zero-thickness boolean.

At default values it happened to survive. At `bar_dia = max` and at `clip_wall = min` it
did not, and the failure is silent about its cause:

```
base+column     wt=True  bodies=1
+low saddle     wt=True  bodies=1
+up saddle      wt=True  bodies=1
-low bore       wt=False bodies=0     ← the coincident face
```

Both failing cases broke at the same step, which is what pointed at the cutter rather
than at the saddles. The re-bore is now `_clip_ir - 0.01`: strictly **inside** the
saddle bore, so it only ever removes column material and never touches the saddle wall
it was accidentally re-cutting.

The general form of the rule: when you re-open a feature through material added later,
size the cutter to the feature that already exists **minus** a hair — not to the nominal
dimension both were derived from.
