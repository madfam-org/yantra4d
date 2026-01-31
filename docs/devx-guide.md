# Developer Experience Guide

How to bring your own SCAD project into the Tablaco platform.

## Quick Start

```bash
# 1. Clone tablaco
git clone <repo-url> && cd tablaco

# 2. Analyze your SCAD files
scripts/tablaco-init /path/to/your/scad --slug my-project --analyze-only

# 3. Review the output, then generate + install
scripts/tablaco-init /path/to/your/scad --slug my-project --install

# 4. Start the platform
./scripts/dev.sh

# 5. Open browser — your project appears in the project selector
```

## What the Analyzer Detects

| Feature | Detection Method |
|---------|-----------------|
| **Numeric variables** | `name = 123;` → slider parameter |
| **Boolean variables** | `name = true;` → checkbox parameter |
| **String variables** | `name = "V";` → text input |
| **Modules** | `module name(params)` → documented in analysis |
| **Includes/Uses** | `include <file>` / `use <file>` → dependency graph |
| **Render modes** | `if (render_mode == N)` → parts with IDs |
| **Entry points** | Files with render_mode usage or not included by others |

## Manifest Conventions

For best results, follow these patterns in your SCAD files:

### render_mode Convention

```scad
render_mode = 0; // 0=all, 1=partA, 2=partB, ...

if (render_mode == 0 || render_mode == 1) {
    // Part A geometry
}
if (render_mode == 0 || render_mode == 2) {
    // Part B geometry
}
```

### Parameterizable Variables

```scad
size = 20;        // Will become a slider (range: 10–40)
thick = 2.5;      // Will become a slider (range: 1.25–5.0)
show_base = true; // Will become a checkbox
letter = "A";     // Will become a text input
```

### Inline Comments

```scad
gap = 2; // Gap between units (mm)
```
Comments after variables become tooltip text in the generated manifest.

## Generated Manifest

The analyzer produces a `project.json` with:

- **Modes**: One per entry-point SCAD file
- **Parts**: One per detected render_mode value
- **Parameters**: Sliders for numbers, checkboxes for booleans, text for strings
- **Ranges**: `min = value × 0.5`, `max = value × 2.0` (adjust manually)
- **Default camera views**: Isometric + front (add more manually)
- **Default estimate constants**: Generic values (tune for your geometry)

## Post-Generation Checklist

After generating `project.json`, review and improve:

- [ ] Parameter min/max ranges — auto-generated from defaults, may need tuning
- [ ] Parameter labels — auto-generated from variable names, add human-readable labels
- [ ] Parameter `visible_in_modes` — restrict parameters to relevant modes
- [ ] Camera views — add views that best showcase your model
- [ ] Estimate formula — tune `base_time`, `per_unit`, `per_part` for your geometry complexity
- [ ] Presets — add useful parameter presets for common configurations
- [ ] Colors — set meaningful default colors for each part

## Schema Validation

Validate your manifest against the JSON Schema:

```bash
# Using ajv-cli or any JSON Schema validator
ajv validate -s schemas/project-manifest.schema.json -d projects/my-project/project.json
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No variables detected | Ensure variables use `name = value;` format (not inside modules) |
| No render_modes | Add `render_mode = 0;` and `if (render_mode == N)` patterns |
| Missing files | Check `include <file>` paths are relative to the project directory |
| Wrong parameter types | Edit the generated `project.json` manually |
