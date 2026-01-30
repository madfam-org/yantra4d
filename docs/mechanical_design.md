# Mechanical Design Documentation

The core of the Tablaco project is the **Parametric Half-Cube** (`scad/half_cube.scad`), a 3-walled interlocking component designed for FDM 3D printing.

---

## File: `scad/half_cube.scad`

This OpenSCAD script defines a single "Half-Cube" which, when printed twice and rotated 180 degrees, forms a complete 20mm cube.

### Parameters

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `size` | `20.0` | The outer dimension of the cube (mm). |
| `thick` | `2.5` | Wall thickness. Includes base and side walls. |
| `rod_D` | `3.0` | Diameter of the central rod hole. Used for grid assembly rods. |
| `clearance` | `0.2` | General clearance for bores. |
| `fit_clear` | `0.2` | **Critical**: Physical clearance gap applied to miter faces to ensure assembly. |
| `show_base` | `true` | Toggle visibility of the Base Plate. |
| `show_walls` | `true` | Toggle visibility of Side Walls. |
| `show_mech` | `true` | Toggle visibility of the Snap Mechanism. |
| `show_letter` | `true` | Toggle visibility of the embossed/carved letter. |
| `is_flipped` | `false` | Flip mode for top unit (rotates mechanism, inverts letter). |

### Design Constants (not UI-exposed)

The following parameters are defined in `half_cube.scad` but are intentionally **not exposed** in the web UI or project manifest. They are design constants tuned for the current geometry:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `clearance` | `0.2` | General clearance for rod bores (mm). |
| `fit_clear` | `0.2` | Miter face clearance gap for assembly fit (mm). |
| `letter` | `"V"` / `"F"` | Letter character (V for bottom, F for top unit). |
| `letter_emboss` | `false` | `true` = raised letter, `false` = carved letter. |
| `letter_depth` | `0.5` | Depth/height of letter emboss/carve (mm). |
| `letter_size` | `6` | Font size of the letter (mm). |

### Snap-Fit Parameters

These constants scale with `scale_factor = size / 20` and have minimum-value guards:

| Parameter | Formula | Min | Description |
| :--- | :--- | :--- | :--- |
| `snap_beam_len` | `6.0 * scale_factor` | `1.5` | Cantilever beam length |
| `snap_beam_width` | `3.0 * scale_factor` | `0.8` | Beam width |
| `snap_beam_thick` | `1.2 * scale_factor` | `0.4` | Beam thickness |
| `snap_undercut` | `0.6 * scale_factor` | `0.15` | Undercut depth on snap head |
| `snap_head_len` | `1.5 * scale_factor` | `0.4` | Length of snap head |
| `snap_relief_w` | `1.5 * scale_factor` | `0.3` | Relief slot width |
| `snap_relief_d` | `0.8 * scale_factor` | `0.2` | Relief slot depth into head |
| `snap_sink` | `0.1` | — | Head sunk into shaft for boolean union |

### Derived Geometry Constants

| Parameter | Formula | Description |
| :--- | :--- | :--- |
| `cyl_R` | `size * 0.15 + rod_D/2 + clearance + 1` | Mechanism cylinder radius, parametric |
| `cyl_H` | `size - thick - fit_clear` | Cylinder/pillar height (full interleaving height) |
| `weld` | `0.4` | Weld cube size for boolean connectivity |

All togglable parameters (`show_base`, `show_walls`, `show_mech`) and dimensional parameters (`size`, `thick`, `rod_D`) are declared in the [project manifest](./manifest.md) and exposed in the web UI for the Unit and Assembly modes.

### Modules

#### 1. `base_plate(flipped)`
-   **Geometry**: Rectangular slab with quarter-circle perforations for opposing mechanism pass-through.
-   **Function**: Forms the floor of the U-channel; perforations allow the mating half's mechanism pillars to extend through.
-   **Clearance**: XY faces are shaved by `fit_clear`; perforations sized at `cyl_R + fit_clear`.

