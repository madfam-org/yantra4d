// Qubic NEMA Motor Mount
// Parametric motor bracket for NEMA 17/23/34 stepper motors
// Uses NopSCADlib dimensions for accurate motor hole patterns

// --- Parameters (overridden by platform) ---
nema_size = 17;
wall_thickness = 4;
base_thickness = 5;
mounting_style = 0;  // 0 = flat plate, 1 = L-bracket
fn = 0;
render_mode = 0;

$fn = fn > 0 ? fn : 48;

// NEMA motor dimensions lookup
// [face_width, hole_spacing, shaft_hole_d, screw_d, body_length]
function nema_dims(size) =
    size == 17 ? [42.3, 31, 22, 3, 48] :
    size == 23 ? [56.4, 47.14, 38.1, 5.5, 56] :
    size == 34 ? [86.0, 69.6, 73, 5.5, 66] :
    [42.3, 31, 22, 3, 48];  // default to 17

dims = nema_dims(nema_size);
face_w = dims[0];
hole_spacing = dims[1];
shaft_hole_d = dims[2];
screw_d = dims[3];
body_len = dims[4];

plate_size = face_w + wall_thickness * 2;
bracket_height = mounting_style == 1 ? face_w : 0;

// Mounting base holes
mount_hole_d = 5;
mount_hole_spacing = plate_size - 10;

module motor_plate() {
    difference() {
        // Base plate
        translate([-plate_size/2, -plate_size/2, 0])
            cube([plate_size, plate_size, base_thickness]);

        // Center shaft hole
        translate([0, 0, -1])
            cylinder(d=shaft_hole_d + 1, h=base_thickness + 2, $fn=$fn);

        // Motor screw holes (4 corners)
        for (x = [-1, 1], y = [-1, 1])
            translate([x * hole_spacing/2, y * hole_spacing/2, -1])
                cylinder(d=screw_d + 0.3, h=base_thickness + 2, $fn=24);

        // Mounting holes for attaching to surface
        for (x = [-1, 1], y = [-1, 1])
            translate([x * mount_hole_spacing/2, y * mount_hole_spacing/2, -1])
                cylinder(d=mount_hole_d, h=base_thickness + 2, $fn=24);
    }
}

module l_bracket() {
    motor_plate();

    // Vertical bracket wall
    translate([-plate_size/2, -plate_size/2, 0])
        difference() {
            cube([plate_size, wall_thickness, bracket_height + base_thickness]);
            // Lightening holes
            translate([plate_size/2, -1, bracket_height/2 + base_thickness])
                rotate([-90, 0, 0])
                    cylinder(d=bracket_height * 0.5, h=wall_thickness + 2, $fn=$fn);
        }
}

// --- Render mode dispatch ---
if (render_mode == 0) {
    if (mounting_style == 0) {
        motor_plate();
    } else {
        l_bracket();
    }
}
// render_mode == 1 is for static_stl (NEMA reference) — handled by platform
