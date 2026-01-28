include <half_cube.scad>

// --- Parameters ---
rows = 8;
cols = 8;
rod_extension = 10;
is_library = true; // Suppress half_cube single render

// --- Derived ---
total_width = cols * size;
total_height = rows * size;

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
        rotate([180, 0, 90]) assembly();
    }
}

module stopper_rail() {
    // Horizontal bar with holes
    rail_W = size;
    rail_H = thick * 2;
    rail_L = total_width;
    
    difference() {
        translate([rail_L/2 - size/2, 0, 0])
             cube([rail_L, rail_W, rail_H], center=true);
             
        // Holes for Rods
        for (i = [0 : cols-1]) {
            translate([i*size, 0, 0])
                cylinder(r=rod_D/2 + clearance, h=rail_H*3, center=true);
        }
    }
}

module vertical_rod() {
    color("silver")
    cylinder(r=rod_D/2, h=rod_length, center=true);
}

// --- Main Assembly ---

// 1. Grid of Cubes
for (j = [0 : rows-1]) {
    for (i = [0 : cols-1]) {
        translate([i*size, 0, j*size])
            full_cube();
    }
}

// 2. Vertical Rods (Per Column)
for (i = [0 : cols-1]) {
    // Center rod vertically relative to the grid
    // Grid Z goes from -size/2 (bottom of first cube) to (rows-1)*size + size/2
    // Actually, full_cube is centered at 0.
    // So row 0 is at Z=0.
    // Row 1 is at Z=20.
    // Total Z range: [-10, (rows-1)*20 + 10].
    // Center Z = (rows-1)*10.
    
    translate([i*size, 0, (rows-1)*size/2])
        vertical_rod();
}

// 3. Stoppers (Top and Bottom)
// Bottom Stopper (Flush with bottom of grid at Z=-size/2)
translate([0, 0, -size/2 - rail_H/2])
    stopper_rail();

// Top Stopper (Flush with top of grid at Z = (rows-1)*size + size/2)
translate([0, 0, (rows-1)*size + size/2 + rail_H/2])
    stopper_rail();
