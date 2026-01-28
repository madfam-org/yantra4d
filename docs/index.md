# Tablaco Project Documentation

Welcome to the documentation for the Tablaco Interlocking Cube project.

## Documentation Index

-   [Mechanical Design](./mechanical_design.md): Details of the Parametric Half-Cube (`half_cube.scad`), geometry topology, and clearance strategies.
-   [Verification Suite](./verification.md): Explanation of the automated testing suite (`verify_design.py`) including watertightness and assembly collision checks.
-   [Web Interface](./web_interface.md): Full-stack architecture (Flask/React) of the "Tablaco Studio" customization app.

## Quick Start

### 1. Generating Models
```bash
# Standard Model
/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD -o models/half_cube.stl half_cube.scad
```

### 2. Running Verification
```bash
python3 tests/verify_design.py
```

### 3. Launching Tablaco Studio
```bash
# Terminal 1
python3 web_interface/backend/app.py

# Terminal 2
cd web_interface/frontend
npm run dev
```
Open http://localhost:5173
