// Parametric Microscope Slide Holder
// Original author: Lucas Wilder — Michigan Technological University — EE 4777
//
// A parametric holder for standard microscope slides.
// Generates a rack with evenly-spaced slots and a center cutout
// for easy slide access.
//
// Parameters:
//   slides    — Number of slide slots (default: 10)
//   thickness — Slide thickness in mm (default: 1)
//   length    — Slide length in mm (default: 76.2, standard 3")
//   width     — Slide width in mm (default: 25, standard 1")

// --- Parameters ---
slides = 10;       // Number of slides
thickness = 1;     // Slide thickness (mm)
length = 76.2;     // Slide length (mm) — standard: 75–76.2
width = 25;        // Slide width (mm)  — standard: 25–26

// --- Derived dimensions ---
slot_spacing = 4;                       // Center-to-center slot distance (mm)
slot_tolerance = 1;                     // Extra width per slot for clearance (mm)
body_width = slot_spacing * slides + 8; // Total body width
body_depth = length + 6.5;             // Total body depth (slide + margin)
body_height = (width / 2) + 3;         // Total body height
wall_inset = 3;                        // Inset from body edge to first slot
floor_inset = 3;                       // Floor thickness under slots

// --- Geometry ---
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
