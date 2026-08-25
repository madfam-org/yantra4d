# Sign Post Bracket

Brackets that mount a sign blank to a street-furniture post — real post sections on one face, the real punched blank pattern on the other.

A **CadQuery** B-Rep hyperobject — every mode renders watertight and exports STEP. Un hiperobjeto **CadQuery** B-Rep: cada modo es hermético y exporta STEP.

Part of the **Yantra4D Hyperobjects Commons** · Official visualizer: [Yantra4D](https://app.yantra4d.com)

## Why this exists

Signage hardware is where small public works quietly stall. The blank and the post are both cheap and standard, but the bracket between them is proprietary, sold in boxes of fifty, and specific to one post family — so a school crossing sign, a trailhead marker, a community garden nameplate or a village fingerpost waits on a minimum order that nobody will place.

Two real interfaces meet in this part and neither is negotiable if it is to fit anything: the **post section** on one side and the **sign-blank hole spacing** on the other. Because both are genuine published patterns, a printed bracket drops into existing stock instead of requiring new posts or drilled blanks.

## Modes

| Mode | Label | Engine | File |
| :--- | :--- | :--- | :--- |
| `u_channel` | U-Channel Bracket | CadQuery B-Rep | `main.py` |
| `square_tube` | Square Tube Clamp | CadQuery B-Rep | `main.py` |
| `blade_arm` | Blade Arm | CadQuery B-Rep | `main.py` |

Each mode dispatches on `target_part`; the `parts[]` id matches the built value so the platform renders each mode distinctly.

## Parameters

`u_section` and `sq_section` pick the post; `clearance` opens the fit for a galvanised or painted section. `wall` and `plate_h` size the bracket — taller spreads the sign's wind load into more of the post. `post_bolt` and `post_holes` land on the post's punching; `sign_bolt` and `sign_spacing` land on the blank's. `arm_len` and `arm_t` size the blade arm. All labels and tooltips are bilingual (en/es).

## The post-section series is the point

The genuinely reusable thing here is not any one bracket — it is the **post-section series** as a declared CDG interface. Any future signage cartridge (a second bracket style, a bracket-to-bracket coupler, a temporary sign clamp) can key to `u_section` / `sq_section` rather than inventing a fourth way to describe a sign post. That is the difference between a commons and a folder of one-off parts.

## Standards encoded

| Feature | Dimension |
| :--- | :--- |
| U-channel 2 lb/ft web | 44.5 mm (1.75 in) |
| U-channel 3 lb/ft web | 50.8 mm (2.00 in) |
| U-channel 4 lb/ft web | 57.2 mm (2.25 in) |
| Square tube | 44.45 / 50.80 / 57.15 mm, plus 60 mm metric |
| Post punching pitch | 25.4 mm (1 in) |
| Sign blank bolt | 9.53 mm (3/8 in) punched |
| Sign blank spacing | 100 / 150 / 304.8 mm (12 in) centres |

## Hyperobject Profile

- **Domain:** infrastructure
- **CDG interfaces:**
  - **U-Channel Post Section** (`profile`, 2 / 3 / 4 lb per ft) — compatible with `stormwater-grate`, `path-stake`.
  - **Square Tube Post Section** (`profile`, 1.75 / 2.00 / 2.25 in and 60 mm) — compatible with `bollard-cap`, `extrusion-hyperobject`.
  - **Sign Blank Hole Pattern** (`bolt_pattern`, 3/8 in punched, 100 / 150 / 304.8 mm centres).
  - **Post Punching Pitch** (`bolt_pattern`, 1 in / 25.4 mm).
- **Material awareness:** shrinkage compensation, tolerance-by-material.
- **Societal benefit:** unblocks small signage jobs that stall on a proprietary bracket sold only in bulk.
- **License:** CERN-OHL-W-2.0

## Printing, material and load notes

Print the back plate flat on the bed so the bolt holes run through the layers rather than across them, and the sign's pull-out load is carried in shear. Use high infill (50%+) and at least four perimeters; this part's whole job is to transfer a wind moment.

**ASA** for anything permanent outdoors, **pigmented PETG** as a second choice. PLA is not suitable: it creeps under sustained bolt preload, so the joint loosens over a season even before UV embrittles it.

**Load scope — read this.** A sign is a wind sail on a lever arm, and the bracket is the fulcrum. A printed polymer bracket is appropriate for **small, low-mounted, non-regulatory signage**: trail markers, garden and allotment nameplates, wayfinding in a park, temporary event signs. It is **not** a substitute for a rated fixing on a regulatory traffic sign, a large blade at height, or anything on a road where failure puts a plate into traffic — those need metal hardware and, in most jurisdictions, an approved fixing. Nothing here has been load-tested, and this cartridge makes no engineering claim. Where a sign is mandated by a traffic authority, its mounting is that authority's specification, not this file's.

## Verification

All three modes verified watertight through the render sandbox at defaults **and** at the min and max of every slider that applies to the mode plus all post-section options — 60/60 cases, each `is_watertight == True` with `body_count == 1`. An additional 81-case local grid covered the nasty combinations (short bracket × six large bolts, minimum wall × maximum arm, tightest section × thickest wall).

Derived dimensions are clamped in `main.py` rather than trusted from the UI. Bolt positions are the interesting part: both `_post_bolt_zs` and `_sign_bolt_zs` compute a margin of `bolt_radius + wall/2` from each end and clamp into it, so six 16 mm bolts on a 40 mm bracket collapse to a legal layout instead of breaking out through the plate edge and shedding slivers. The post bolts fall back from the true 25.4 mm punching pitch to an even spread only when the pitch genuinely will not fit — the standard is honoured whenever the geometry allows it. Every hole is cut fully through and breaks out on both faces, so none is a blind pocket; a blind pocket would keep the Euler characteristic at 2 and pass a naive watertight check while being geometrically wrong, which is why the local harness reports genus as well as body count.
