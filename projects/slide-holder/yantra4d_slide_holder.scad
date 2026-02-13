// Yantra4D Parametric Microscope Slide Holder
// Wrapper for vendor/slide-holder/slide_holder.scad
// Original design: Lucas Wilder — Michigan Technological University — EE 4777

// --- Parameters (overridden by platform) ---
slides = 10;        // Number of slide slots
thickness = 1;      // Slide thickness (mm)
length = 76.2;      // Slide length (mm)
width = 25;         // Slide width (mm)
fn = 0;             // Quality ($fn) — 0 = auto
render_mode = 0;    // 0 = holder

$fn = fn > 0 ? fn : 32;

// --- Derived dimensions (match vendor logic) ---
slot_spacing = 4;
slot_tolerance = 1;
body_width = slot_spacing * slides + 8;
body_depth = length + 6.5;
body_height = (width / 2) + 3;
wall_inset = 3;
floor_inset = 3;

// --- Modules ---
module slide_holder() {
    difference() {
        // Main body
        cube(size = [body_width, body_depth, body_height], center = false);

        // Slide slots with tolerance
        for (i = [0 : 1 : slides]) {
            translate([wall_inset + (slot_spacing * i), 2.5, floor_inset])
                cube(size = [thickness + slot_tolerance, length + 2, width], center = false);
        }

        // Center cutout for easy slide access
        translate([wall_inset, 5, -1])
            cube(size = [slot_spacing * slides + 2, length - 3, width + 4], center = false);
    }
}

// --- Render mode dispatch ---
if (render_mode == 0) {
    slide_holder();
}
