// Suppress default render in half_cube
is_library = 1;
include <half_cube.scad>

// --- Parameters ---
// Inherits size, thick, rod_D from half_cube via command line

render_mode = 0; // 0=all, 1=bottom, 2=top

// --- Main Assembly ---
// A single interlocking cube (two half-cubes)

// Part A: Right-side up (Bottom Unit)
if (render_mode == 0 || render_mode == 1)
    assembly();

// Part B: Upside down and Rotated 90 (Top Unit)
if (render_mode == 0 || render_mode == 2)
    rotate([180, 0, 90]) assembly();
