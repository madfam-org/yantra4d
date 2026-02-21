# Changelog

All notable changes to the Yantra4D Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **glTF 2.0 Export Pipeline**: Integrated `cascadio` parsing so CadQuery now defaults to exporting pristine `.glb` representations instead of relying on CadQuery's native experimental `.gltf` writer.
- **WASM Component Tests**: Vitest integrated to enforce safety of React components on the landing page specifically for Astro islands (`ProjectGalleryGrid`, `InteractiveShowcase`).
- **Telemetry Module**: Integrated core MQTT subscriptions via `paho-mqtt` alongside `cadquery_engine.py` parametric generation.
- **Premium Tier Protections**: Render endpoint strictly blocks unauthenticated or tier-less users from generating expensive STEP/GLB file payloads.

### Changed
- **Web Worker Geometry Fetcher**: Caching layer updated from buffering geometry directly to caching JavaScript Promises. Simultaneous part fetching requests are now perfectly coalesced with no race conditions or redundant thread spawns.
- **Worker Execution Offload**: Refactored `assemblyFetcher.js` to dispatch rendering payloads to a Web Worker, preventing main thread deadlocking during heavy JSON loading.
- **Strict Manifest Discovery**: The project discovery pipeline in `manifest.py` now guarantees all objects must feature complete `thumbnail`, `tags`, and `difficulty` descriptors to be indexed by the platform.

### Removed
- **Redundant Roadmaps**: Cleaned up the `/docs` folder by removing the secondary `roadmap.md` and merging tasks into the root.
