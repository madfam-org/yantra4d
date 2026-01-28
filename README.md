# Tablaco: Parametric Interlocking Cube

A generative design project creating a 3-walled interlocking cube system optimized for FDM 3D printing.

![Tablaco Studio](/docs/images/half_cube_iso.png)

## Features
-   **Parametric**: Fully adjustable size, thickness, and clearance via OpenSCAD.
-   **Interlocking**: Two identical "Half-Cubes" snap together to form a solid void.
-   **Cantilever Snaps**: Integrated mechanism for secure, repeated assembly.
-   **Grid Assembly**: Generate arrays of cubes with configurable rows, columns, and connecting rods.
-   **Tablaco Studio**: A web-based interface for customization and visualization.
    -   **Two Modes**: Unit Design (`half_cube.scad`) and Grid Design (`tablaco.scad`).
    -   **Theme Toggle**: Light, Dark, and System (Auto) modes.
    -   **Bilingual UI**: Spanish (default) and English.
    -   **Export**: Download STL files and capture images (Iso, Top, Front, Right).

## Documentation

Full documentation is available in the [`docs/`](./docs/index.md) directory:

-   [Mechanical Design](./docs/mechanical_design.md)
-   [Verification Suite](./docs/verification.md)
-   [Web Interface](./docs/web_interface.md)

## Tech Stack
-   **CAD**: OpenSCAD
-   **Backend**: Python 3 (Flask, trimesh)
-   **Frontend**: React (Vite), Tailwind CSS, Shadcn UI, Three.js

## Usage

### Prerequisites
-   OpenSCAD
-   Python 3 (trimesh, flask, flask-cors)
-   Node.js (v18+)

### Quick Run
Generate the default model:
```bash
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o models/half_cube.stl half_cube.scad
```

### Launching Tablaco Studio
```bash
# Terminal 1: Backend
python3 web_interface/backend/app.py

# Terminal 2: Frontend
cd web_interface/frontend
npm install  # First time only
npm run dev
```
Open http://localhost:5173

