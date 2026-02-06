// Desk Organizer — Portacosas
// Parametric modular desk organizer with snap-fit tray system
// render_mode selects part: 0=tray_base, 1=pen_holder, 2=phone_stand,
//                           3=card_slot, 4=cable_clip, 5=label_plate

// --- Parameters ---
render_mode = 0;

// Tray dimensions
tray_width = 200;
tray_depth = 120;
wall_height = 80;
wall_thickness = 2.0;

// Pen holder
pen_count = 5;
pen_diameter = 12;
pen_style = false; // false=round, true=hex

// Phone stand
phone_width = 75;
phone_angle = 65;
charging_slot = true;

// Card slot
card_width = 90;
card_depth = 60;
card_angle = 10;

// Cable clip
clip_count = 2;
clip_diameter = 6;

// Personalization
label_text = "YANTRA4D";
label_depth = 0.5;

// Grid (used by grid.scad)
rows = 1;
cols = 1;

// Resolution
$fn = 48;

// --- Derived ---
snap_size = 3;        // snap-fit nub size
snap_tol = 0.2;       // snap-fit tolerance
base_h = wall_thickness;  // tray floor thickness
pen_holder_w = pen_count * (pen_diameter + wall_thickness) + wall_thickness;
pen_holder_d = pen_diameter + wall_thickness * 2;

// --- Snap-fit socket/nub helpers ---
module snap_nub(h=snap_size) {
    cylinder(d1=snap_size, d2=snap_size*0.6, h=h);
}

module snap_socket(h=snap_size) {
    cylinder(d=snap_size + snap_tol*2, h=h+0.1);
}

// --- Tray Base ---
module tray_base() {
    difference() {
        union() {
            // Floor plate
            cube([tray_width, tray_depth, base_h]);
            // Low perimeter lip
            difference() {
                cube([tray_width, tray_depth, base_h + 4]);
                translate([wall_thickness, wall_thickness, base_h])
                    cube([tray_width - wall_thickness*2,
                          tray_depth - wall_thickness*2,
                          5]);
            }
        }
        // Snap-fit sockets for components
        // Pen holder socket — left side
        translate([wall_thickness + pen_holder_w/2,
                   tray_depth/2, -0.05])
            snap_socket(base_h + 0.1);
        // Phone stand socket — right side
        translate([tray_width - wall_thickness - 30,
                   tray_depth/2, -0.05])
            snap_socket(base_h + 0.1);
        // Card slot socket — front center
        translate([tray_width/2,
                   wall_thickness + 15, -0.05])
            snap_socket(base_h + 0.1);
        // Cable clip sockets — back edge
        for (i = [0 : clip_count - 1]) {
            translate([wall_thickness + 20 + i * (tray_width - 40) / max(clip_count - 1, 1),
                       tray_depth - wall_thickness - 5, -0.05])
                snap_socket(base_h + 0.1);
        }
    }
}

// --- Pen Holder ---
module pen_holder() {
    holder_h = wall_height * 0.7;
    difference() {
        // Outer shell
        if (pen_style) {
            // Hex grid container
            cube([pen_holder_w, pen_holder_d, holder_h]);
        } else {
            cube([pen_holder_w, pen_holder_d, holder_h]);
        }
        // Pen bores
        for (i = [0 : pen_count - 1]) {
            px = wall_thickness + pen_diameter/2 + i * (pen_diameter + wall_thickness);
            py = pen_holder_d / 2;
            translate([px, py, wall_thickness]) {
                if (pen_style) {
                    // Hexagonal bore
                    cylinder(d=pen_diameter, h=holder_h, $fn=6);
                } else {
                    cylinder(d=pen_diameter, h=holder_h);
                }
            }
        }
    }
    // Snap nub on bottom
    translate([pen_holder_w/2, pen_holder_d/2, 0])
        mirror([0,0,1]) snap_nub();
}

// --- Phone Stand ---
module phone_stand() {
    stand_d = 40;
    stand_h = wall_height * 0.8;
    lip_h = 10;

    difference() {
        union() {
            // Back angled support — hull for smooth cradle
            hull() {
                cube([phone_width, wall_thickness, stand_h]);
                translate([0, stand_d, 0])
                    cube([phone_width, wall_thickness, lip_h]);
            }
            // Bottom platform
            cube([phone_width, stand_d + wall_thickness, wall_thickness]);
            // Front lip
            translate([0, stand_d, 0])
                cube([phone_width, wall_thickness, lip_h]);
        }
        // Charging slot cutout
        if (charging_slot) {
            slot_w = 25;
            slot_h = 8;
            translate([(phone_width - slot_w)/2, -0.1, wall_thickness])
                cube([slot_w, wall_thickness + 0.2, slot_h]);
            translate([(phone_width - slot_w)/2, -0.1, wall_thickness])
                cube([slot_w, stand_d * 0.3, slot_h]);
        }
    }
    // Snap nub on bottom center
    translate([phone_width/2, stand_d/2, 0])
        mirror([0,0,1]) snap_nub();
}

// --- Card Slot ---
module card_slot() {
    slot_h = wall_height * 0.4;
    difference() {
        // Angled pocket
        hull() {
            cube([card_width, wall_thickness, slot_h]);
            translate([0, card_depth, 0])
                cube([card_width, wall_thickness, slot_h * 0.3]);
        }
        // Interior cutout
        translate([wall_thickness, wall_thickness, wall_thickness])
            hull() {
                cube([card_width - wall_thickness*2, 0.1, slot_h - wall_thickness]);
                translate([0, card_depth - wall_thickness, 0])
                    cube([card_width - wall_thickness*2, 0.1,
                          slot_h * 0.3 - wall_thickness]);
            }
    }
    // Bottom platform
    cube([card_width, card_depth + wall_thickness, wall_thickness]);
    // Snap nub
    translate([card_width/2, card_depth/2, 0])
        mirror([0,0,1]) snap_nub();
}

// --- Cable Clip ---
module cable_clip() {
    clip_h = 15;
    clip_w = clip_diameter + wall_thickness * 2;
    gap = clip_diameter * 0.4; // opening gap

    difference() {
        cylinder(d=clip_w, h=clip_h);
        // Cable bore
        translate([0, 0, wall_thickness])
            cylinder(d=clip_diameter, h=clip_h);
        // C-shaped opening
        translate([0, clip_w/2, wall_thickness + clip_h * 0.3])
            cube([gap, clip_w, clip_h], center=true);
    }
    // Base pad
    translate([-clip_w/2, -clip_w/2, 0])
        cube([clip_w, clip_w, wall_thickness]);
    // Snap nub
    mirror([0,0,1]) snap_nub();
}

// --- Label Plate ---
module label_plate() {
    plate_w = tray_width * 0.4;
    plate_h = 12;
    plate_d = wall_thickness;

    difference() {
        cube([plate_w, plate_d, plate_h]);
        // Embossed text
        translate([plate_w/2, -0.01, plate_h/2])
            rotate([90, 0, 180])
                linear_extrude(height=label_depth + 0.01)
                    text(label_text, size=plate_h * 0.6,
                         halign="center", valign="center",
                         font="Liberation Sans:style=Bold");
    }
}

// --- Render Selector ---
if (render_mode == 0) tray_base();
if (render_mode == 1) pen_holder();
if (render_mode == 2) phone_stand();
if (render_mode == 3) card_slot();
if (render_mode == 4) cable_clip();
if (render_mode == 5) label_plate();
