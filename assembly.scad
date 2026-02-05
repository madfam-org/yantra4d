// Suppress default render in half_cube
is_library = 1;
include <half_cube.scad>

// --- Parameters ---
// Inherits size, thick, rod_D from half_cube via command line

render_mode = 0; // Part selector (see project.json manifest): 0=all, 1=bottom, 2=top

// --- Letter Parameters ---
letter_bottom = "V";
letter_top = "F";

// --- Visibility Toggles ---
show_bottom = true;  // Show/hide bottom half-cube unit
show_top = true;     // Show/hide top half-cube unit

// --- Per-Half Advanced Visibility ---
show_bottom_base = true;
show_bottom_walls = true;
show_bottom_mech = true;
show_bottom_letter = true;
show_bottom_wall_left = true;
show_bottom_wall_right = true;
show_bottom_mech_base_ring = true;
show_bottom_mech_pillars = true;
show_bottom_mech_snap_beams = true;

show_top_base = true;
show_top_walls = true;
show_top_mech = true;
show_top_letter = true;
show_top_wall_left = true;
show_top_wall_right = true;
show_top_mech_base_ring = true;
show_top_mech_pillars = true;
show_top_mech_snap_beams = true;

// --- Main Assembly ---
// A single interlocking cube (two half-cubes)

// Part A: Right-side up (Bottom Unit)
if (render_mode == 0 || render_mode == 1)
    if (show_bottom) assembly(
        v_base=show_bottom_base, v_walls=show_bottom_walls,
        v_mech=show_bottom_mech, v_letter=show_bottom_letter,
        v_wall_left=show_bottom_wall_left, v_wall_right=show_bottom_wall_right,
        v_mech_base_ring=show_bottom_mech_base_ring,
        v_mech_pillars=show_bottom_mech_pillars,
        v_mech_snap_beams=show_bottom_mech_snap_beams
    );

// Part B: Upside down and Rotated 90 (Top Unit)
if (render_mode == 0 || render_mode == 2)
    if (show_top) translate([0, 0, size]) rotate([180, 0, 90]) assembly(flipped=true,
        v_base=show_top_base, v_walls=show_top_walls,
        v_mech=show_top_mech, v_letter=show_top_letter,
        v_wall_left=show_top_wall_left, v_wall_right=show_top_wall_right,
        v_mech_base_ring=show_top_mech_base_ring,
        v_mech_pillars=show_top_mech_pillars,
        v_mech_snap_beams=show_top_mech_snap_beams
    );
