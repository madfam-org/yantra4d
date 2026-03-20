---
title: Configuring Models
description: How to use the Yantra4D Studio to select projects, adjust parameters, apply presets, and share configurations.
---

The Yantra4D Studio is a browser-based configurator that lets you adjust parametric 3D models in real time. This guide covers the core workflows.

## Selecting a project

Open the studio at your deployment URL (or `localhost:5173` during local development). The project selector dropdown in the header lists all available projects. Each project appears with its name, thumbnail, and difficulty level.

Click a project to load it. The studio fetches the project manifest and generates the parameter controls, mode tabs, and 3D viewer automatically.

## Choosing a mode

Many projects offer multiple **modes** -- distinct variants of the same model. For example, a microscope slide holder project might have modes for "Storage Box", "Horizontal Tray", "Staining Rack", and "Cabinet Drawer".

Mode tabs appear below the header. Switching modes can change:

- Which parameters are visible (each parameter can be restricted to specific modes)
- Which parts are rendered in the viewport
- The underlying SCAD file used for rendering

## Adjusting parameters

Parameters appear in the sidebar as interactive controls:

- **Sliders** for numeric values (width, height, count, thickness). Each slider shows its current value, minimum, maximum, and step size.
- **Checkboxes** for boolean toggles (show base, enable magnets, stackable).
- **Text inputs** for string values (custom labels, engraving text).
- **Color pickers** for part colors.
- **Component pickers** for selecting hardware from a catalog (e.g., ball bearings from NopSCADlib).

### Parameter groups

Parameters are organized into named groups with collapsible section headers. Some groups support a **Basic/Advanced** toggle that hides less common parameters until you need them.

### Constraints

Some projects define cross-parameter constraints. For example, a grid storage project might limit the total cell count (`width_units * depth_units <= 24`). When you violate a constraint, the studio shows a warning or blocks the render, depending on the severity.

### Hover preview

When you hover over a parameter control, the 3D viewer shows a visual hint of what that parameter affects:

- Dimensional parameters (width, height, depth) display directional arrows along the affected axis with min/max labels.
- Other parameters highlight the affected parts with an amber glow.
- If cached geometry variants exist, semi-transparent ghost meshes appear showing the model at its minimum and maximum values.

## Using presets

Projects can define **presets** -- saved parameter combinations for common use cases. Presets appear as buttons above the parameter controls. Click a preset to apply its values instantly.

Examples of presets:

- "Quick Preview" -- small, fast-rendering configuration for exploring parameters
- "Large Grid" -- full-size manufacturing configuration
- "Custom" -- your current values (active when parameters differ from any preset)

## Rendering

The studio renders your model automatically when you change parameters. Two rendering paths are available:

1. **WASM (client-side).** OpenSCAD runs in your browser via WebAssembly. Fast for simple models, no server needed.
2. **Backend.** The server renders using native OpenSCAD or CadQuery. Handles complex geometry and additional export formats.

If the backend is unreachable, the studio falls back to WASM automatically. Some projects with `force_backend: true` prefer server rendering but will still fall back to WASM if the server is down.

A progress indicator shows estimated render time. For models with long render times (above the project's warning threshold), a confirmation dialog appears before starting.

## 3D viewer controls

The Three.js viewer supports:

| Action | Mouse | Keyboard |
|--------|-------|----------|
| Orbit | Left-click drag | -- |
| Pan | Right-click drag | -- |
| Zoom | Scroll wheel | -- |
| Toggle orthographic camera | -- | `O` |
| Toggle clipping plane | -- | `C` |
| Toggle measure tool | -- | `M` |
| Toggle sidebar | -- | `[` |
| Toggle console | -- | `]` |
| Keyboard shortcut help | -- | `?` |

### Camera views

Projects can define named camera positions (isometric, front, top, etc.). Camera view buttons appear in the viewer toolbar.

### Inspection tools

- **Clipping plane.** Cross-section view with axis selector and position slider.
- **Measure tool.** Click two points on the model to measure the distance between them.
- **Wall thickness analysis.** Heatmap overlay showing thin-wall regions (Pro tier).
- **Overhang analysis.** Color-coded overlay showing overhang angles relative to the build plate (Pro tier).
- **Exploded view.** Displacement slider separating multi-part assemblies.
- **Model info panel.** Dimensions, volume, triangle count, and part count.

## Sharing a configuration

To share your current parameter choices:

1. Click the share button in the header.
2. The studio generates a URL encoding your non-default parameters as a compact base64url query string.
3. Copy the URL and send it to anyone.

When someone opens the link, the studio loads the project with your exact parameter values pre-applied.

The URL format is: `/project/{slug}/share/{mode}?p={encoded_params}`

## Undo and redo

Parameter changes support undo/redo:

- **Undo**: `Cmd+Z` (macOS) or `Ctrl+Z` (Windows/Linux)
- **Redo**: `Cmd+Shift+Z` or `Ctrl+Shift+Z`

The history stack holds up to 50 entries. Any new parameter change clears the redo stack.

## Unit system

The studio defaults to millimeters. You can toggle to inches using the unit system control. This is a display-only conversion -- all underlying values and exports remain in millimeters.
