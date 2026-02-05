# Tablaco: Parametric Interlocking Cube

A generative design project creating a 3-walled interlocking cube system optimized for FDM 3D printing.

![Tablaco Studio](/docs/images/half_cube_iso.png)

## Features
-   **Parametric**: Fully adjustable size, thickness, and clearance via OpenSCAD.
-   **Interlocking**: Two identical "Half-Cubes" snap together to form a solid void.
-   **Cantilever Snaps**: Integrated mechanism for secure, repeated assembly.
-   **Grid Assembly**: Generate arrays of cubes with configurable rows, columns, and connecting rods.

## Quick Start

Generate the default model:
```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o projects/tablaco/exports/models/half_cube.stl projects/tablaco/half_cube.scad
```

## Documentation

- [Mechanical Design](./docs/mechanical_design.md) — OpenSCAD geometry, parameters, snap-fit modules
- [Platform README](../../README.md) — Platform usage, Docker, dev setup
- [Platform Docs](../../docs/index.md) — Manifest schema, web interface, verification
