---
title: JSON Manifest Specs
description: Documentation for project.json architecture
---

Every Hyperobject inside Yantra4D's `projects/` directory requires a rigid JSON structural manifest (`project.json`).

## Schema Validation
The JSON structure is strictly validated by `scripts/validate_manifests.py` against `project-manifest.schema.json`.

### Minimal Example
```json
{
  "project": {
    "name": "Soft Jaw",
    "hyperobject": {
      "is_hyperobject": true
    }
  },
  "estimate_constants": {
    "base_time": 2,
    "per_unit": 0.5,
    "per_part": 1.5,
    "wasm_multiplier": 1.5
  },
  "modes": [
    {
      "id": "jaw",
      "scad_file": "soft_jaw.scad",
      "cq_file": "soft_jaw.py"
    }
  ],
  "parameters": [
    {
      "id": "jaw_width",
      "type": "slider",
      "min": 10,
      "max": 100
    }
  ]
}
```

### Core Components
1. **`modes`**: Defines the different visual variants of a project. Each mode names a `scad_file`, which may be an OpenSCAD `.scad`, a CadQuery `.py`, or a `.graph.json` node graph; the engine is inferred from the extension or set explicitly with `engine`. A `cq_file` is optional and only used for dual-kernel cartridges that want CadQuery to serve B-Rep formats for an OpenSCAD mode — it is **not** required, and graph cartridges never use one.
2. **`parameters`**: Declares UI interactive components for the Yantra4D React workspace to auto-generate.
3. **`estimate_constants`**: Required numerical heuristics allowing the AI logic to predict the exact time a user's browser/backend CPU will take compiling the STL depending on parameter densities.
4. **`material_awareness`**: When defined, connects the geometric cartridge to the intelligence pipeline of Yantra4D's **Material Hyperobjects**. It allows the object to attain "hyperawareness", ingesting nanoscale variables (TDA), spatial compensations (shrinkage), and semantic data from physical AM substrates to dynamically adapt its geometry.
