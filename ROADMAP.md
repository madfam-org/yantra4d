# Yantra4D Architectural Roadmap

This roadmap outlines the strategic path towards a world-class hyperobject commons library, configurator, and visualizer, based on the findings from our [Architecture Audit](./docs/architecture_audit.md).

## Completed Milestones

### Phase 1: Fluid UI via Web Worker Geometry Processing
- [x] **Web Worker Integration:** Moved STL geometry parsing (`STLLoader`) entirely off the main thread into a dedicated Web Worker (`stlWorker.js`).
- [x] **Asynchronous Loader Hook:** Implemented `useWorkerLoader` to seamlessly drop into the React Three Fiber viewer with built-in caching and smooth fallbacks.
- [x] **Zero UI Freezing:** Eliminated browser jitter during complex, high-poly geometry ingestion, allowing sliders and interactive elements to remain 100% fluid.
- [x] **Schema Validation:** Standardized all hyperobject ontology definitions (`project.json`) by integrating robust JSON Schema validation into the CI pipeline.

---

## The Road Ahead (Towards Excellence)

The following phases define the core architectural transformations required to scale Yantra4D globally with maximum performance and minimal server overhead.

### Phase 2: Hybrid Compute Architecture (WASM + Cloud Fallback)
The primary bottleneck in parametric generation is the client-server rendering loop. 
- **WASM Execution:** We will compile the core CAD engine (e.g., OpenSCAD) to WebAssembly. This allows capable devices (laptops, modern smartphones) to calculate geometry entirely client-side, enabling near real-time interaction (60FPS) and eliminating server rendering costs.
- **Intelligent Cloud Fallback:** For low-powered devices, we will dynamically detect hardware limitations (`hardwareConcurrency`, `deviceMemory`) and route computation requests to a scalable backend server cluster.

### Phase 3: Dual-Kernel Compute Engine (OpenSCAD + CadQuery)
CSG modeling (OpenSCAD) excels at basic primitives but struggles with complex fillets and modern CAD integrations.
- **B-Rep Integration:** We will introduce a CadQuery (OpenCASCADE) kernel alongside OpenSCAD.
- **Dual Definitions:** Top-tier hyperobjects will be defined in both kernels, allowing the platform to intelligently route generation depending on the requested outcome (e.g., OpenSCAD for lightweight mesh, CadQuery for high-fidelity STEP exports).
- **Geometric Parity:** CI pipelines will be upgraded with automated diffing algorithms to ensure perfect parity between the OpenSCAD and CadQuery definitions.

### Phase 4: glTF 2.0 Viewport Transmission
STL is antiquated and lacks native support for colors, materials, and distinct sub-assembly components.
- **Format Upgrade:** We will deprecate STL for viewport transmission in favor of `glTF` or `GLB`.
- **Rich Assemblies:** This will allow hyperobjects to transmit their hierarchical structures and material properties, drastically improving the visual fidelity of the Studio configuration environment.

### Phase 5: Monetization & Computational Tiering
To ensure sustainable development and manage computational expenses from the cloud fallback architecture.
- **Tier Enforcements:** Define clear usage boundaries (e.g., Free, Pro, Enterprise).
- **Premium Features:** Cloud fallback rendering, high-fidelity export generation (STEP, raw scripts), and complex multi-part CadQuery compilations will be gated behind premium tiers, while WASM-based generation remains freely accessible.
