# Boot Hook Puller

The printable **boot-pull** — a T-handle on a flat blade ending in a hook that grabs the
sewn fabric loop inside a boot shaft. Generated with **CadQuery** (B-Rep). One piece.

Riding boots, western boots, work boots and waders carry that loop precisely because they
cannot be pulled on by hand. Without a hook the loop is nearly useless: clawing at it with
fingers is what rips the loop's stitching out of the shaft lining. Two pullers let you haul
both boots on at once, standing.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and configurator:
[Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Single Puller** | `puller` | One T-handle puller. |
| **Puller Pair** | `puller_pair` | Two on a plate — two boots, two hands. Two separate bodies. |
| **Wide-Throat Puller** | `wide_hook` | Throat opened ~70 % and the rod thickened ~45 %, for a folded webbing strap loop rather than a thin cord. |

## Parameters

| Group | Parameter | Default | Range | Notes |
| :--- | :--- | :--- | :--- | :--- |
| Blade | `blade_len` | 160.0 mm | 70–400 | Handle to hook. 140–180 mm mid-calf boot; 250 mm+ tall riding boot or wader. |
| Blade | `blade_w` | 20.0 mm | 10–45 | Blade width. Wider resists twist when one side of the loop takes the pull. |
| Blade | `blade_t` | 5.0 mm | 3–12 | Blade thickness. This is a lever carrying real body weight. |
| Handle | `handle_len` | 95.0 mm | 50–180 | Crossbar length — a whole hand plus a little. |
| Handle | `handle_dia` | 22.0 mm | 12–40 | Crossbar diameter. 22–28 mm spreads the pull across the palm. |
| Handle | `overlap_f` | 0.55 | 0.25–0.9 | **Handle root overlap** — see below. |
| Hook | `hook_r` | 11.0 mm | 4–30 | Throat radius; the gap the loop sits in. Cord loop 8–12 mm, webbing more. |
| Hook | `hook_d` | 6.0 mm | 2.4–14 | Hook rod diameter. Auto-clamped to the blade thickness. |

## The handle root

`overlap_f` sets how deep the handle cylinder sinks into the blade, as a fraction of the
handle diameter. **The handle root is where a printed puller actually breaks** — it is a
stress concentration at the exact point where the whole pull is transferred from a cylinder
into a slab, and a shallow, nearly-tangent union there fails on the first hard haul. The
default 0.55 is generous on purpose. Keep it above **0.4** for anything you will really lean
on, and take it toward 0.7–0.9 for a wader puller or if you print in a brittle material.

Beyond overlap: print the handle **along the bed**, so layer lines run across the root
rather than parallel to the crack that wants to form there.

## Print notes

Print **flat, blade lying on the bed** — the blade is flat in Y and the handle crosses it in
X, so the whole tool lies down with no bridging and no supports. PETG at 0.2 mm layers,
**5 perimeters**, 40 % infill is the minimum for a boot you have to fight; nylon or
polycarbonate for waders. PLA will snap at the handle root — do not use it here.

Perimeters matter far more than infill on this part: the load path runs along the blade
surface, and adding perimeters is what actually makes it survive. If a puller does break,
it will break at the root and it will break suddenly, so do not stand on one leg while
pulling.

Every mode exports as a single watertight solid. The hook is a **trimmed
`cq.Solid.makeTorus` quarter** wrapped in `cq.Workplane(obj=...)` — never a swept
`radiusArc`, which degenerates — with a stub arm giving the blade union real volume overlap.
The hook rod diameter is biased strictly off `blade_t`: a rod exactly as thick as the blade
sits **tangent** to the blade's flat side faces, and that tangency was observed to produce a
non-watertight union, so the clamps push it off tangency automatically.

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Boot-Loop Hook Throat** (`profile`, internal) — the working throat the boot's pull
    loop sits in, defined by `hook_r`, `hook_d`, `blade_t`. Not a sewn edge: the puller
    grabs a loop, it is never stitched to anything, so it is a profile match.
  - **T-Handle Grip** (`custom`, internal) — the hand interface and its load-bearing root,
    defined by `handle_len`, `handle_dia`, `overlap_f`.

## Fashion Cabinet bridge

Expected FC consumers: **tall boots** — riding, western, work boots and waders — whose
pull-loop notion specifies a matching puller, plus **dressing-aid** and
**accessible-dressing** kits alongside the long `shoe-horn`. Where FC's boot pattern places
the shaft pull loop, that loop's finished dimensions are what this tool has to fit.

FC-side `hardware_ref` block on the boot pull-loop notion:

```json
{
  "notion": {
    "hardware_ref": {
      "platform": "yantra4d",
      "project_slug": "boot-hook-puller",
      "linked": true,
      "params_map": {
        "blade_len": "boot_shaft_height_mm * 0.8",
        "blade_w": "20.0",
        "blade_t": "5.0",
        "handle_len": "grip_width_mm",
        "handle_dia": "22.0",
        "overlap_f": "0.55",
        "hook_r": "pull_loop_inside_h_mm * 0.5",
        "hook_d": "min(pull_loop_inside_w_mm * 0.4, 14)"
      }
    }
  }
}
```

The mating geometry is sized by **`hook_r` and `hook_d`** — the throat has to swallow the
boot's finished pull loop without forcing it, and the rod has to be thick enough to spread
the load over the loop's stitching instead of concentrating it on a few threads. The FC boot
item's pull-loop inside dimensions and shaft height are the driving values; `handle_len` and
`handle_dia` come from the user's grip.

`CERN-OHL-W-2.0`.
