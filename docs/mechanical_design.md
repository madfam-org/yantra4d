# Mechanical Design Documentation

The core of the Tablaco project is the **Parametric Half-Cube** (`half_cube.scad`), a 3-walled interlocking component designed for FDM 3D printing.

## File: `half_cube.scad`

This OpenSCAD script defines a single "Half-Cube" which, when printed twice and rotated 180 degrees, forms a complete 20mm cube.

### Parameters

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `size` | `20.0` | The outer dimension of the cube (mm). |
| `thick` | `2.5` | Wall thickness. Includes base and side walls. |
| `rod_D` | `6.0` | Diameter of the central rod hole (not currently used for interlocking but defined). |
| `clearance` | `0.2` | General clearance for bores. |
| `fit_clear` | `0.1` | **Critical**: Physical clearance gap applied to miter faces to ensure assembly. |
| `show_base` | `true` | Toggle visibility of the Base Plate. |
| `show_walls` | `true` | Toggle visibility of Side Walls. |
| `show_mech` | `true` | Toggle visibility of the Snap Mechanism. |

### Modules

#### 1. `base_plate()`
-   **Geometry**: Inverted Pyramid / Dovetail shape.
-   **Function**: Forms the floor of the U-channel.
-   **Design Note**: The simple trapezoid was inverted to ensuring the top surface (where walls meet) is wide enough to support the full wall thickness.
-   **Clearance**: Y-faces are shaved by `fit_clear` to prevent collision with the mating part's walls.

#### 2. `mitered_wall_left()` / `mitered_wall_right()`
-   **Geometry**: Vertical walls with 45-degree miter cuts on Top, Front, and Back faces.
-   **Function**: Interlocks with the mating half's walls.
-   **Clearance**: Miter cuts are offset deeper by `fit_clear`.

#### 3. `mechanism()`
-   **Geometry**: Central cylindrical shaft with cantilever snaps.
-   **Function**: Locks the two halves together.
-   **Integration**: Uses a "Union-Then-Subtract" approach to fuse the snaps to the shaft, preventing mesh disconnection.
-   **Features**:
    -   **Snaps**: True cantilever heads with a 1.5mm relief slot cut through them.
    -   **Sinking**: The snap heads are sunk 0.1mm into the shaft to force a valid boolean union.

#### 4. `welds()`
-   **Geometry**: Small hidden cubes at internal intersections.
-   **Purpose**: Forces OpenSCAD to recognize the assembly as a single connected volume ("Volumes: 1") by bridging any potential arithmetic gaps between primitives.

[Back to Index](./index.md)
