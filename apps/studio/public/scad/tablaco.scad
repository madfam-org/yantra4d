// Suppress default render in half_cube
is_library = 1;
include <half_cube.scad>

// --- Parameters ---
rows = 8;
cols = 8;
rod_extension = 10;
rotation_clearance = 2;  // Gap between rotating cubes (mm)
is_library = true; // Suppress half_cube single render

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
        assembly();
        
        // Part B: Upside down and Rotated 90
        rotate([180, 0, 90]) assembly(flipped=true);
    }
}

module stopper_rail() {
    // Horizontal bar with holes
    rail_W = size;
    rail_H = thick * 2;
    rail_L = total_width;
    
    difference() {
        translate([(cols-1)*grid_pitch/2, 0, 0])
             cube([rail_L, rail_W, rail_H], center=true);
             
        // Holes for Rods (spaced at grid_pitch)
        for (i = [0 : cols-1]) {
            translate([i*grid_pitch, 0, 0])
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
render_mode = 0; // 0=all, 1=bottom, 2=top, 3=rods, 4=stoppers

// --- Main Assembly ---

// 1. Grid of Cubes
for (j = [0 : rows-1]) {
    for (i = [0 : cols-1]) {
        translate([i*grid_pitch, 0, j*size]) {
            // Part A: Right-side up (Bottom Unit)
            if (render_mode == 0 || render_mode == 1)
                assembly();
            
            // Part B: Upside down and Rotated 90 (Top Unit)
            if (render_mode == 0 || render_mode == 2)
                rotate([180, 0, 90]) assembly(flipped=true);
        }
    }
}

// 2. Vertical Rods (Per Column)
if (render_mode == 0 || render_mode == 3) {
    for (i = [0 : cols-1]) {
        translate([i*grid_pitch, 0, (rows-1)*size/2])
            vertical_rod();
    }
}

// 3. Stoppers (Top and Bottom)
if (render_mode == 0 || render_mode == 4) {
    // Bottom Stopper
    translate([0, 0, -size/2 - rail_H/2])
        stopper_rail();

    // Top Stopper
    translate([0, 0, (rows-1)*size + size/2 + rail_H/2])
        stopper_rail();
}
