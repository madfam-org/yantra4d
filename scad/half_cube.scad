// half_cube.scad - Parametric Half-Cube with Snap-Fit Mechanism
// Research-faithful implementation: Dual-U topology, snap locks, mitered walls
// Units: mm

$fn = 64;

// --- Parameters ---
size = 20.0;          // Outer cube dimension
thick = 2.5;          // Wall thickness
rod_D = 3.0;          // Rod diameter
clearance = 0.2;      // Clearance for rod bore
fit_clear = 0.2;      // Miter face clearance (per research)

// --- Visibility Toggles ---
show_base = true;
show_walls = true;
show_mech = true;
show_letter = true;

// --- Flip Mode (for top unit) ---
is_flipped = false;        // true = top unit (rotated mechanism, inverted letter)

// --- Letter Parameters ---
letter = is_flipped ? "F" : "V";
letter_emboss = false;     // true = raised, false = carved
letter_depth = 0.5;
letter_size = 6;

// --- Snap-Fit Parameters (scaled from research: 60mm -> size) ---
scale_factor = size / 60;
snap_beam_len   = max(6.0 * scale_factor, 1.5);  // Cantilever beam length
snap_beam_width = max(3.0 * scale_factor, 0.8);   // Beam width
snap_beam_thick = max(1.2 * scale_factor, 0.4);   // Beam thickness
snap_undercut   = max(0.6 * scale_factor, 0.15);   // Undercut depth on snap head
snap_head_len   = max(1.5 * scale_factor, 0.4);    // Length of snap head
snap_relief_w   = max(1.5 * scale_factor, 0.3);    // Relief slot width
snap_relief_d   = max(0.8 * scale_factor, 0.2);    // Relief slot depth into head
snap_sink       = 0.1;                              // Head sunk into shaft for boolean union

// Derived
cyl_R = size * 0.15 + rod_D/2 + clearance + 1;  // Parametric: derived from size and rod
cyl_H = size/2 - thick - fit_clear;

// Weld cube size for mesh integrity at internal junctions
weld = 0.4;

// --- Main Assembly ---
module assembly(flipped=is_flipped) {
    difference() {
        union() {
            // 1. Base Plate
            if (show_base)
                translate([0, 0, -size/2 + thick/2])
                    base_plate();

            // 2. Side Walls with full mitered edges (top + front/back)
            if (show_walls) {
                translate([-size/2 + thick/2, 0, 0])
                    mitered_wall();
                translate([size/2 - thick/2, 0, 0])
                    mirror([1,0,0]) mitered_wall();
            }

            // 3. Central mechanism with snap-fit
            if (show_mech)
                translate([0, 0, -size/2])
                    mechanism_pillars(flipped=flipped);

            // 4. Letters on BOTH walls (embossed mode)
            if (show_letter && letter_emboss) {
                letter_geometry(flipped=flipped, side="left");
                letter_geometry(flipped=flipped, side="right");
            }
        }

        // Global subtractions
        // Rod bore through center
        cylinder(r=rod_D/2 + clearance, h=size*2, center=true);

        // Letters carved on BOTH walls
        if (show_letter && !letter_emboss) {
            letter_geometry(flipped=flipped, side="left");
            letter_geometry(flipped=flipped, side="right");
        }
    }
}

// --- Base Plate ---
// Full width/depth, matching wall footprint for flush assembled faces
module base_plate() {
    cube([size - 2*fit_clear, size - 2*fit_clear, thick], center=true);
}

// --- Mitered Wall ---
// Wall spans from base to midpoint with 45° chamfer on top AND front/back edges
module mitered_wall() {
    wall_length = size - 2*fit_clear;  // Y dimension
    wall_half_z = size/2;              // Total Z span from -size/2 to 0

    // Wall height: from base bottom (-size/2) to top (-fit_clear)
    // With 45° miter on top edge and front/back edges
    difference() {
        // Main wall body
        rotate([90, 0, 0])
        linear_extrude(wall_length, center=true)
            // Profile in XZ plane: 45° chamfer on top
            polygon([
                [-thick/2, -size/2],             // Bottom-outer
                [-thick/2, -fit_clear],          // Top-outer
                [thick/2, -thick - fit_clear],   // Top-inner (45° chamfer)
                [thick/2, -size/2]               // Bottom-inner
            ]);

        // Front miter cut: 45° chamfer on front face (+Y edge)
        translate([0, size/2 - fit_clear, -size/4])
            rotate([45, 0, 0])
                cube([thick + 1, thick * 1.5, thick * 1.5], center=true);

        // Back miter cut: 45° chamfer on back face (-Y edge)
        translate([0, -(size/2 - fit_clear), -size/4])
            rotate([-45, 0, 0])
                cube([thick + 1, thick * 1.5, thick * 1.5], center=true);
    }
}

// --- Letter Geometry ---
// Places letter on specified wall exterior
// Both left and right walls get letters
module letter_geometry(flipped=is_flipped, side="left") {
    local_letter = flipped ? "F" : "V";
    flip_angle = flipped ? 180 : 0;
    letter_z = -size/4;

