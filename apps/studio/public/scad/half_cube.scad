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
show_letter = true;

// --- Flip Mode (for top unit) ---
is_flipped = false;        // true = top unit (rotated mechanism, inverted letter)

// --- Letter Parameters ---
letter = is_flipped ? "F" : "V";  // Default: V for bottom, F for top
letter_emboss = false;     // true = raised, false = carved
letter_depth = 0.5;        // Depth/height of letter (mm)
letter_size = 6;           // Font size (mm)

// Derived
cyl_R = 4.5;          // Mechanism cylinder radius
cyl_H = size/2 - thick - fit_clear; // Height from base top to part top

// --- Main Assembly ---
module assembly(flipped=is_flipped) {
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
                    mechanism_pillars(flipped=flipped);
            
            // 4. Letter (embossed mode - raised)
            if (show_letter && letter_emboss)
                letter_geometry(flipped=flipped);
        }
        
        // Global subtractions
        // Rod bore through center
        cylinder(r=rod_D/2 + clearance, h=size*2, center=true);
        
        // Letter (carved mode - recessed)
        if (show_letter && !letter_emboss)
            letter_geometry(flipped=flipped);
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

// --- Letter Geometry ---
// Places letter on left wall exterior
// Flipped 180° for top unit so it reads correctly after assembly
module letter_geometry(flipped=is_flipped) {
    // Position on left wall exterior face
    wall_x = -size/2;  // Left wall position
    letter_z = -size/4;  // Center of wall height
    
    // Determine letter and rotation based on local flipped state
    local_letter = flipped ? "F" : "V";
    
    // Rotation: 90° to face outward from wall
    // When flipped: add 180° so letter reads correctly after assembly flip
    flip_angle = flipped ? 180 : 0;
    
    translate([wall_x, 0, letter_z])
        rotate([90, flip_angle, 90]) { // Face outward (-X direction)
            // Counter-mirror for flipped unit to ensure text reads Left-to-Right
            scale([flipped ? -1 : 1, 1, 1])
            
            linear_extrude(letter_depth + (letter_emboss ? 0 : thick))
                text(local_letter, size=letter_size, halign="center", valign="center", 
                     font="Liberation Sans:style=Bold");
}
}

// --- Mechanism Pillars ---
// Two opposing quadrant pillars with a solid base ring
// Bottom unit: pillars at 0°/180°, cuts at 90°/270°
// Flipped unit: pillars at 90°/270°, cuts at 0°/180° (rotated 90°)
module mechanism_pillars(flipped=is_flipped) {
    base_ring_h = thick + 0.1;  // Height of solid ring = base plate thickness + overlap
    pillar_height = cyl_H;
    
    // Rotate entire mechanism 90° for flipped (top) unit
    mech_rotation = flipped ? 90 : 0;
    
    rotate([0, 0, mech_rotation])
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
