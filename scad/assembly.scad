// Suppress default render in half_cube
is_library = 1;
include <half_cube.scad>

// --- Parameters ---
// Inherits size, thick, rod_D from half_cube via command line

render_mode = 0; // Part selector (see project.json manifest): 0=all, 1=bottom, 2=top

// --- Visibility Toggles ---
show_bottom = true;  // Show/hide bottom half-cube unit
show_top = true;     // Show/hide top half-cube unit

// --- Main Assembly ---
// A single interlocking cube (two half-cubes)

// Part A: Right-side up (Bottom Unit)
if (render_mode == 0 || render_mode == 1)
    if (show_bottom) assembly();

// Part B: Upside down and Rotated 90 (Top Unit)
if (render_mode == 0 || render_mode == 2)
    if (show_top) rotate([180, 0, 90]) assembly(flipped=true);
