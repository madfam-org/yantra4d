// Suppress default render in half_cube
is_library = 1;
include <half_cube.scad>

// --- Parameters ---
rows = 8;
cols = 8;
rod_extension = 10;
rotation_clearance = 2;  // Gap between rotating cubes (mm)
is_library = true; // Suppress half_cube single render

// --- Letter Parameters ---
letter_bottom = "V";
letter_top = "F";

// --- Visibility Toggles ---
show_bottom = true;    // Show/hide bottom half-cube units
show_top = true;       // Show/hide top half-cube units
show_rods = true;      // Show/hide connecting rods
show_stoppers = true;  // Show/hide rod stoppers

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

// --- Derived ---
// Grid pitch = cube diagonal + clearance for free rotation
grid_pitch = size * sqrt(2) + rotation_clearance;

// Total dimensions based on grid pitch
total_width = (cols - 1) * grid_pitch + size;  // First and last cubes contribute half their size
total_height = rows * size;  // Vertical stacking remains at cube size

// Rod Logic:
// The assembly stack is:
// 1. Bottom Stopper (rail_H = 2*thick)
// 2. Grid (total_height = rows * size)
// 3. Top Stopper (rail_H = 2*thick)
// Flush Length = total_height + 2 * rail_H
// Rod Length = Flush Length + 2 * rod_extension

rail_H = thick * 2;
flush_length = total_height + 2 * rail_H;
rod_length = flush_length + 2 * rod_extension;

// --- Modules ---

module full_cube() {
    union() {
        // Part A: Right-side up
        assembly(
            v_base=show_bottom_base, v_walls=show_bottom_walls,
            v_mech=show_bottom_mech, v_letter=show_bottom_letter,
            v_wall_left=show_bottom_wall_left, v_wall_right=show_bottom_wall_right,
            v_mech_base_ring=show_bottom_mech_base_ring,
            v_mech_pillars=show_bottom_mech_pillars,
            v_mech_snap_beams=show_bottom_mech_snap_beams
        );

        // Part B: Upside down and Rotated 90
        translate([0, 0, size]) rotate([180, 0, 90]) assembly(flipped=true,
            v_base=show_top_base, v_walls=show_top_walls,
            v_mech=show_top_mech, v_letter=show_top_letter,
            v_wall_left=show_top_wall_left, v_wall_right=show_top_wall_right,
            v_mech_base_ring=show_top_mech_base_ring,
            v_mech_pillars=show_top_mech_pillars,
            v_mech_snap_beams=show_top_mech_snap_beams
        );
    }
}

module stopper_rail() {
    // Horizontal bar with holes
    rail_W = size;
    rail_H = thick * 2;
    rail_L = total_width;

    difference() {
        translate([size/2, (cols-1)*grid_pitch/2 + size/2, 0])
             cube([rail_W, rail_L, rail_H], center=true);

        // Holes for Rods (spaced at grid_pitch)
        for (i = [0 : cols-1]) {
            translate([size/2, i*grid_pitch + size/2, 0])
                cylinder(r=rod_D/2 + clearance, h=rail_H*3, center=true);
        }
    }
}

module vertical_rod() {
    color("silver")
    cylinder(r=rod_D/2, h=rod_length, center=true);
}

// --- Main Assembly ---

// --- Render Logic ---
render_mode = 0; // Part selector (see project.json manifest): 0=all, 1=bottom, 2=top, 3=rods, 4=stoppers

// --- Main Assembly ---

// 1. Grid of Cubes
for (j = [0 : rows-1]) {
    for (i = [0 : cols-1]) {
        translate([0, i*grid_pitch, j*size]) {
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
        }
    }
}

// 2. Vertical Rods (Per Column)
if (render_mode == 0 || render_mode == 3) {
    if (show_rods) {
        for (i = [0 : cols-1]) {
            translate([size/2, i*grid_pitch + size/2, rows*size/2])
                vertical_rod();
        }
    }
}

// 3. Stoppers (Top and Bottom)
if (render_mode == 0 || render_mode == 4) {
    if (show_stoppers) {
        // Bottom Stopper
        translate([0, 0, -rail_H/2])
            stopper_rail();

        // Top Stopper
        translate([0, 0, rows*size + rail_H/2])
            stopper_rail();
    }
}
