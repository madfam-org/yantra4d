# Fourth 100 Hyperobjects (#301–400) — Strategy

The first three hundreds grew the commons by *popularity*. The fourth hundred can be
**graph-aware and insight-led** because we now have the CDG family taxonomy, the
compatibility graph, and the data-shape learnings. Author #301–400 to *strengthen the
moat and the data pool*, not just add count.

## Design principles (new, earned this cycle)

1. **Fill thin CDG families to multiply edges.** The compatibility graph is 98 nodes / 92
   edges. Many high-value families have only 1–2 members — adding a compatible object to a
   thin family creates NEW interoperability edges (higher marginal value than a new isolated
   object). Priority thin families (members):
   - `arca-swiss` (1), `gopro-mount` (1), `unc-3/8-16` (1) — photography/mounting ecosystem
   - `e26-e27-lamp` (2), `gu10`/`b22` — lighting
   - `optical-breadboard` (2), `cuvette` (2) — lab/optics
   - `battery-cell` (2), `timing-belt` (2), `shaft-spline` (2), `iso-hex-fastener` (2)
   - `cable-gland` (1), `conduit` (1), `drip-irrigation` (1), `wall-stud` (1),
     `compass-capsule` (1), `beverage-can` (1), `bevel-gear` (1), `aerator-m22-m24` (1)
   Each of these wants 2–4 more members that mate on the shared standard.

2. **Balance under-represented domains.** Current: household 113, industrial 78, commercial
   63, medical 29, infrastructure 20, hybrid 7, soft-robotics 1. The fourth 100 should skew
   toward **medical, infrastructure, hybrid, soft-robotics** to round out the commons.

3. **Author with `compatible_with` populated from the start.** New objects should declare the
   family standards they mate with, so they arrive INSIDE the graph (no backfill needed).
   Cite real standards for the interoperability facet.

4. **Feed the data pool deliberately.** Every cartridge already ships presets/constraints/
   camera_views/material_awareness — keep that. Now that discovery surfaces standards,
   material capabilities, and families, choose objects and standards that make those facets
   richer (e.g. objects with `shrinkage_compensation`/`recycled_material_toggle` are rare —
   16/30 of 300 — so material-adaptive objects add facet value).

## Hard-won authoring canon (carry forward — in CARTRIDGE_BRIEF.md)
- `import cadquery as cq` top; `PARAM(lambda: name, default)`; `result`; dispatch on `target_part`.
- `material_awareness` in TOP-LEVEL `hyperobject`; `project.hyperobject` minimal `{is_hyperobject:true}`.
- Constraints use `expression` (not `rule`). Watertight canon: fillet-before-cut, union overlaps
  not tangents, grooves/threads as volumetric ribs, **thread turns half-integer (never whole)**,
  loft-to-flat-bottom for domes (no sphere-apex pole singularity), obround slots.
- NEVER let a script write into submodule-backed projects (gridfinity, din-rail-clip, motor-mount…).
- System ruff 0.15 for cartridges; the backend now has a `[tool.ruff]` config.

## Process
Same proven wave model: tier the 100 by domain/theme, dispatch ~5–8 cartridges per agent with
the CARTRIDGE_BRIEF + a per-tier spec, each self-validating (watertight + body-count + ruff +
compliance). Validate + commit in tiers. Only AFTER PR #24 is merged.
