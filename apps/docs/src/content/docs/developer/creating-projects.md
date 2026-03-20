---
title: Creating Projects
description: How to onboard your own OpenSCAD projects into Yantra4D — manifest structure, CLI tool, and web wizard.
---

Every Yantra4D project lives in a directory under `projects/` and is defined by a `project.json` manifest file. This guide walks through three ways to create a project: the CLI analyzer, the web wizard, and manual setup.

## Project structure

A minimal project looks like this:

```
projects/my-project/
  project.json          # Manifest (required)
  main.scad             # OpenSCAD geometry (at least one)
  exports/              # Reference STL exports (optional)
  docs/                 # Project documentation (optional)
```

The platform auto-discovers any subdirectory of `projects/` that contains a `project.json`.

## Option 1: CLI analyzer

The `yantra4d-init` script analyzes your SCAD files and generates a draft manifest:

```bash
# Analyze only (preview what will be generated)
scripts/yantra4d-init /path/to/your/scad --slug my-project --analyze-only

# Generate manifest and install into projects/
scripts/yantra4d-init /path/to/your/scad --slug my-project --install
```

### What the analyzer detects

| SCAD pattern | Result in manifest |
|---|---|
| `width = 50;` | Slider parameter (range: 25-100, step auto) |
| `show_base = true;` | Checkbox parameter |
| `label = "A";` | Text input parameter |
| `if (render_mode == 1)` | Part with `render_mode: 1` |
| `include <file.scad>` | Dependency tracked |
| `module name(...)` | Documented in analysis output |

The analyzer sets parameter ranges to `value * 0.5` (min) and `value * 2.0` (max) by default. Adjust these manually after generation.

## Option 2: Web wizard

The studio includes an onboarding wizard accessible from the project gallery:

1. Click **New Project** in the project selector.
2. Upload your `.scad` files.
3. The backend analyzes the files and presents a draft manifest.
4. Review and edit parameter ranges, labels, and modes.
5. Save to create the project in `projects/`.

The web wizard uses the same analysis engine as the CLI.

## Option 3: Manual setup

Create the directory and write `project.json` by hand. This gives you full control over every field.

### Minimal manifest

```json
{
  "project": {
    "name": "My Widget",
    "slug": "my-widget",
    "version": "1.0.0"
  },
  "modes": [
    {
      "id": "default",
      "scad_file": "widget.scad",
      "label": { "en": "Default" },
      "parts": ["body"],
      "estimate": {
        "base_units": 1,
        "formula": "constant"
      }
    }
  ],
  "parts": [
    {
      "id": "body",
      "render_mode": 0,
      "label": { "en": "Body" },
      "default_color": "#4a90d9"
    }
  ],
  "parameters": [
    {
      "id": "width",
      "type": "slider",
      "default": 40,
      "min": 10,
      "max": 100,
      "step": 1,
      "label": { "en": "Width (mm)" }
    }
  ],
  "estimate_constants": {
    "base_time": 5,
    "per_unit": 1.5,
    "per_part": 8,
    "wasm_multiplier": 3
  }
}
```

### Required fields

| Field | Type | Purpose |
|---|---|---|
| `project.name` | string | Display name in the gallery and header |
| `project.slug` | string | URL-safe identifier (lowercase, hyphens) |
| `modes` | array | At least one mode with `id`, `scad_file`, and `parts` |
| `parts` | array | At least one part with `id`, `render_mode`, and `default_color` |
| `parameters` | array | Can be empty, but usually has at least one slider |
| `estimate_constants` | object | Render time estimation coefficients |

## Adding parameters

Each parameter entry defines a UI control and a value passed to the SCAD file during rendering:

```json
{
  "id": "num_slots",
  "type": "slider",
  "default": 4,
  "min": 1,
  "max": 20,
  "step": 1,
  "label": { "en": "Number of Slots", "es": "Cantidad de Ranuras" },
  "tooltip": { "en": "How many slots to generate" },
  "group": "dimensions",
  "visible_in_modes": ["tray", "box"]
}
```

