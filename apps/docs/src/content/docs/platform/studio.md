---
title: Yantra4D Studio
description: Overview of the Studio Editor and Configurator
---

# The Studio App

The Yantra4D `apps/studio` workspace is a cutting-edge React application powered by Vite, providing realtime, zero-latency parametric rendering directly in the browser.

## Browser-Based WASM

By leveraging `openscad-wasm`, the application spawns an Emscripten instance of OpenSCAD natively in an isolated Web Worker. As users slide parametric values (like `Width`, `Height`, or `Teeth Count`), the Studio re-renders the artifact on the fly without touching a backend server.

**This is the default**, not an offline mode: a browser render is free and does not consume any of your hourly render allowance. The server runs the render only when the browser cannot -- a mode built on the CadQuery, graph or implicit engines, a project that declares `render.server_only`, an export format other than STL, a device the capability probe measures as too weak, an estimate over the budget for your device, or your own **Server** choice in the sidebar's placement control. See [Configuring models](/platform/configuring-models/) for that control and what it says about each render.

### Features
1. **Interactive Configurator**: Auto-generates UI sliders, checkboxes, and dials based on a `project.json` manifest.
2. **Monaco Code Editor**: Split-pane architectural display showing the underlying `.scad` layout.
3. **Three.js Renderer**: Implements shadow maps, environmental lighting, and orbit controls via `react-three-fiber` and `drei`.

## When a browser render gives way to the server

Two different things can move a render off your machine, and they happen at different moments.

**Before the render.** The Studio measures your device once (WebAssembly and SIMD support, cores, memory, and a one-shot micro-benchmark in the worker) and caches the result. A cartridge whose estimated browser render exceeds the budget for that class of device -- or a device measured as unable to run the kernel at all -- is sent to the server before any work starts.

**After a failure.** A browser render that dies on memory, a failed worker start-up or a timeout is retried on the server. A render that fails because the *model* is wrong is not: the server would reject the same geometry identically, and retrying would spend one of your render units to be told the same thing. The fallback runs the other way too -- a render that merely *preferred* the server returns to your browser when the API is unreachable.
