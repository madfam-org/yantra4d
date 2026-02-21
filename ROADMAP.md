# Yantra4D Architectural Roadmap

This roadmap outlines the strategic path towards a world-class hyperobject commons library, configurator, and visualizer, based on the findings from our [Architecture Audit](./docs/architecture_audit.md).

## Completed Milestones

### Phase 1: Fluid UI via Web Worker Geometry Processing
- [x] **Web Worker Integration:** Moved STL geometry parsing (`STLLoader`) entirely off the main thread into a dedicated Web Worker (`stlWorker.js`).
- [x] **Asynchronous Loader Hook:** Implemented `useWorkerLoader` to seamlessly drop into the React Three Fiber viewer with built-in caching and smooth fallbacks.
- [x] **Zero UI Freezing:** Eliminated browser jitter during complex, high-poly geometry ingestion, allowing sliders and interactive elements to remain 100% fluid.
- [x] **Schema Validation:** Standardized all hyperobject ontology definitions (`project.json`) by integrating robust JSON Schema validation into the CI pipeline.

### Phase 2: Hybrid Compute Architecture (WASM + Cloud Fallback)
- [x] **WASM Execution:** Core CAD engine (OpenSCAD) compiled to WebAssembly for zero-latency client-side generation.
- [x] **Intelligent Cloud Fallback:** Dynamic detection of hardware limitations with automatic routing to backend clusters for complex CadQuery operations.

### Phase 4: glTF 2.0 Viewport Transmission
- [x] **Format Upgrade:** Deprecated STL for active viewport transmission in favor of high-fidelity `glTF`/`GLB`.
- [x] **Rich Assemblies:** Enabled hierarchical structures and material properties, significantly improving visual quality in the Studio environment.

### Phase 5: Monetization & Computational Tiering
- [x] **Tier Enforcements:** Defined usage boundaries (Free, Pro, MadFam) across API and UI level.
- [x] **Premium Gating:** Cloud rendering and high-fidelity CadQuery exports are successfully gated behind authorized tiers.

### Phase 6: The Hyperobjects Commons & CDG Standardization
- [x] **CDG Interface Formalization:** Integrated Common Denominator Geometry interfaces into the manifest schema.
- [x] **Unified Geometry:** Successfully localized shared primitives (e.g. microscope slides) into standalone hyperobjects.

### Phase 7: Live 3D Carousel Gallery
- [x] **Immersive Browsing:** Replaced the flat grid with an interactive 3D carousel.
- [x] **Dynamic LOD:** Smooth transition between optimized thumbnails and live, morphable 3D hyperobjects.

---

### Phase 3: Dual-Kernel Compute Engine (OpenSCAD + CadQuery)
CSG modeling (OpenSCAD) excels at basic primitives but struggles with complex fillets and modern CAD integrations.
- [ ] **Dual Definitions:** Top-tier hyperobjects will be defined in both kernels, allowing the platform to intelligently route generation depending on the requested outcome.
- [ ] **Geometric Parity:** CI pipelines will be upgraded with automated diffing algorithms to ensure perfect parity between the OpenSCAD and CadQuery definitions.

### Phase 8: Visual "3D Git" & Decentralized Ecosystem
To bridge the gap with visual version control platforms while maintaining open-source, decentralized ethos.
- [ ] **Visual Version Control (3D Diffing):** Implement a Three.js-based visual diffing tool that overlays and highlights geometric additions/subtractions between git commits.
- [ ] **Decentralized Instancing:** Enhance the CLI and multi-project tools to allow independent creators to easily spin up and host their own white-labeled Yantra4D nodes, federating the Hyperobjects Commons.