    if (side == "left") {
        wall_x = -size/2;
        translate([wall_x, 0, letter_z])
            rotate([90, flip_angle, 90])
                scale([flipped ? -1 : 1, 1, 1])
                    linear_extrude(letter_depth + (letter_emboss ? 0 : thick))
                        text(local_letter, size=letter_size, halign="center", valign="center",
                             font="Liberation Sans:style=Bold");
    } else {
        // Right wall: mirror placement
        wall_x = size/2;
        translate([wall_x, 0, letter_z])
            rotate([90, flip_angle, -90])
                scale([flipped ? -1 : 1, 1, 1])
                    linear_extrude(letter_depth + (letter_emboss ? 0 : thick))
                        text(local_letter, size=letter_size, halign="center", valign="center",
                             font="Liberation Sans:style=Bold");
    }
}

// --- Mechanism Pillars with Snap-Fit ---
// Two opposing quadrant pillars with base ring, snap beams, and weld cubes
module mechanism_pillars(flipped=is_flipped) {
    base_ring_h = thick + 0.1;
    pillar_height = cyl_H;

    mech_rotation = flipped ? 90 : 0;

    rotate([0, 0, mech_rotation])
    union() {
        // 1. Solid base ring
        cylinder(r=cyl_R, h=base_ring_h);

        // 2. Weld cubes at base ring / pillar junction for mesh integrity
        for (angle = [0, 90, 180, 270])
            rotate([0, 0, angle])
                translate([cyl_R * 0.5, 0, base_ring_h - weld/2])
                    cube(weld, center=true);

        // 3. Pillars with wedge cuts
        translate([0, 0, base_ring_h - 0.1])
            difference() {
                cylinder(r=cyl_R, h=pillar_height);

                // Cut away Q2 and Q4 (90° and 270°)
                rotate([0, 0, 90])
                    wedge_cutter(pillar_height + 1);
                rotate([0, 0, 270])
                    wedge_cutter(pillar_height + 1);
            }

        // 4. Snap-fit cantilever beams on pillar faces
        // Beams face outward from each pillar into the cut-away quadrants
        // Q1 pillar (0°-90°) gets beams facing into Q2 (90°) and Q4 (360°/0°-side)
        // Q3 pillar (180°-270°) gets beams facing into Q2 and Q4

        // Pillar Q1: beam at 90° face (facing +Y)
        translate([0, 0, base_ring_h - 0.1])
            snap_beam_at(angle=45, pillar_height=pillar_height);

        // Pillar Q1: beam at 0° face (facing +X)
        translate([0, 0, base_ring_h - 0.1])
            snap_beam_at(angle=315, pillar_height=pillar_height);

        // Pillar Q3: beam at 180° face (facing -X)
        translate([0, 0, base_ring_h - 0.1])
            snap_beam_at(angle=135, pillar_height=pillar_height);

        // Pillar Q3: beam at 270° face (facing -Y)
        translate([0, 0, base_ring_h - 0.1])
            snap_beam_at(angle=225, pillar_height=pillar_height);

        // 5. Weld cubes at pillar tops for mesh integrity
        for (angle = [0, 180])
            rotate([0, 0, angle])
                translate([cyl_R * 0.4, 0, base_ring_h + pillar_height - weld/2])
                    cube(weld, center=true);
    }
}

// --- Snap Beam ---
// Cantilever beam with undercut head and relief slot
// Placed at a given angle on the cylinder surface, growing upward from mid-pillar
module snap_beam_at(angle, pillar_height) {
    beam_z_start = pillar_height * 0.3;  // Start beam at 30% up the pillar

    rotate([0, 0, angle])
    translate([cyl_R - snap_sink, 0, beam_z_start]) {
        // Cantilever beam body
        // Extends radially outward, with length along Z
        rotate([0, 0, 0])
        union() {
            // Beam shaft - tapered slightly (thicker at root)
            hull() {
                // Root (attached to pillar)
                translate([0, -snap_beam_width/2, 0])
                    cube([snap_beam_thick, snap_beam_width, 0.01]);
                // Tip (slightly thinner)
                translate([0, -snap_beam_width/2, snap_beam_len])
                    cube([snap_beam_thick * 0.85, snap_beam_width, 0.01]);
            }

            // Snap head with undercut
            translate([0, -snap_beam_width/2, snap_beam_len])
                snap_head();
        }
    }
}

// --- Snap Head ---
// Overhanging head with undercut for positive engagement
// Includes relief slot for beam flexibility
module snap_head() {
    difference() {
        // Ramped head: hull from full undercut at base to flush at tip
        // Creates ~30° lead-in chamfer for easier insertion
        hull() {
            // Base: full undercut width
            translate([-snap_undercut, 0, 0])
                cube([snap_beam_thick + snap_undercut, snap_beam_width, 0.01]);
            // Tip: no undercut (flush with beam)
            translate([0, 0, snap_head_len - 0.01])
                cube([snap_beam_thick, snap_beam_width, 0.01]);
        }

        // Relief slot through center of head for flexibility
        translate([snap_beam_thick/2 - snap_relief_d/2, (snap_beam_width - snap_relief_w)/2, -0.1])
            cube([snap_relief_d, snap_relief_w, snap_head_len + 0.2]);
    }
}

// --- Wedge Cutter ---
// 90° sector cutter for quadrant removal
module wedge_cutter(h=size) {
    linear_extrude(h)
        polygon([[0, 0], [size, 0], [0, size]]);
}

// --- Render ---
if (is_undef(is_library)) {
    assembly();
}