### Parameter types

| Type | UI control | Extra fields |
|---|---|---|
| `slider` | Numeric slider | `min`, `max`, `step` |
| `checkbox` | Toggle switch | `default` (boolean) |
| `text` | Text input | `maxlength` |

### Visibility control

- **`visible_in_modes`**: Array of mode IDs where this parameter appears. Omit to show in all modes.
- **`visibility_level`**: Set to `"advanced"` to hide behind the Basic/Advanced toggle. Default is `"basic"`.
- **`parent`**: ID of a parent parameter. The child is only visible when the parent checkbox is checked.

## Adding modes

Each mode maps to a SCAD file and defines which parts to render:

```json
{
  "id": "staining_rack",
  "scad_file": "staining_rack.scad",
  "label": { "en": "Staining Rack", "es": "Bastidor de Tincion" },
  "parts": ["rack"],
  "estimate": {
    "base_units": 1,
    "formula": "constant"
  }
}
```

For grid-based models where render complexity scales with parameters:

```json
{
  "id": "grid",
  "scad_file": "grid.scad",
  "parts": ["cup", "baseplate"],
  "part_quantities": {
    "cup": "rows * cols",
    "baseplate": "1"
  },
  "estimate": {
    "formula": "grid",
    "formula_vars": ["rows", "cols"]
  }
}
```

Quantity formulas can reference any parameter ID and are evaluated client-side using `expr-eval`.

## Adding presets

Presets provide one-click parameter configurations:

```json
{
  "grid_presets": {
    "small": {
      "label": { "en": "Small (2x1)" },
      "values": { "width_units": 2, "depth_units": 1 }
    },
    "large": {
      "label": { "en": "Large (4x4)" },
      "values": { "width_units": 4, "depth_units": 4 }
    },
    "default": "small"
  }
}
```

## Adding BOM (Bill of Materials)

Define hardware items with quantity formulas:

```json
{
  "bom": {
    "hardware": [
      {
        "id": "magnets_6x2",
        "label": { "en": "N52 6x2mm Magnets" },
        "quantity_formula": "enable_magnets ? 4 : 0",
        "unit": "pcs",
        "supplier_url": "https://example.com/magnets"
      }
    ]
  }
}
```

Quantity formulas are evaluated with the current parameter values, so BOM quantities update as users adjust sliders.

## SCAD file conventions

For the analyzer and platform to work optimally, follow these patterns in your SCAD files:

### render_mode variable

Use an integer `render_mode` to control which part is rendered:

```scad
render_mode = 0; // 0=all, 1=base, 2=lid

if (render_mode == 0 || render_mode == 1) {
    // Base geometry
}
if (render_mode == 0 || render_mode == 2) {
    // Lid geometry
}
```

### Parameterizable variables

Declare variables at the top of the file with default values:

```scad
width = 50;       // Becomes a slider
height = 30;      // Becomes a slider
show_base = true; // Becomes a checkbox
```

Inline comments after variable declarations become tooltip text in the generated manifest.

## Post-generation checklist

After generating a manifest (via CLI or web wizard), review these items:

- [ ] **Parameter ranges** -- auto-generated as `value * 0.5` to `value * 2.0`. Adjust to meaningful limits.
- [ ] **Labels** -- auto-generated from variable names. Add human-readable labels and translations.
- [ ] **Mode-parameter mapping** -- restrict parameters to relevant modes with `visible_in_modes`.
- [ ] **Camera views** -- add positions that showcase the model well.
- [ ] **Estimate tuning** -- adjust `base_time`, `per_unit`, `per_part` for your geometry complexity.
- [ ] **Presets** -- add useful default configurations.
- [ ] **Part colors** -- set distinct, meaningful default colors.

## Validating the manifest

Check your manifest against the JSON Schema:

```bash
ajv validate -s packages/schemas/project-manifest.schema.json \
  -d projects/my-project/project.json
```

## Testing locally

Start the development servers and verify your project appears:

```bash
./scripts/dev.sh
# Open http://localhost:5173 -- your project should appear in the selector
```