#### 2. `mitered_wall()` (mirrored for left/right)
-   **Geometry**: Full-height vertical wall (`size - fit_clear` tall) with 45° miter on top edge and full-height 45° chamfers on front/back corners.
-   **Function**: Interlocks with the mating half's perpendicular walls. Bottom half walls sit on X-faces, top half walls on Y-faces after assembly rotation — no wall-to-wall collision.
-   **Clearance**: Miter cuts offset by `fit_clear`. Corner miters resolve the `thick×thick` overlap at the 4 vertical corners.
-   **Usage**: Called once directly (left wall) and once with `mirror([1,0,0])` (right wall).

#### 3. `mechanism_pillars(flipped)`
-   **Geometry**: Central cylindrical mechanism with snap-fit locking.
-   **Function**: Locks the two halves together.
-   **Structure**:
    -   Base ring (`cylinder(r=cyl_R, h=base_ring_h)`)
    -   Two opposing quadrant pillars with wedge cuts (90° sectors)
    -   4 snap beams via `snap_beam_at(angle, pillar_height)` at 45°, 135°, 225°, 315°
    -   Snap heads with undercut and relief slots via `snap_head()`
    -   Weld cubes at base and top junctions for boolean connectivity
-   **Flip**: When `flipped=true`, the mechanism is rotated 180° on X so snap beams engage from the opposite direction.

#### 4. `snap_beam_at(angle, pillar_height)`
-   **Geometry**: Single cantilever beam with tapered profile and snap head.
-   **Function**: Provides the deflection and locking action for snap-fit assembly.

#### 5. `snap_head()`
-   **Geometry**: Overhanging head with undercut ramp and relief slot.
-   **Function**: Creates the locking barb that catches on the mating cylinder bore.

#### 6. `letter_geometry(flipped, side)`
-   **Geometry**: Extruded text character on wall surface.
-   **Function**: Embosses or carves a letter on both left and right walls.
-   **Mirror logic**: Right wall text is mirrored so it reads correctly from the outside.

---

## File: `scad/assembly.scad`

This script generates a **single interlocking cube** by combining two half-cubes. It is the source file for the **Assembly** mode in the web interface.

### Parameters

Inherits `size`, `thick`, and `rod_D` from `half_cube.scad` via command-line defines.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `render_mode` | `0` | `0` = all parts, `1` = bottom only, `2` = top only |

### Assembly Logic

- **Part A (Bottom)**: The half-cube in its default orientation.
- **Part B (Top)**: The same half-cube rotated 180° around X and 90° around Z, positioned to interlock.

The web interface renders bottom and top as separate STL files (using `render_mode` 1 and 2) so they can be colored independently.

---

## File: `scad/tablaco.scad`

This script generates a **grid assembly** of full cubes, including vertical rods and stopper rails.

### Parameters

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `rows` | `8` | Number of rows in the grid (vertical). |
| `cols` | `8` | Number of columns in the grid (horizontal). |
| `rod_extension` | `10` | How far the rods protrude beyond the stoppers (mm). 0 = flush. |

These parameters are declared in the [project manifest](./manifest.md) and exposed in the web UI for the Grid mode.

### Modules

#### 1. `full_cube()`
-   Combines two `assembly()` calls (from `half_cube.scad`), one rotated 180 degrees, to form a complete interlocking cube.

#### 2. `stopper_rail()`
-   A horizontal bar placed at the top and bottom of the grid.
-   Contains holes matching `rod_D` for the vertical rods to pass through.
-   Acts as a structural cap for the assembly.

#### 3. `vertical_rod()`
-   A simple cylinder with diameter `rod_D`.
-   Length is dynamically calculated: `(rows * size) + (2 * rail_H) + (2 * rod_extension)`.

### Assembly Logic
1.  A nested loop generates a grid of `full_cube()` modules.
2.  Vertical rods are placed at the center of each column.
3.  Stoppers are placed flush at the top and bottom of the grid stack.

---

## Render Modes and Parts

Each SCAD file uses a `render_mode` integer to select which part to export. The mapping is declared in the [project manifest](./manifest.md):

| Part ID | `render_mode` | Used in Modes |
|---------|---------------|---------------|
| `main` | 0 | Unit |
| `bottom` | 1 | Assembly, Grid |
| `top` | 2 | Assembly, Grid |
| `rods` | 3 | Grid |
| `stoppers` | 4 | Grid |

[Back to Index](./index.md)
