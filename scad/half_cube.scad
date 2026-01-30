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

// --- Advanced Visibility (sub-component toggles) ---
show_wall_left = true;
show_wall_right = true;
show_mech_base_ring = true;
show_mech_pillars = true;
show_mech_snap_beams = true;

// --- Flip Mode (for top unit) ---
is_flipped = false;        // true = top unit (rotated mechanism, inverted letter)

// --- Letter Parameters ---
letter_bottom = "V";
letter_top = "F";
letter = is_flipped ? letter_top : letter_bottom;
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
snap_sink       = max(size * 0.005, 0.05);            // Head sunk into shaft for boolean union

// Derived
cyl_R_base = rod_D/2 + clearance;
cyl_R = cyl_R_base + (size/2 - thick - cyl_R_base) * 0.7;  // Adaptive to available space
cyl_H = size - thick - fit_clear;

// Weld cube size for mesh integrity at internal junctions
weld = max(size * 0.02, 0.15);

// --- Main Assembly ---
module assembly(
    flipped=is_flipped,
    v_base=show_base, v_walls=show_walls, v_mech=show_mech, v_letter=show_letter,
    v_wall_left=show_wall_left, v_wall_right=show_wall_right,
    v_mech_base_ring=show_mech_base_ring,
    v_mech_pillars=show_mech_pillars,
    v_mech_snap_beams=show_mech_snap_beams
) {
    difference() {
        union() {
            // 1. Base Plate
            if (v_base)
                translate([0, 0, -size/2 + thick/2])
                    base_plate(flipped=flipped);

            // 2. Side Walls with full mitered edges (top + front/back)
            if (v_walls && v_wall_left)
                translate([-size/2 + thick/2, 0, 0])
                    mitered_wall();
            if (v_walls && v_wall_right)
                translate([size/2 - thick/2, 0, 0])
                    mirror([1,0,0]) mitered_wall();

            // 3. Central mechanism with snap-fit
            if (v_mech)
                translate([0, 0, -size/2])
                    mechanism_pillars(flipped=flipped,
                        v_base_ring=v_mech_base_ring,
                        v_pillars=v_mech_pillars,
                        v_snap_beams=v_mech_snap_beams);

            // 4. Letters on BOTH walls (embossed mode)
            if (v_letter && letter_emboss) {
                letter_geometry(flipped=flipped, side="left");
                letter_geometry(flipped=flipped, side="right");
            }
        }

        // Global subtractions
        // Rod bore through center
        cylinder(r=rod_D/2 + clearance, h=size*2, center=true);

        // Letters carved on BOTH walls
        if (v_letter && !letter_emboss) {
            letter_geometry(flipped=flipped, side="left");
            letter_geometry(flipped=flipped, side="right");
        }
    }
}

// --- Base Plate ---
// Full width/depth with quarter-circle perforations for opposing mechanism pass-through
module base_plate(flipped=false) {
    perf_R = cyl_R + fit_clear;
    // Bottom half (flipped=false): opposing pillars are at Q2/Q4 (angles 90, 270)
    // Top half (flipped=true): opposing pillars are at Q1/Q3 (angles 0, 180)
    perf_base = flipped ? 0 : 90;

    difference() {
        cube([size - 2*fit_clear, size - 2*fit_clear, thick], center=true);

        // Quarter-circle perforations for opposing mechanism
        for (angle = [perf_base, perf_base + 180])
            rotate([0, 0, angle])
                linear_extrude(thick + 1, center=true)
                    intersection() {
                        circle(r = perf_R, $fn = 64);
                        polygon([[0,0], [size,0], [0,size]]);
                    };
    }
}

// --- Mitered Wall ---
// Full-height wall from -size/2 to +size/2-fit_clear with 45° miters on top and front/back
module mitered_wall() {
    wall_length = size - 2*fit_clear;  // Y dimension

    difference() {
        // Main wall body — full height
        rotate([90, 0, 0])
        linear_extrude(wall_length, center=true)
            polygon([
                [-thick/2, -size/2],                   // Bottom-outer
                [-thick/2, size/2 - fit_clear],        // Top-outer (full height)
                [thick/2, size/2 - thick - fit_clear], // Top-inner (45° miter)
                [thick/2, -size/2]                     // Bottom-inner
            ]);

        // Front miter cut: full-height 45° chamfer at +Y corner
        translate([0, size/2 - fit_clear, 0])
            rotate([45, 0, 0])
                cube([thick + 1, thick * 1.5, size * 2], center=true);

        // Back miter cut: full-height 45° chamfer at -Y corner
        translate([0, -(size/2 - fit_clear), 0])
            rotate([-45, 0, 0])
                cube([thick + 1, thick * 1.5, size * 2], center=true);
    }
}

// --- Letter Geometry ---
// Places letter on specified wall exterior
// Both left and right walls get letters
module letter_geometry(flipped=is_flipped, side="left") {
    local_letter = flipped ? letter_top : letter_bottom;
    flip_angle = flipped ? 180 : 0;
    letter_z = 0;  // Center of cube (full-height walls)

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
module mechanism_pillars(flipped=is_flipped,
    v_base_ring=true, v_pillars=true, v_snap_beams=true
) {
    base_ring_h = thick + max(size * 0.005, 0.05);
    pillar_height = cyl_H;

    mech_rotation = flipped ? 90 : 0;

    rotate([0, 0, mech_rotation])
    union() {
        // 1. Solid base ring
        if (v_base_ring)
            cylinder(r=cyl_R, h=base_ring_h);

        // 2. Weld cubes at base ring / pillar junction for mesh integrity
        if (v_pillars)
            for (angle = [0, 90, 180, 270])
                rotate([0, 0, angle])
                    translate([cyl_R * 0.5, 0, base_ring_h - weld/2])
                        cube(weld, center=true);

        // 3. Pillars with wedge cuts
        if (v_pillars)
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
        if (v_snap_beams) {
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
        }

        // 5. Weld cubes at pillar tops for mesh integrity
        if (v_snap_beams)
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
