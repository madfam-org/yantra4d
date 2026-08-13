---
title: Exporting Models
description: Available export formats, when to use each one, and how print estimation works.
---

Yantra4D supports exporting configured models in multiple file formats. The available formats depend on your access tier and the rendering engine used by the project.

## Available formats

| Format | Extension | Tier | Best for |
|--------|-----------|------|----------|
| **STL** | `.stl` | Guest+ | 3D printing (universal slicer support) |
| **3MF** | `.3mf` | Essentials+ | 3D printing (supports colors, metadata) |
| **OFF** | `.off` | Pro+ | Academic and computational geometry |
| **STEP** | `.step` | Pro+ | Engineering CAD (Fusion 360, SolidWorks, FreeCAD) |
| **GLB** | `.glb` | Pro+ | Web, AR/VR, game engines (binary glTF) |
| **GLTF** | `.gltf` | Pro+ | Web, AR/VR, game engines (JSON + binary) |
| **OBJ** | `.obj` | Essentials+ | General 3D (Blender, Maya, 3ds Max) |

### Format availability by engine

Not every format is available for every project. It depends on the rendering engine:

- **OpenSCAD engine** produces STL, 3MF, and OFF natively. OBJ, GLB, and GLTF are generated through automatic post-render conversion from STL.
- **CadQuery engine** produces STL, STEP, GLB, GLTF, 3MF, OBJ, VRML, and AMF natively with B-Rep precision.
- **Implicit SDF engine** produces STL natively; other mesh formats come from conversion, and STEP is not available.
- **Graph engine** transpiles a `.graph.json` node graph into sandboxed CadQuery, so it shares CadQuery's formats — including STEP, with no `cq_file`.
- **STEP export** requires that the project includes a CadQuery script (`cq_file` in the manifest). If no CadQuery script is available, STEP export is not offered.

The export panel only shows formats that the current project supports. The project manifest declares which formats are available via its `export_formats` field.

## How to export

1. Open the **Export** panel in the studio sidebar.
2. Select the format you want.
3. Click the download button.

For non-GLB formats, the studio triggers a dedicated render with the target format. The 3D viewer always displays GLB (converted automatically from STL) regardless of your export choice.

### Multi-part exports

If the current mode renders multiple parts, each part is exported as a separate file. This lets you print or process parts individually.

## Choosing the right format

**For 3D printing:**
- Use **STL** for maximum compatibility with slicers (Cura, PrusaSlicer, OrcaSlicer).
- Use **3MF** if your slicer supports it -- 3MF preserves color information and model metadata.

**For engineering workflows:**
- Use **STEP** when you need mathematically exact surfaces for CNC, injection molding, or further CAD work. STEP files carry true B-Rep geometry (parametric surfaces and edges), not tessellated triangles.

**For web and AR:**
- Use **GLB** for the most compact single-file format. GLB is the binary variant of glTF and is widely supported by web viewers, AR platforms, and game engines.
- Use **GLTF** if you need the JSON-readable structure (e.g., for programmatic post-processing).

**For general 3D work:**
- Use **OBJ** for broad compatibility with 3D modeling software like Blender, Maya, and 3ds Max.

## Print estimation

The Export panel includes a **print estimation** feature that calculates approximate printing metrics based on the current model geometry.

### What it estimates

| Metric | How it is calculated |
|--------|---------------------|
| Filament weight | Model volume (from Three.js geometry) multiplied by material density |
| Print time | Heuristic based on volume, layer height, and infill |
| Material cost | Weight multiplied by cost-per-kilogram for the selected material |

### Material profiles

You can select from the following materials (if the project defines them):

| Material | Density (g/cm3) | Typical cost/kg |
|----------|:---:|:---:|
| PLA | 1.24 | ~$20 |
| PETG | 1.27 | ~$25 |
| ABS | 1.04 | ~$22 |
| TPU | 1.21 | ~$30 |

Infill percentage is adjustable and defaults to 20%.

### Accuracy disclaimer

Print estimates are **heuristic approximations**, not slicer-accurate calculations. They are computed from the mesh volume and material density, without accounting for support structures, travel moves, retraction, or printer-specific acceleration profiles.

Use these estimates for rough planning. For accurate print time and filament usage, slice the exported STL or 3MF in your preferred slicer software.
