# Project Manifest

The project manifest (`projects/{slug}/project.json`) is the single source of truth for modes, parameters, parts, colors, labels, and estimation formulas. Both the backend and frontend consume it, making the webapp fully data-driven and project-agnostic. A formal JSON Schema is available at `schemas/project-manifest.schema.json`.

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
    "name": "Tablaco Studio",     // Display name (used in header)
    "slug": "tablaco",            // Used for localStorage keys, export filenames
    "version": "1.0.0"
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
      "type": "slider",                     // "slider" or "checkbox"
      "default": 20.0,
      "min": 10, "max": 50, "step": 0.5,   // Slider range (ignored for checkboxes)
      "label": { "en": "Size (mm)", "es": "Tamaño (mm)" },
      "tooltip": { "en": "...", "es": "..." },
      "description": { "en": "...", "es": "..." },  // Optional, shown below slider
      "group": "visibility",                // Optional grouping (renders with header)
      "visibility_level": "basic",           // Optional: "basic" (default) or "advanced"
      "parent": "show_walls",               // Optional: parent param ID (for hierarchy)
      "visible_in_modes": ["unit", "assembly"]  // Which modes show this parameter
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

Alternatively, use the CLI tool: `scripts/tablaco-init <scad-directory> --slug my-project --install`

See [Multi-Project Platform](./multi-project.md) and [Developer Experience Guide](./devx-guide.md) for details.

### Single-Project Mode (legacy)

1. **Set `SCAD_DIR`** environment variable to point at your project directory.
2. **Copy `project.json`** to `web_interface/frontend/src/config/fallback-manifest.json` for offline mode.
3. **Restart the backend**.

No frontend or backend code changes are required in either mode.

---

## Relationship to Other Docs

- The manifest defines the modes documented in [Mechanical Design](../projects/tablaco/docs/mechanical_design.md)
- The backend loader is part of the architecture described in [Web Interface](./web_interface.md)
- Verification modes map to manifest mode IDs, as described in [Verification Suite](./verification.md)

[Back to Index](./index.md)
