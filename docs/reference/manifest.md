# Project Manifest

The project manifest (`projects/{slug}/project.json`) is the single source of truth for modes, parameters, parts, colors, labels, estimation formulas, verification checks, and optional hyperobject metadata. Both the backend and frontend consume it, making the webapp fully data-driven and project-agnostic. A formal JSON Schema is available at `schemas/project-manifest.schema.json`.

---

## How It Works

1. **Backend** (`manifest.py`): Multi-project manifest registry. `discover_projects()` scans `PROJECTS_DIR` for subdirectories with `project.json`. `get_manifest(slug)` loads and caches per-project `ProjectManifest` instances. Falls back to `SCAD_DIR` for single-project mode.
2. **Frontend** (`ManifestProvider.jsx`): Fetches `/api/projects` on mount, then `/api/projects/{slug}/manifest` for the active project. On failure (backend down), falls back to a bundled copy at `src/config/fallback-manifest.json`.
3. **All UI controls** (sliders, checkboxes, color pickers, tabs, labels, tooltips) are rendered from manifest data — no hardcoded parameter definitions in the frontend.

---

## Schema

```jsonc
{
  "project": {
    "name": "Gridfinity Extended", // Display name (used in header)
    "slug": "gridfinity",         // Used for localStorage keys, export filenames
    "version": "1.0.0",
    "thumbnail": "/docs/images/gridfinity_thumb.png", // Path to gallery image
    "tags": ["storage", "modular", "organization"],
    "difficulty": "beginner"
  },

  "modes": [
    {
      "id": "unit",                         // Unique mode identifier
      "scad_file": "half_cube.scad",        // Which SCAD file to render
      "label": { "en": "Unit", "es": "Unidad" },  // Tab label (bilingual)
      "parts": ["main"],                    // Part IDs rendered in this mode
      "estimate": {
        "base_units": 1,                    // Fixed unit count, or "rows*cols"
        "formula": "constant",              // "constant" or "grid"
        "formula_vars": ["rows", "cols"]    // Optional: param names multiplied to compute units
      }
    }
    // ... more modes
  ],

  "parts": [
    {
      "id": "main",                         // Part identifier (matches SCAD render_mode)
      "render_mode": 0,                     // Integer passed to OpenSCAD as render_mode
      "label": { "en": "Color", "es": "Color" },  // Color picker label
      "default_color": "#e5e7eb"            // Default hex color
    }
    // ... more parts
  ],

  "parameters": [
    {
      "id": "size",                         // Parameter name (sent to backend)
      "type": "slider",                     // "slider", "checkbox", or "text"
      "default": 20.0,
      "min": 10, "max": 50, "step": 0.5,   // Slider range (ignored for checkboxes)
      "label": { "en": "Size (mm)", "es": "Tamaño (mm)" },
      "tooltip": { "en": "...", "es": "..." },
      "description": { "en": "...", "es": "..." },  // Optional, shown below slider
      "group": "visibility",                // Optional grouping (renders with header)
      "visibility_level": "basic",           // Optional: "basic" (default) or "advanced"
      "parent": "show_walls",               // Optional: parent param ID (for hierarchy)
      "visible_in_modes": ["unit", "assembly"],  // Which modes show this parameter
      "widget": {                            // Optional: custom widget type
        "type": "color-gradient"             // "color-gradient" or "component-picker"
        // If type="component-picker", add: "catalog": "nopscadlib/ball_bearings"
      },
      "maxlength": 30                        // Optional: max characters for text params
    }
    // ... more parameters
  ],

  "camera_views": [
    {
      "id": "iso",                                    // View identifier
      "label": { "en": "Isometric", "es": "Isométrico" },  // Button label (bilingual)
      "position": [50, 50, 50]                        // Camera XYZ position
    }
    // ... more views
  ],

  "parameter_groups": [
    {
      "id": "visibility",                             // Group ID (matches param.group)
      "label": { "en": "Visibility", "es": "Visibilidad" },  // Section header label
      "levels": [                                    // Optional: enables Basic/Advanced toggle
        {"id": "basic", "label": {"en": "Basic", "es": "Básico"}},
        {"id": "advanced", "label": {"en": "Advanced", "es": "Avanzado"}}
      ]
    }
    // ... more groups
  ],

  "viewer": {
    "default_color": "#e5e7eb"                        // Fallback mesh color
  },

  "constraints": [                            // Optional: cross-parameter validation rules
    {
      "rule": "width_units * depth_units <= 24",  // Expression evaluated with current params
      "message": { "en": "Max 24 grid cells", "es": "Máximo 24 celdas" },
      "severity": "warning",                 // "warning" or "error" (error blocks render)
      "applies_to": ["width_units", "depth_units"]  // Params highlighted on violation
    }
  ],

  "bom": {                                   // Optional: bill of materials
    "hardware": [
      {
        "id": "magnets_6x2",                // Unique hardware item ID
        "label": { "en": "N52 6×2mm Magnets", "es": "Imanes N52 6×2mm" },
        "quantity_formula": "(enable_magnets ? 4 : 0) + (bp_enable_magnets ? 4 * width_units * depth_units : 0)",
        "unit": "pcs",                       // Display unit
        "supplier_url": "https://..."        // Optional: link to supplier
      }
    ]
  },

  "grid_presets": {                          // Optional: rendering/manufacturing quality presets
    "rendering": {
      "emoji": "🪽",
      "label": { "en": "Quick Preview", "es": "Vista Rápida" },
      "values": { "width_units": 2, "depth_units": 1 }  // Param overrides for this preset
    },
    "manufacturing": {
      "emoji": "⭐",
      "label": { "en": "Large Grid", "es": "Rejilla Grande" },
      "values": { "width_units": 4, "depth_units": 4 }
    },
    "default": "rendering"                   // Which preset to apply by default
  },

  "export_formats": ["stl", "3mf", "off"],  // Optional: supported export formats (default: ["stl"])

  "print_estimation": {                     // Optional: print estimation defaults
    "default_material": "pla",              // "pla", "petg", "abs", or "tpu"
    "default_infill": 0.2                   // 0.0 to 1.0
  },

  "difficulty": "beginner",               // Optional: "beginner", "intermediate", "advanced"

  "materials": [                           // Optional: material profiles for print estimation
    { "id": "pla", "label": {"en": "PLA"}, "density_g_cm3": 1.24, "cost_per_kg": 20 },
    { "id": "petg", "label": {"en": "PETG"}, "density_g_cm3": 1.27, "cost_per_kg": 25 }
  ],

  "verification": {                        // Optional: multi-stage STL quality checks
    "stages": [
      {
        "id": "geometry",
        "label": {"en": "Geometry Check"},
        "checks": ["watertight", "volume_positive", "no_degenerate_faces"]
      },
      {
        "id": "printability",
        "label": {"en": "Printability Check"},
        "checks": ["min_wall_thickness", "overhang_angle", "bed_adhesion"]
      }
    ]
  },

  "assembly_steps": [                      // Optional: step-by-step assembly instructions
    {
      "step": 1,
      "label": {"en": "Print all parts", "es": "Imprime todas las piezas"},
      "visible_parts": ["main"],
      "camera": {"position": [60, 60, 60], "target": [0, 0, 0]}
    }
  ],

  "estimate_constants": {
    "base_time": 5,       // Base seconds for any render
    "per_unit": 1.5,      // Added per unit (grid cell or fixed count)
    "fn_factor": 64,      // OpenSCAD $fn resolution factor
    "per_part": 8,        // Added per part in the mode
    "wasm_multiplier": 3, // Multiplier applied to estimates in WASM mode
    "warning_threshold_seconds": 60  // Show confirmation dialog above this estimate
  }
}
```

