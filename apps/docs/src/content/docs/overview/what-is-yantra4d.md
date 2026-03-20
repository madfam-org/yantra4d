---
title: What is Yantra4D?
description: Platform overview — what Yantra4D does, who it serves, and how it works.
---

Yantra4D is an open-source web platform for configuring, visualizing, and exporting parametric 3D-printable models. It turns text-based CAD scripts into interactive browser applications where anyone can adjust dimensions with sliders, preview changes in real time, and download production-ready files -- no CAD experience required.

## What you can do

- **Configure models visually.** Adjust width, height, slot count, wall thickness, and other parameters using sliders, checkboxes, and presets. The 3D preview updates in the browser.
- **Export in multiple formats.** Download STL for 3D printing, STEP for engineering workflows, GLB/GLTF for web and AR, or 3MF, OFF, and OBJ for specialized toolchains.
- **Estimate print cost.** Get filament weight, print time, and cost estimates for PLA, PETG, ABS, and TPU before you print.
- **Use AI to adjust parameters.** Describe what you want in plain language ("make it wider and shorter") and let the AI Configurator adjust sliders for you.
- **Inspect geometry.** Measure distances, view cross-sections, analyze wall thickness, and check overhang angles directly in the browser.
- **Share configurations.** Generate a URL that encodes your exact parameter choices so others can open the same configuration instantly.

## Who it serves

**Makers and hobbyists.** Browse the project gallery, pick a model, tweak it to your needs, and download an STL. No software to install.

**Educators and researchers.** Use parametric models as teaching tools. Students can explore how changing one dimension affects the entire geometry.

**Product designers.** Prototype faster by exposing tunable parameters to stakeholders. Share a link instead of a CAD file.

**Companies and labs.** Host custom parametric tools for internal use. The platform is self-hostable via Docker and supports tiered access control for teams.

**Open-source hardware contributors.** Publish your OpenSCAD projects as interactive configurators. The Hyperobjects Commons initiative provides a shared registry with standardized mechanical interfaces.

## How it works

### Manifest-driven design

Every project is defined by a single `project.json` manifest file. The manifest declares:

- **Modes** -- variants of the model (e.g., "Storage Box", "Horizontal Tray", "Staining Rack")
- **Parameters** -- adjustable values with types, ranges, defaults, and labels
- **Parts** -- individual components that can be rendered and colored separately
- **Presets** -- saved parameter combinations for common configurations

The studio reads this manifest and generates the entire UI automatically. Adding a new parameter or mode requires editing the manifest, not writing frontend code.

### Dual rendering

Yantra4D renders models through two paths:

1. **Client-side WASM.** OpenSCAD compiled to WebAssembly runs in a Web Worker inside the browser. This provides instant feedback as you move sliders, with no server required.
2. **Backend rendering.** A Flask API runs OpenSCAD (or CadQuery for B-Rep models) on the server. This handles complex models that exceed browser memory and produces formats like STEP that require a native CAD kernel.

If the backend is unreachable, the studio falls back to WASM automatically.

### Tiered access

The platform supports four access tiers:

| Tier | Renders/hr | Projects | Export formats | AI features |
|------|:---:|:---:|---|---|
| Guest | 30 | 0 | STL | -- |
| Essentials | 50 | 3 | STL | Configurator |
| Pro | 200 | Unlimited | STL, 3MF, OFF, STEP, GLB, GLTF, OBJ | Configurator + Code Editor |
| Madfam | 500 | Unlimited | All formats | All features + GitHub sync |

Guest access requires no account. For self-hosted deployments, authentication can be disabled entirely (all users receive full access).

## Architecture at a glance

```
projects/{slug}/project.json    Manifest (source of truth)
projects/{slug}/*.scad          OpenSCAD geometry files

apps/api/                       Flask API (rendering, export, AI, GitHub)
apps/studio/                    React + Vite + Three.js (configurator UI)
apps/landing/                   Astro marketing site
apps/admin/                     Admin dashboard
apps/docs/                      This documentation site

libs/                           OpenSCAD libraries (BOSL2, NopSCADlib, Round-Anything)
```

## Next steps

- [Configuring Models](/platform/configuring-models/) -- learn the studio interface
- [Exporting](/platform/exporting/) -- download models in the format you need
- [AI Assistant](/platform/ai-assistant/) -- use natural language to adjust parameters
- [API Quickstart](/developer/api-quickstart/) -- integrate with the Yantra4D API
