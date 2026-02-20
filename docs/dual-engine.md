# Dual-Engine Architecture: OpenSCAD & CadQuery

Yantra4D implements a **Dual-Engine Model Strategy** to bridge the gap between hobbyist maker culture and industrial manufacturing.

## The Engines

### OpenSCAD (CSG)
- **Role**: Client-side visualization, rapid prototyping, and web-ready parametric previews.
- **Technology**: Constructive Solid Geometry (CSG) rendered via WASM in the browser or via CLI on the backend.
- **Output**: STL / WebGL meshes.

### CadQuery (B-Rep)
- **Role**: Industrial manufacturing, professional engineering, and simulation.
- **Technology**: Boundary Representation (B-Rep) powered by OpenCASCADE.
- **Output**: STEP files, high-precision BREP geometry.

## Why Both?

Maintaining two parallel implementations of the same geometry provides several critical advantages:

1. **Performance vs. Precision**: OpenSCAD provides the sub-second visual feedback needed for web-based "design-as-you-type." CadQuery provides the mathematical precision needed for CNC milling and injection molding.
2. **Double-Entry Verification**: Just as in accounting, having two independent logical paths to the same physical result acts as a "Proof of Geometry." A bug in the math of one engine is rarely duplicated in the other.
3. **Ecosystem Access**: OpenSCAD gives us access to a decade of community libraries (`BOSL2`). CadQuery gives us access to the entire Python ecosystem (`NumPy`, `SciPy`, Machine Learning).

## The Geometric Parity Guarantee

For a project to reach **Hyperobject Status**, it must maintain strict parity between its OpenSCAD and CadQuery definitions.

- **Verification**: The `scripts/verify_parity.py` CI script renders both engines and compares the resulting 3D volumes.
- **Tolerance**: High-precision surface checks (Hausdorff distance) ensure that the two models never diverge by more than **0.001mm**.
- **Requirement**: The Yantra4D manifest schema strictly enforces the presence of both `.scad` and `.py` source files for all Hyperobjects.

## Benefits for the Commons

- **Trust**: Users can manufacture Yantra4D designs knowing they have been mathematically verified across two different CAD paradigms.
- **Interoperability**: Standardized "External Interfaces" are verified to match identically in both Mesh and B-Rep formats, ensuring hardware always fits.
- **Longevity**: By not being tied to a single CAD engine, Yantra4D designs are resilient to the obsolescence of any single tool or library.