### Hyperobject Metadata (optional)

Projects can optionally declare `hyperobject` metadata to be classified as **Bounded 4D Hyperobjects** in the Yantra4D Commons:

```jsonc
{
  "hyperobject": {
    "domain": "medical",               // household | industrial | medical | commercial | hybrid
    "cdg_interfaces": [                // Common Denominator Geometry interfaces
      {
        "id": "iso_8037_standard",
        "label": { "en": "ISO 8037 Microscope Slide", "es": "Estándar ISO 8037" },
        "geometry_type": "pocket",     // grid | rail | thread | socket | pocket | snap | bolt_pattern | profile | spline | custom
        "standard": "ISO 8037-1:2003", // ISO/internal standard
        "parameters": ["slide_standard", "custom_slide_length"]  // References to manifest param IDs
      }
    ],
    "material_awareness": {
      "shrinkage_compensation": false,  // Adapts geometry to shrinkage curves
      "recycled_material_toggle": false, // Loosened tolerance for recycled filament
      "tolerance_by_material": true     // Material-specific tolerance profiles
    },
    "societal_benefit": {              // Human-readable commons value statement
      "en": "Enables labs to fabricate precision slide holders",
      "es": "Permite a laboratorios fabricar portaobjetos de precisión"
    },
    "commons_license": "CERN-OHL-W-2.0"  // SPDX license identifier
  }
}
```

**Reference implementations**:
- See `projects/microscope-slide-holder/project.json` for the first hyperobject in the commons.
- See `projects/scara-robotics/project.json` for the benchmark dual-engine parity implementation.

---

## Backend Accessors (`manifest.py`)

The `ProjectManifest` class provides:

| Method | Returns | Description |
|--------|---------|-------------|
| `get_allowed_files()` | `{filename: Path}` | All SCAD files referenced by modes |
| `get_parts_map()` | `{scad_filename: [part_ids]}` | Parts per SCAD file |
| `get_mode_map()` | `{part_id: render_mode_int}` | Render mode integers for OpenSCAD |
| `get_scad_file_for_mode(mode_id)` | `str \| None` | SCAD filename for a mode |
| `get_parts_for_mode(mode_id)` | `[str]` | Part IDs for a mode |
| `calculate_estimate_units(mode_id, params)` | `int` | Unit count for time estimation |
| `as_json()` | `dict` | Raw data for API serialization |

