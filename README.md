# Tablaco: Parametric Interlocking Cube

A generative design project creating a 3-walled interlocking cube system optimized for FDM 3D printing.

## Features
-   **Parametric**: Fully adjustable size, thickness, and clearace via OpenSCAD.
-   **Interlocking**: Two identical "Half-Cubes" snap together to form a solid void.
-   **Cantilever Snaps**: Integrated mechanism for secure, repeated assembly.
-   **Tablaco Studio**: A web-based interface for customization and visualization.

## Documentation

Full documentation is available in the [`docs/`](./docs/index.md) directory:

-   [Mechanical Design](./docs/mechanical_design.md)
-   [Verification Suite](./docs/verification.md)
-   [Web Interface](./docs/web_interface.md)

## Usage

### Prerequisites
-   OpenSCAD
-   Python 3 (trimesh, flask)
-   Node.js (for Web Interface)

### Quick Run
Generate the default model:
```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o models/half_cube.stl half_cube.scad
```
