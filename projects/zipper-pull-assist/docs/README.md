# Zipper Pull Assist Lever

A rigid lever adaptive aid for zippers — clamps the slider **body** and multiplies hand force.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Not a repeat of `zipper-loop-aid`

The commons already publishes `zipper-loop-aid` (a finger ring on a C-clip) and `button-hook-aid`. This cartridge is the **rigid-lever** member of that family, and it takes a different interface on purpose:

| | `zipper-loop-aid` | this cartridge |
| :--- | :--- | :--- |
| Grips | the pull **tab** (a ~2 mm slip of metal) | the slider **body** (the moulded casting) |
| Helps when the problem is | grip **area** | grip **force** |
| Gives you | somewhere to hook a finger | a lever arm |

The distinction is mechanical, not cosmetic. A lever anchored on the tab would simply bend the tab flat; the slider casting is the only part of the assembly stiff enough to react a lever moment. That is why the CDG interface here is `slider_body_clamp` and not a second copy of `pull_tab_clip`.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `lever` | Pull Assist Lever | CadQuery B-Rep | `main.py` |
| `t_handle` | T Handle | CadQuery B-Rep | `main.py` |
| `tab_shim` | Broken-Tab Shim | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`body_l` / `body_w` / `body_h` measure the slider casting; `clamp_clear`, `wall` and `retain` set the clamp fit and how hard it snaps on. `lever_len`, `lever_w` and `lever_t` shape the arm; `bar_len` and `bar_dia` shape the T. All labels and tooltips are bilingual (en/es).

The lever arm leaves the clamp on the face **opposite** the retaining mouth, so pulling on the lever seats the clamp harder instead of prying it open — the failure mode that makes cheap commercial aids pop off mid-pull.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| #5 coil slider body (jackets, bags) | ~22 × 11 × 6 mm |
| Body length range (#3 → #10 series) | 10–40 mm |
| Clamp pocket | body + 2 × `clamp_clear` |
| Retaining mouth | `retain` × pocket width |

## Hyperobject Profile

- **Domain:** wearable
- **CDG interfaces:**
  - **Zipper Slider Body Clamp** (`socket`, moulded slider casting, #3–#10 series) — the load-bearing interface.
  - **Pull Eye** (`profile`, internal) — compatible with `zipper-loop-aid` and `cord-end`, so the shim can carry the existing ring.
- **Material awareness:** tolerance-by-material (clamp fit tuned per filament).
- **Societal benefit:** restores independent dressing where a zipper is the specific barrier, fitted to the user's own zipper and hand rather than to an average of both.
- **License:** CERN-OHL-W-2.0

## Printing notes

Print the lever flat with the arm in the bed plane so the bending load runs along the layer lines — an arm printed standing up will snap at a layer boundary on the first hard pull. PETG or ABS; PLA creeps and will slowly bend under repeated leverage. Stiffness scales with the *cube* of `lever_t`, so if an arm flexes, thicken it before lengthening it.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every applicable slider — 59/59 cases, each `is_watertight == True` with `body_count == 1`.

The T handle's rounded bar ends are a **filleted cylinder**, not spheres and not a revolved capsule profile. Both of those close the surface to a point on the bar axis; OCC tessellates that pole into zero-area facets, and although the B-Rep still reports a single watertight solid, the exported mesh carries two degenerate zero-volume shells and `body_count` comes back as **3**. This reproduced at every parameter value, including defaults, until the caps were rebuilt as fillets. It is the same pole-singularity failure already recorded against CadQuery spheres elsewhere in this commons.