The render route also accepts an optional `export_format` field (`"stl"`, `"3mf"`, `"off"`) in render payloads. OpenSCAD determines the output format from the file extension.

Module-level functions:
- `discover_projects()` — Scan `PROJECTS_DIR` for subdirectories with `project.json`
- `get_manifest(slug=None)` — Load and cache a project manifest by slug (falls back to `SCAD_DIR`)

---

## Frontend Accessors (`ManifestProvider.jsx`)

The `useManifest()` hook provides:

| Property / Method | Description |
|-------------------|-------------|
| `manifest` | Raw manifest object |
| `loading` | `true` while fetching |
| `projectSlug` | `manifest.project.slug` |
| `projects` | List of available projects (`[{slug, name, version}]`) |
| `switchProject(slug)` | Switch to a different project (re-fetches manifest) |
| `getMode(modeId)` | Mode object by ID |
| `getParametersForMode(modeId)` | Parameters visible in that mode |
| `getPartColors(modeId)` | Part definitions (with labels + default colors) for that mode |
| `getDefaultParams()` | `{param_id: default_value}` for all parameters |
| `getDefaultColors()` | `{part_id: default_color}` for all parts |
| `getLabel(obj, key, lang)` | Resolve bilingual label from an object |
| `getCameraViews()` | Array of `{id, label, position}` camera view configs |
| `getGroupLabel(groupId, lang)` | Translated label for a parameter group section |
| `getViewerConfig()` | Viewer settings (e.g., `default_color`) |
| `getEstimateConstants()` | Estimate constants including `wasm_multiplier`, `warning_threshold_seconds` |

Additional hooks for Phase 1 features:

| Hook / Utility | Location | Description |
|----------------|----------|-------------|
| `useShareableUrl({ params, mode, projectSlug, defaultParams })` | `hooks/useShareableUrl.js` | Generates shareable URLs with encoded param diff; `copyShareUrl()` copies to clipboard |
| `getSharedParams()` | `hooks/useShareableUrl.js` | Reads `?p=` query param and decodes shared parameter state |
| `useUndoRedo(initialValue)` | `hooks/useUndoRedo.js` | Returns `[value, setValue, { undo, redo, canUndo, canRedo }]` with 50-entry history |
| `computeVolumeMm3(geometry)` | `lib/printEstimator.js` | Computes STL volume using signed tetrahedra method |
| `computeBoundingBox(geometry)` | `lib/printEstimator.js` | Computes bounding box from Three.js geometry |
| `estimatePrint(volumeMm3, bbox, materialId, overrides)` | `lib/printEstimator.js` | Estimates print time, filament weight/length/cost |
| `getMaterialProfiles()` | `lib/printEstimator.js` | Returns available material profiles (PLA, PETG, ABS, TPU) |

---

## Estimation Formulas

Each mode declares an `estimate` block:

- **`formula: "constant"`**: Uses `base_units` directly (e.g., `1` for unit, `2` for assembly).
- **`formula_vars`** (preferred): When present, the unit count is computed as the product of the named parameter values. For example, `"formula_vars": ["rows", "cols"]` computes `rows × cols`.
- **Legacy `formula: "grid"`**: Equivalent to `formula_vars: ["rows", "cols"]`. Supported for backward compatibility.

The total estimated time is:

```
estimated_seconds = base_time + (num_units × per_unit) + (num_parts × per_part)
```

In WASM mode, this estimate is multiplied by `wasm_multiplier` (default: 3).

If the estimate exceeds `warning_threshold_seconds` (default: 60), a confirmation dialog is shown before rendering.

---

## Adding a New SCAD Project

### Multi-Project Mode (recommended)

1. **Write your `.scad` files** with a `render_mode` parameter convention (integer selects which part to export).
2. **Create a project directory** under `projects/`: `projects/my-project/`
3. **Create `project.json`** in that directory, declaring your modes, parts, parameters, and labels. Validate against `schemas/project-manifest.schema.json`.
4. **Place `.scad` files** in the same directory.
5. **Restart the backend** — the new project appears in `/api/projects` and the frontend project selector.

Alternatively, use the CLI tool: `tools/yantra4d-init <scad-directory> --slug my-project --install`

See [Multi-Project Platform](./multi-project.md) and [Developer Experience Guide](./devx-guide.md) for details.

### Single-Project Mode (legacy)

1. **Set `SCAD_DIR`** environment variable to point at your project directory.
2. **Copy `project.json`** to `apps/studio/src/config/fallback-manifest.json` for offline mode.
3. **Restart the backend**.

No frontend or backend code changes are required in either mode.

### Minimal Template

Ensure your `project.json` follows this root structure. **Common mistake:** defining `name` or `modes` at the top level without the `project` wrapper.

```json
{
  "project": {
    "name": "My Project",
    "slug": "my-project",
    "version": "0.0.1"
  },
  "modes": [],
  "parts": [],
  "parameters": []
}
```

---

## Relationship to Other Docs

- The backend loader is part of the architecture described in [Web Interface](./web_interface.md)
- Verification modes map to manifest mode IDs, as described in [Verification Suite](./verification.md)

[Back to Index](./index.md)
