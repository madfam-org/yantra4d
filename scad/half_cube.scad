// half_cube.scad - Simplified Parametric Half-Cube
// Designed for verification: single volume, watertight, no collision
// Units: mm

$fn = 64;

// --- Parameters ---
size = 20.0;          // Outer cube dimension
thick = 2.5;          // Wall thickness
rod_D = 3.0;          // Rod diameter
clearance = 0.2;      // Clearance for rod bore
fit_clear = 0.2;      // Miter face clearance (increased per research)

// --- Visibility Toggles ---
show_base = true;
show_walls = true;
show_mech = true;

// Derived
cyl_R = 4.5;          // Mechanism cylinder radius
cyl_H = size/2 - thick - fit_clear; // Height from base top to part top

// --- Main Assembly ---
module assembly() {
    difference() {
        union() {
            // 1. Base Plate (bottom of U-channel)
            if (show_base)
                translate([0, 0, -size/2 + thick/2])
                    base_plate();
            
            // 2. Side Walls with mitered edges
            if (show_walls) {
                translate([-size/2 + thick/2, 0, 0])
                    mitered_wall();
                translate([size/2 - thick/2, 0, 0])
                    mirror([1,0,0]) mitered_wall();
            }
            
            // 3. Central mechanism pillars
            // Position at base plate bottom (z=-10) so base_ring spans through base
            if (show_mech)
                translate([0, 0, -size/2])  // Start at very bottom of part
                    mechanism_pillars();
        }
        
        // Global subtractions
        // Rod bore through center
        cylinder(r=rod_D/2 + clearance, h=size*2, center=true);
    }
}

// --- Base Plate ---
// Full width in X and Y, with trapezoid profile in Y-Z
module base_plate() {
    // Simple rectangular base that spans full width
    // The Y dimension must go edge to edge (minus clearance)
    cube([size - 2*fit_clear, size - 2*fit_clear, thick], center=true);
}

// --- Mitered Wall ---
// Wall with 45° chamfer only on top for mating interface
// Wall only spans HALF the cube (from base to midpoint)
module mitered_wall() {
    // The wall needs to span: 
    //   X = thick (wall thickness)
    //   Y = size (full cube width, minus clearance)
    //   Z = half cube height (from -size/2 to -fit_clear)
    
    wall_length = size - 2*fit_clear;  // Y dimension
    
    // Rotate the extrusion so it extends along Y instead of Z
    rotate([90, 0, 0])  // Rotate -90° around X to point extrusion in -Y (then center=true makes it +/-Y)
    linear_extrude(wall_length, center=true)  // This now extrudes along Y
        // Polygon in XZ plane (after rotation, this becomes the actual XZ plane of the wall)
        polygon([
            [-thick/2, -size/2],             // Bottom-outer (z=-10)
            [-thick/2, -fit_clear],          // Top-outer (z=-0.2)
            [thick/2, -thick - fit_clear],   // Top-inner (z=-2.7, chamfered)
            [thick/2, -size/2]               // Bottom-inner (z=-10)
        ]);
}

// --- Mechanism Pillars ---
// Two opposing quadrant pillars (0° and 180°) with a solid base ring
module mechanism_pillars() {
    base_ring_h = thick + 0.1;  // Height of solid ring = base plate thickness + overlap
    pillar_height = cyl_H;
    
    union() {
        // 1. Solid base ring (no wedge cuts) - this connects to base plate
        cylinder(r=cyl_R, h=base_ring_h);
        
        // 2. Pillars above the base ring (with wedge cuts)
        translate([0, 0, base_ring_h - 0.1])  // Small overlap for solid union
            difference() {
                cylinder(r=cyl_R, h=pillar_height);
                
                // Cut away two opposing quadrants (90° and 270°)
                rotate([0, 0, 90])
                    wedge_cutter(pillar_height + 1);
                rotate([0, 0, 270])
                    wedge_cutter(pillar_height + 1);
            }
    }
}

// Wedge cutter for 90° sector
module wedge_cutter(h=size) {
    linear_extrude(h)
        polygon([[0, 0], [size, 0], [0, size]]);
}

// --- Render ---
// Only render if not included as library
if (is_undef(is_library)) {
    assembly();
}
