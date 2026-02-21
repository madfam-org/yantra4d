---
title: Yantra4D Studio
description: Overview of the Studio Editor and Configurator
---

# The Studio App

The Yantra4D `apps/studio` workspace is a cutting-edge React application powered by Vite, providing realtime, zero-latency parametric rendering directly in the browser.

## Browser-Based WASM
By leveraging `openscad-wasm`, the application spawns an Emscripten instance of OpenSCAD natively in an isolated Web Worker. As users slide parametric values (like `Width`, `Height`, or `Teeth Count`), the Studio application instructs the WASM buffer to re-render the artifact on the fly without ever touching a backend server.

### Features
1. **Interactive Configurator**: Auto-generates UI sliders, checkboxes, and dials based on a `project.json` manifest.
2. **Monaco Code Editor**: Split-pane architectural display showing the underlying `.scad` layout.
3. **Three.js Renderer**: Implements shadow maps, environmental lighting, and orbit controls via `react-three-fiber` and `drei`.

## Memory Optimizations
If a mesh reaches massive geometric densities, the local WASM instance intelligently aborts the operation and queues it into the heavy-duty Docker API cluster instead.
