# Accessory Shoe Mount

The **ISO 518 camera accessory shoe**, generated with **CadQuery** (B-Rep): the
~18.7 mm rail with rounded-corner flanges that every on-camera light,
microphone, monitor and flash slides onto. Build the male foot, the female
socket, or a dual bar that carries two accessories at once.

Part of the **Yantra4D Hyperobjects Commons**. Official visualizer and
configurator: [Yantra4D](https://app.yantra4d.com).

## Modes

| Mode | Part | Description |
| :--- | :--- | :--- |
| **Cold Shoe (Male Foot)** | `cold_shoe_male` | The male accessory-shoe foot on a mounting base with a 1/4-20 clearance hole. Slides into any ISO 518 socket. |
| **Shoe Socket (Female)** | `shoe_socket` | The camera-side receiver — a block with the shoe channel milled through, so a male foot slides in and the lips capture its flanges. Carries a 1/4-20 hole. |
| **Dual Shoe Bar** | `dual_shoe_bar` | A rigid bar with a male shoe foot at each end and a central 1/4-20 hole — rig two accessories to one camera shoe or handle. |

## Parameters

| Group | Parameter | Default | Notes |
| :--- | :--- | :--- | :--- |
| Accessory Shoe | `shoe_type` | male-shoe | Bias a lone build toward foot vs receiver. |
| Accessory Shoe | `foot_width` | 18.7 mm | ISO 518 outer shoe width. |
| Accessory Shoe | `channel_w` | 14.9 mm | Recessed tongue width the flanges frame. |
| Accessory Shoe | `flange_th` | 1.6 mm | Flange lip thickness the socket grips. |
| Accessory Shoe | `shoe_len` | 20.0 mm | Slide travel length. |
| Accessory Shoe | `corner_r` | 1.0 mm | Rounded outer flange corners. |
| Base & Fit | `base_th` / `base_pad` | 5.0 / 5.0 mm | Mounting-base thickness and overhang. |
| Base & Fit | `quarter_d` | 6.6 mm | 1/4-20 clearance hole. |
| Base & Fit | `wall` | 3.0 mm | Socket lip wall thickness (`shoe_socket`). |
| Base & Fit | `clearance` | 0.35 mm | Per-side socket↔foot sliding fit. |
| Dual Bar | `bar_span` | 70.0 mm | Overall dual-bar length. |

## The shoe profile (why it mates)

The accessory shoe is an **inverted-T flange pair**: a full-width plate whose
centre is raised, leaving two side flanges of `flange_th`. The `shoe_socket`
mills the same cross-section (grown by `clearance` per side) straight through
the block, so its overhanging lips capture the male foot's flanges as it slides
in along the shoe length. Because the channel is **open at both Y ends**, the
cavity vents to outside — a through-slide, never a trapped void. The
`channel_w ≤ foot_width − 2` constraint keeps at least a 1 mm flange per side.

## Presets

- **Standard ISO 518 Foot** — the reference male foot at spec dimensions.
- **Camera-Side Socket** — the receiver at nominal fit clearance.
- **Twin-Light Bar** — a 90 mm bar for a light + mic pair.

## Hyperobject Profile

- **Domain:** commercial
- **CDG interfaces:**
  - **ISO 518 Accessory Shoe** (`rail`, *ISO 518*) — the shoe cross-section,
    defined by `foot_width`, `channel_w`, `flange_th`, `shoe_len`, `corner_r`.
    Any foot and socket built at the same width and flange mate, and mate with
    the century of commercial accessory-shoe gear.
  - **1/4-20 UNC Mounting Hole** (`bolt_pattern`, *ASME B1.1 1/4-20 UNC*) — the
    base's mounting hole, defined by `quarter_d`, for the tripod screw common to
    every camera rig.
- **Material awareness:** `tolerance_by_material` is declared — flange and
  channel dimensions plus `clearance` are exposed so the sliding fit tunes per
  material/printer.
- **Societal benefit:** the accessory shoe is the single most universal camera
  interface; on-demand feet, sockets and dual bars keep any accessory mountable
  to any rig and repair a cracked shoe instead of discarding the accessory.
- **License:** CERN-OHL-W-2.0

## Engine notes

- Engine: **CadQuery** (`main.py`). Exports STL / 3MF / STEP / GLB / GLTF / OBJ.
- Self-contained (sandbox-safe): parameters via a `PARAM(lambda: name, default)`
  guard because the render sandbox does not expose `globals()` / `eval`.
  `target_part` dispatches which part to build; the final solid is `result`.
- Every part is built from extruded 2D cross-sections and overlapping box
  unions — no tangent kisses, no post-cut fillets (flange corners are rounded in
  the 2D profile). All shipped modes and presets render **watertight** in well
  under 20 s.
